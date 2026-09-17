# Standalone Image API

## Local setup

```powershell
..\venv\Scripts\python.exe -m pip install -r requirements.txt
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

Images are stored under `media/images/`. Each upload keeps its original validated format (`original.jpg`, `original.png`, or `original.webp`) and creates five derived WebP variants. The API contract is documented in `../specs/05-http-api.md`; a Vue 3 client uploads with `FormData` and persists the returned asset `id`.

Database configuration uses one `DATABASE_URL` environment variable. Local development defaults to `sqlite:///db.sqlite3`; production can use `postgresql://user:password@host:5432/database`.

## Test

```powershell
..\venv\Scripts\python.exe manage.py test images.tests
```

## Benchmark

The benchmark generates deterministic JPEG fixtures for 2K, 4K, 8K and 12K, runs one warm-up and three measured uploads for each profile, then writes input checksums, raw samples, environment data, summary JSON and Markdown report.

```powershell
..\venv\Scripts\python.exe manage.py benchmark_images
```

Provide `--output <directory>` for an explicit output directory, or `--profiles 2k,4k` for a limited local smoke benchmark. The command removes generated service assets after each sample; its report and input fixture copies remain under `benchmarks/<UTC timestamp>/`.

## Production readiness

Before deployment, complete [the production readiness checklist](../specs/07-production-readiness.md): persistent media volume, backup/restore, authentication and rate limit at the boundary, secure production settings, disk quota, and monitoring of upload errors, processing duration, storage and missing-file inconsistencies.
