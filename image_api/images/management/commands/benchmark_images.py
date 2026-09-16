"""Benchmark the synchronous pregeneration API with deterministic source images."""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import psutil
import pyvips
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from images.models import ImageAsset
from images.services.storage import get_image_storage


IMAGE_DIMENSIONS = {
    "2k": (2048, 1024),
    "4k": (4096, 2048),
    "8k": (8192, 4096),
    "12k": (12000, 6000),
}


@dataclass
class BenchmarkSample:
    profile: str
    phase: str
    run: int
    width: int
    height: int
    upload_latency_ms: float
    processing_time_ms: float
    process_cpu_time_ms: float
    rss_before_bytes: int
    peak_rss_bytes: int
    storage_bytes: int
    file_count: int
    first_get_latency_ms: float
    second_get_latency_ms: float


class RssMonitor:
    """Sample the current process RSS while one request is being processed."""

    def __init__(self, interval_seconds: float = 0.01) -> None:
        self.process = psutil.Process()
        self.interval_seconds = interval_seconds
        self.peak_rss = self.process.memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)

    def start(self) -> int:
        baseline = self.process.memory_info().rss
        self.peak_rss = baseline
        self._thread.start()
        return baseline

    def stop(self) -> int:
        self._stop.set()
        self._thread.join()
        self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
        return self.peak_rss


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_deterministic_input(path: Path, width: int, height: int) -> None:
    """Create a non-flat RGB JPEG without requiring a separately downloaded fixture."""
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    coordinates = pyvips.Image.xyz(width, height)
    x = coordinates.extract_band(0).cast("uchar")
    y = coordinates.extract_band(1).cast("uchar")
    blue = (coordinates.extract_band(0) + coordinates.extract_band(1)).cast("uchar")
    x.bandjoin([y, blue]).write_to_file(str(path), Q=90, strip=True)


def directory_metrics(directory: Path) -> tuple[int, int]:
    files = [path for path in directory.rglob("*") if path.is_file()]
    return sum(path.stat().st_size for path in files), len(files)


def elapsed_request(client: Client, url: str) -> float:
    started = time.perf_counter()
    response = client.get(url)
    # Force FileResponse streaming work to be included in GET latency.
    if response.streaming:
        b"".join(response.streaming_content)
        response.close()
    if response.status_code != 200:
        raise CommandError(f"GET {url} returned HTTP {response.status_code}: {response.content!r}")
    return (time.perf_counter() - started) * 1000


class Command(BaseCommand):
    help = "Benchmark 2K/4K/8K/12K uploads and pregenerated WebP reads."

    def add_arguments(self, parser):
        parser.add_argument("--runs", type=int, default=3, help="Measured runs for each input profile (default: 3).")
        parser.add_argument("--warmup", type=int, default=1, help="Warm-up runs for each profile (default: 1).")
        parser.add_argument(
            "--profiles",
            default="2k,4k,8k,12k",
            help="Comma-separated profile names from: 2k, 4k, 8k, 12k.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            help="Directory for manifest, raw samples and report. Defaults to a timestamped benchmarks directory.",
        )

    def handle(self, *args, **options):
        runs, warmup = options["runs"], options["warmup"]
        if runs < 1 or warmup < 0:
            raise CommandError("--runs must be at least 1 and --warmup cannot be negative.")

        profiles = [profile.strip().lower() for profile in options["profiles"].split(",") if profile.strip()]
        unknown_profiles = set(profiles) - IMAGE_DIMENSIONS.keys()
        if not profiles or unknown_profiles:
            raise CommandError(f"Unknown profile(s): {', '.join(sorted(unknown_profiles)) or 'none'}")

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_directory = (options["output"] or (settings.BASE_DIR / "benchmarks" / timestamp)).resolve()
        if output_directory.exists() and any(output_directory.iterdir()):
            raise CommandError(f"Benchmark output directory must be empty: {output_directory}")
        input_directory = output_directory / "inputs"
        output_directory.mkdir(parents=True, exist_ok=True)

        manifest = []
        source_paths: dict[str, Path] = {}
        for profile in profiles:
            width, height = IMAGE_DIMENSIONS[profile]
            source_path = input_directory / f"{profile}.jpg"
            create_deterministic_input(source_path, width, height)
            source_paths[profile] = source_path
            manifest.append(
                {
                    "profile": profile,
                    "width": width,
                    "height": height,
                    "format": "image/jpeg",
                    "bytes": source_path.stat().st_size,
                    "sha256": sha256_file(source_path),
                }
            )

        environment = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_total_bytes": psutil.virtual_memory().total,
            "pyvips": pyvips.__version__,
            "libvips": ".".join(str(pyvips.version(index)) for index in range(3)),
            "runs": runs,
            "warmup": warmup,
            "profiles": profiles,
        }

        client = Client(HTTP_HOST="localhost")
        samples: list[BenchmarkSample] = []
        for profile in profiles:
            width, height = IMAGE_DIMENSIONS[profile]
            for iteration in range(warmup + runs):
                phase = "warmup" if iteration < warmup else "measurement"
                run_number = iteration + 1 if phase == "warmup" else iteration - warmup + 1
                source_bytes = source_paths[profile].read_bytes()
                upload = SimpleUploadedFile(f"{profile}.jpg", source_bytes, content_type="image/jpeg")
                monitor = RssMonitor()
                rss_before = monitor.start()
                cpu_started = time.process_time()
                wall_started = time.perf_counter()
                response = client.post("/api/v1/images", {"file": upload})
                upload_latency_ms = (time.perf_counter() - wall_started) * 1000
                cpu_time_ms = (time.process_time() - cpu_started) * 1000
                peak_rss = monitor.stop()
                if response.status_code != 201:
                    raise CommandError(f"POST for {profile} returned HTTP {response.status_code}: {response.content!r}")

                asset_id = response.json()["id"]
                storage = get_image_storage()
                asset_directory = storage.absolute_path(asset_id)
                try:
                    storage_bytes, file_count = directory_metrics(asset_directory)
                    first_get = elapsed_request(client, f"/api/v1/images/{asset_id}/medium")
                    second_get = elapsed_request(client, f"/api/v1/images/{asset_id}/medium")
                    sample = BenchmarkSample(
                        profile=profile,
                        phase=phase,
                        run=run_number,
                        width=width,
                        height=height,
                        upload_latency_ms=round(upload_latency_ms, 3),
                        # This pipeline processes synchronously; request latency is processing duration.
                        processing_time_ms=round(upload_latency_ms, 3),
                        process_cpu_time_ms=round(cpu_time_ms, 3),
                        rss_before_bytes=rss_before,
                        peak_rss_bytes=peak_rss,
                        storage_bytes=storage_bytes,
                        file_count=file_count,
                        first_get_latency_ms=round(first_get, 3),
                        second_get_latency_ms=round(second_get, 3),
                    )
                    samples.append(sample)
                    self.stdout.write(f"{profile} {phase} {run_number}: {upload_latency_ms:.1f} ms")
                finally:
                    storage.delete_asset_tree(asset_id)
                    ImageAsset.objects.filter(id=asset_id).delete()

        measured = [sample for sample in samples if sample.phase == "measurement"]
        summaries = {}
        for profile in profiles:
            profile_samples = [sample for sample in measured if sample.profile == profile]
            summaries[profile] = {
                "upload_latency_ms": metric_summary(sample.upload_latency_ms for sample in profile_samples),
                "processing_time_ms": metric_summary(sample.processing_time_ms for sample in profile_samples),
                "process_cpu_time_ms": metric_summary(sample.process_cpu_time_ms for sample in profile_samples),
                "peak_rss_bytes": metric_summary(sample.peak_rss_bytes for sample in profile_samples),
                "storage_bytes": metric_summary(sample.storage_bytes for sample in profile_samples),
                "file_count": metric_summary(sample.file_count for sample in profile_samples),
                "first_get_latency_ms": metric_summary(sample.first_get_latency_ms for sample in profile_samples),
                "second_get_latency_ms": metric_summary(sample.second_get_latency_ms for sample in profile_samples),
            }

        (output_directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (output_directory / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
        (output_directory / "samples.json").write_text(
            json.dumps([asdict(sample) for sample in samples], indent=2), encoding="utf-8"
        )
        (output_directory / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        (output_directory / "report.md").write_text(build_report(environment, manifest, summaries), encoding="utf-8")
        # Avoid printing an absolute workspace path: Windows consoles configured
        # with a legacy code page may not encode non-ASCII folder names.
        self.stdout.write(self.style.SUCCESS("Benchmark report written successfully."))


def metric_summary(values) -> dict[str, float]:
    values = list(values)
    return {"median": round(statistics.median(values), 3), "max": round(max(values), 3)}


def build_report(environment: dict, manifest: list[dict], summaries: dict) -> str:
    lines = [
        "# Image API benchmark report",
        "",
        "## Environment",
        "",
        f"- Timestamp (UTC): {environment['timestamp_utc']}",
        f"- Platform: {environment['platform']}",
        f"- CPU logical cores: {environment['cpu_count']}",
        f"- Memory: {environment['memory_total_bytes']} bytes",
        f"- Python: {environment['python'].splitlines()[0]}",
        f"- pyvips / libvips: {environment['pyvips']} / {environment['libvips']}",
        f"- Measured runs per profile: {environment['runs']} (after {environment['warmup']} warm-up run(s))",
        "",
        "## Input manifest",
        "",
        "| Profile | Dimensions | Bytes | SHA-256 |",
        "| --- | --- | ---: | --- |",
    ]
    lines.extend(
        f"| {item['profile']} | {item['width']}×{item['height']} | {item['bytes']} | `{item['sha256']}` |"
        for item in manifest
    )
    lines.extend(
        [
            "",
            "## Measured summary",
            "",
            "Processing time equals POST latency because this baseline completes all five variants synchronously before responding.",
            "",
            "| Profile | POST median/max (ms) | Peak RSS median/max (bytes) | Storage median/max (bytes) | Files median/max | GET first median/max (ms) | GET second median/max (ms) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for profile, data in summaries.items():
        lines.append(
            f"| {profile} | {data['upload_latency_ms']['median']}/{data['upload_latency_ms']['max']} "
            f"| {data['peak_rss_bytes']['median']}/{data['peak_rss_bytes']['max']} "
            f"| {data['storage_bytes']['median']}/{data['storage_bytes']['max']} "
            f"| {data['file_count']['median']}/{data['file_count']['max']} "
            f"| {data['first_get_latency_ms']['median']}/{data['first_get_latency_ms']['max']} "
            f"| {data['second_get_latency_ms']['median']}/{data['second_get_latency_ms']['max']} |"
        )
    lines.extend(
        [
            "",
            "Raw samples are in `samples.json`; this run removes processed assets after collecting metrics.",
            "",
        ]
    )
    return "\n".join(lines)
