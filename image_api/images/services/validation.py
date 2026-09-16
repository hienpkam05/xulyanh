"""Upload validation based on decoded image metadata, not client-controlled names."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyvips
from django.conf import settings


LOADER_MIME_TYPES = {
    "jpegload": ("image/jpeg", "jpg"),
    "pngload": ("image/png", "png"),
    "webpload": ("image/webp", "webp"),
}


class ImageValidationError(Exception):
    def __init__(self, code: str, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ValidatedImage:
    mime_type: str
    extension: str
    width: int
    height: int
    size: int


def _loader_details(image: pyvips.Image) -> tuple[str, str] | None:
    try:
        loader = image.get("vips-loader")
    except pyvips.Error:
        return None

    # libvips may append a source suffix, for example "jpegload_buffer".
    for prefix, details in LOADER_MIME_TYPES.items():
        if str(loader).startswith(prefix):
            return details
    return None


def _load_image(uploaded_file) -> pyvips.Image:
    try:
        try:
            temporary_path = uploaded_file.temporary_file_path()
        except (AttributeError, OSError):
            temporary_path = None

        if temporary_path:
            return pyvips.Image.new_from_file(str(Path(temporary_path)), access="sequential")

        # Django keeps only small uploads in memory. This reads compressed bytes,
        # not a decoded raster, and is reset before the storage service copies it.
        return pyvips.Image.new_from_buffer(uploaded_file.read(), "", access="sequential")
    except (pyvips.Error, OSError, ValueError) as error:
        raise ImageValidationError("invalid_image", "The uploaded file is not a decodable image.", 422) from error
    finally:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)


def validate_upload(uploaded_file) -> ValidatedImage:
    """Validate one Django uploaded file and return metadata safe for persistence."""
    if uploaded_file is None or getattr(uploaded_file, "size", 0) <= 0:
        raise ImageValidationError("invalid_file", "A non-empty file is required.", 400)

    if uploaded_file.size > settings.MAX_FILE_SIZE:
        raise ImageValidationError("file_too_large", "The uploaded file exceeds the maximum allowed size.", 413)

    image = _load_image(uploaded_file)
    mime_details = _loader_details(image)
    if mime_details is None:
        raise ImageValidationError("unsupported_media_type", "Only JPEG, PNG, and WebP images are supported.", 415)

    width, height = image.width, image.height
    if width <= 0 or height <= 0:
        raise ImageValidationError("invalid_image", "The uploaded image has invalid dimensions.", 422)

    if width > settings.MAX_WIDTH or height > settings.MAX_HEIGHT or width * height > settings.MAX_PIXELS:
        raise ImageValidationError(
            "image_dimensions_exceeded",
            "The uploaded image exceeds the configured dimension limit.",
            422,
        )

    mime_type, extension = mime_details
    return ValidatedImage(mime_type=mime_type, extension=extension, width=width, height=height, size=uploaded_file.size)

