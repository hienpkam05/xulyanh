"""Synchronous pregeneration pipeline for one uploaded image."""

from __future__ import annotations

import logging
from pathlib import Path

import pyvips
from django.db import transaction
from django.utils.text import get_valid_filename

from images.models import ImageAsset, generate_asset_id
from images.services.presets import IMAGE_PRESETS
from images.services.storage import LocalImageStorage, get_image_storage
from images.services.validation import ValidatedImage, validate_upload


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Safe application error for an unexpected storage or libvips failure."""


def _safe_original_filename(uploaded_file) -> str:
    raw_name = str(getattr(uploaded_file, "name", "upload"))
    basename = raw_name.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    return get_valid_filename(basename)[:255] or "upload"


def resize_variant(original_path: Path, output_path: Path, width: int, quality: int) -> None:
    """Write one WebP variant while preserving aspect ratio and never upscaling."""
    image = pyvips.Image.new_from_file(str(original_path), access="sequential")
    target_width = min(width, image.width)
    if target_width < image.width:
        image = image.resize(target_width / image.width)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.write_to_file(str(output_path), Q=quality)


def _record_cleanup_failure(asset_id: str, metadata: ValidatedImage, original_filename: str, original_path: str) -> None:
    """Keep an auditable failed record only when partial files could not be removed."""
    try:
        ImageAsset.objects.create(
            id=asset_id,
            original_filename=original_filename,
            original_path=original_path,
            original_width=metadata.width,
            original_height=metadata.height,
            original_size=metadata.size,
            mime_type=metadata.mime_type,
            status=ImageAsset.Status.FAILED,
        )
    except Exception:
        logger.exception("Could not record cleanup failure for image asset %s", asset_id)


def create_image_asset(uploaded_file, storage: LocalImageStorage | None = None) -> ImageAsset:
    """Create a ready asset or raise a typed error without exposing partial output.

    Validation errors intentionally propagate to the HTTP layer. Any processing
    failure rolls back the normal record and removes the partial asset directory.
    """
    metadata = validate_upload(uploaded_file)
    storage = storage or get_image_storage()
    asset_id = generate_asset_id()
    original_filename = _safe_original_filename(uploaded_file)
    original_path = f"{asset_id}/original.{metadata.extension}"

    try:
        with transaction.atomic():
            asset = ImageAsset.objects.create(
                id=asset_id,
                original_filename=original_filename,
                original_path="",
                original_width=metadata.width,
                original_height=metadata.height,
                original_size=metadata.size,
                mime_type=metadata.mime_type,
                status=ImageAsset.Status.PROCESSING,
            )
            asset.original_path = storage.save_original(asset_id, uploaded_file, metadata.extension)
            original_file = storage.absolute_path(asset.original_path)

            for preset, options in IMAGE_PRESETS.items():
                variant_file = storage.absolute_path(storage.variant_path(asset_id, preset))
                resize_variant(original_file, variant_file, **options)

            asset.status = ImageAsset.Status.READY
            asset.save(update_fields=["original_path", "status", "updated_at"])
            return asset
    except Exception as error:
        logger.exception("Image processing failed for asset %s", asset_id)
        try:
            storage.delete_asset_tree(asset_id)
        except Exception:
            logger.exception("Could not remove partial files for image asset %s", asset_id)
            _record_cleanup_failure(asset_id, metadata, original_filename, original_path)
        raise ImageProcessingError("Image processing failed.") from error

