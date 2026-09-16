"""Local-disk storage for image assets.

All paths accepted by this module are validated before touching the filesystem.
The public API deals in relative keys; only this adapter resolves local paths.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from django.conf import settings

from images.services.presets import is_valid_preset


ASSET_ID_PATTERN = re.compile(r"^img_[0-9a-f]{32}$")


class StoragePathError(ValueError):
    """Raised when a storage key could escape the image storage root."""


class LocalImageStorage:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or settings.IMAGE_STORAGE_ROOT).resolve()

    def _validate_asset_id(self, asset_id: str) -> None:
        if not ASSET_ID_PATTERN.fullmatch(asset_id):
            raise StoragePathError("Invalid asset ID.")

    def _asset_directory(self, asset_id: str) -> Path:
        self._validate_asset_id(asset_id)
        return self.absolute_path(asset_id)

    def absolute_path(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise StoragePathError("Storage path must stay within the image storage root.")

        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise StoragePathError("Storage path must stay within the image storage root.") from error
        return candidate

    def save_original(self, asset_id: str, uploaded_file, extension: str) -> str:
        if extension not in {"jpg", "png", "webp"}:
            raise StoragePathError("Unsupported original file extension.")

        asset_directory = self._asset_directory(asset_id)
        relative_path = Path(asset_id) / f"original.{extension}"
        destination = self.absolute_path(relative_path)
        asset_directory.mkdir(parents=True, exist_ok=False)

        try:
            with destination.open("wb") as output:
                for chunk in uploaded_file.chunks():
                    output.write(chunk)
        except Exception:
            # This directory is new for an asset ID and may safely be removed on copy failure.
            if asset_directory.exists():
                shutil.rmtree(asset_directory)
            raise
        finally:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)

        return relative_path.as_posix()

    def variant_path(self, asset_id: str, preset: str) -> str:
        self._validate_asset_id(asset_id)
        if not is_valid_preset(preset):
            raise StoragePathError("Invalid preset.")
        return (Path(asset_id) / "variants" / f"{preset}.webp").as_posix()

    def open_variant(self, asset_id: str, preset: str) -> Path:
        return self.absolute_path(self.variant_path(asset_id, preset))

    def asset_exists(self, asset_id: str) -> bool:
        return self._asset_directory(asset_id).is_dir()

    def delete_asset_tree(self, asset_id: str) -> None:
        asset_directory = self._asset_directory(asset_id)
        if asset_directory.exists():
            shutil.rmtree(asset_directory)


def get_image_storage() -> LocalImageStorage:
    return LocalImageStorage()

