import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pyvips
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from images.models import ImageAsset
from images.services import processor


class UploadEndpointTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.previous_cache_max = pyvips.cache_get_max()
        self.previous_cache_max_files = pyvips.cache_get_max_files()
        # Avoid libvips retaining file handles for files in a temporary media root.
        pyvips.cache_set_max(0)
        pyvips.cache_set_max_files(0)
        self.settings_override = override_settings(
            MEDIA_ROOT=Path(self.temporary_directory.name),
            IMAGE_STORAGE_ROOT=Path(self.temporary_directory.name) / "images",
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        gc.collect()
        self.temporary_directory.cleanup()
        pyvips.cache_set_max(self.previous_cache_max)
        pyvips.cache_set_max_files(self.previous_cache_max_files)

    @staticmethod
    def image_upload(width: int, height: int) -> SimpleUploadedFile:
        source = pyvips.Image.black(width, height)
        return SimpleUploadedFile("source.png", source.write_to_buffer(".png"), content_type="image/png")

    def post_image(self, width: int, height: int):
        return self.client.post("/api/v1/images", {"file": self.image_upload(width, height)})

    def test_upload_creates_original_and_all_webp_variants(self):
        response = self.post_image(2000, 1000)

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["presets"], ["thumb", "small", "medium", "large", "xlarge"])
        asset = ImageAsset.objects.get(id=body["id"])
        asset_directory = Path(self.temporary_directory.name) / "images" / asset.id
        self.assertTrue((asset_directory / "original.png").is_file())

        expected_widths = {"thumb": 128, "small": 320, "medium": 640, "large": 1280, "xlarge": 1920}
        for preset, expected_width in expected_widths.items():
            variant = asset_directory / "variants" / f"{preset}.webp"
            self.assertTrue(variant.is_file(), preset)
            self.assertEqual(pyvips.Image.new_from_file(str(variant)).width, expected_width)

    def test_upload_does_not_upscale_small_original(self):
        response = self.post_image(500, 250)

        self.assertEqual(response.status_code, 201, response.content)
        asset_id = response.json()["id"]
        variants = Path(self.temporary_directory.name) / "images" / asset_id / "variants"
        self.assertEqual(pyvips.Image.new_from_file(str(variants / "large.webp")).width, 500)
        self.assertEqual(pyvips.Image.new_from_file(str(variants / "xlarge.webp")).width, 500)

    def test_variant_failure_removes_partial_files_and_ready_record(self):
        original_resize = processor.resize_variant
        calls = 0

        def fail_on_third_variant(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise pyvips.Error("simulated write error")
            return original_resize(*args, **kwargs)

        with patch("images.services.processor.resize_variant", side_effect=fail_on_third_variant):
            response = self.post_image(1000, 500)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "processing_failed")
        self.assertEqual(ImageAsset.objects.count(), 0)
        image_root = Path(self.temporary_directory.name) / "images"
        self.assertFalse(image_root.exists() and any(image_root.iterdir()))
