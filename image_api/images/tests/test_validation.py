from unittest.mock import patch

import pyvips
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from images.services.validation import ImageValidationError, validate_upload


class FakeImage:
    def __init__(self, loader="jpegload_buffer", width=1200, height=800):
        self.loader = loader
        self.width = width
        self.height = height

    def get(self, field):
        if field != "vips-loader":
            raise pyvips.Error("missing field")
        return self.loader


class ValidationTests(SimpleTestCase):
    def upload(self, content=b"encoded-image", size=None):
        if size is None:
            size = len(content)
        file = SimpleUploadedFile("pretends-to-be.png", content, content_type="image/png")
        file.size = size
        return file

    def assert_validation_error(self, expected_code, expected_status, upload, image=None):
        with patch("images.services.validation.pyvips.Image.new_from_buffer", return_value=image or FakeImage()):
            with self.assertRaises(ImageValidationError) as context:
                validate_upload(upload)
        self.assertEqual(context.exception.code, expected_code)
        self.assertEqual(context.exception.status_code, expected_status)

    def test_valid_jpeg_metadata_is_returned_independent_of_filename(self):
        upload = self.upload()
        with patch("images.services.validation.pyvips.Image.new_from_buffer", return_value=FakeImage()):
            validated = validate_upload(upload)

        self.assertEqual(validated.mime_type, "image/jpeg")
        self.assertEqual(validated.extension, "jpg")
        self.assertEqual((validated.width, validated.height, validated.size), (1200, 800, len(b"encoded-image")))
        self.assertEqual(upload.read(), b"encoded-image")

    def test_png_and_webp_loaders_are_accepted(self):
        for loader, mime_type, extension in (
            ("pngload_buffer", "image/png", "png"),
            ("webpload_buffer", "image/webp", "webp"),
        ):
            with self.subTest(loader=loader):
                with patch("images.services.validation.pyvips.Image.new_from_buffer", return_value=FakeImage(loader=loader)):
                    validated = validate_upload(self.upload())
                self.assertEqual((validated.mime_type, validated.extension), (mime_type, extension))

    def test_missing_or_empty_file_is_rejected(self):
        self.assert_validation_error("invalid_file", 400, None)
        self.assert_validation_error("invalid_file", 400, self.upload(b""))

    @override_settings(MAX_FILE_SIZE=5)
    def test_file_larger_than_byte_limit_is_rejected_before_decode(self):
        self.assert_validation_error("file_too_large", 413, self.upload(b"six-bytes"))

    def test_unsupported_decoder_loader_is_rejected(self):
        self.assert_validation_error("unsupported_media_type", 415, self.upload(), FakeImage(loader="gifload"))

    def test_decode_failure_is_rejected(self):
        with patch("images.services.validation.pyvips.Image.new_from_buffer", side_effect=pyvips.Error("corrupt")):
            with self.assertRaises(ImageValidationError) as context:
                validate_upload(self.upload())
        self.assertEqual((context.exception.code, context.exception.status_code), ("invalid_image", 422))

    @override_settings(MAX_PIXELS=1_000)
    def test_pixel_limit_is_enforced(self):
        self.assert_validation_error("image_dimensions_exceeded", 422, self.upload(), FakeImage(width=100, height=100))
