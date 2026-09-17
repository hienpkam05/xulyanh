import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pyvips
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from images.models import ImageAsset


class ImageApiTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.previous_cache_max = pyvips.cache_get_max()
        self.previous_cache_max_files = pyvips.cache_get_max_files()
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

    def create_ready_asset(self, width=800, height=400) -> ImageAsset:
        source = pyvips.Image.black(width, height)
        upload = SimpleUploadedFile("source.png", source.write_to_buffer(".png"), content_type="image/png")
        response = self.client.post("/api/v1/images", {"file": upload})
        self.assertEqual(response.status_code, 201, response.content)
        return ImageAsset.objects.get(id=response.json()["id"])

    def test_metadata_returns_only_public_ready_contract(self):
        asset = self.create_ready_asset()

        response = self.client.get(f"/api/v1/images/{asset.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": asset.id,
                "width": 800,
                "height": 400,
                "status": "ready",
                "available_presets": ["thumb", "small", "medium", "large", "xlarge"],
            },
        )

    def test_metadata_returns_404_for_missing_asset(self):
        response = self.client.get("/api/v1/images/img_0123456789abcdef0123456789abcdef")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "asset_not_found")

    def test_variant_streams_pregenerated_webp_without_processing(self):
        asset = self.create_ready_asset()

        with (
            patch("images.views.create_image_asset") as create_asset,
            patch("images.services.processor.pyvips.Image.new_from_file") as vips_loader,
        ):
            response = self.client.get(f"/api/v1/images/{asset.id}/medium")
            body = b"".join(response.streaming_content)
            response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("immutable", response["Cache-Control"])
        self.assertTrue(body.startswith(b"RIFF"))
        create_asset.assert_not_called()
        vips_loader.assert_not_called()

    def test_original_streams_the_uploaded_png_without_conversion(self):
        asset = self.create_ready_asset()

        response = self.client.get(f"/api/v1/images/{asset.id}/original")
        body = b"".join(response.streaming_content)
        response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertTrue(body.startswith(b"\x89PNG"))

    def test_invalid_preset_and_missing_variant_return_404(self):
        asset = self.create_ready_asset()
        invalid = self.client.get(f"/api/v1/images/{asset.id}/custom")
        missing_variant = Path(self.temporary_directory.name) / "images" / asset.id / "variants" / "medium.webp"
        missing_variant.unlink()
        unavailable = self.client.get(f"/api/v1/images/{asset.id}/medium")

        self.assertEqual((invalid.status_code, invalid.json()["code"]), (404, "preset_not_found"))
        self.assertEqual((unavailable.status_code, unavailable.json()["code"]), (404, "variant_not_available"))

    def test_processing_asset_does_not_expose_variants(self):
        asset = self.create_ready_asset()
        asset.status = ImageAsset.Status.PROCESSING
        asset.save(update_fields=["status"])

        response = self.client.get(f"/api/v1/images/{asset.id}/thumb")

        self.assertEqual((response.status_code, response.json()["code"]), (404, "variant_not_available"))

    def test_delete_removes_storage_and_database_record(self):
        asset = self.create_ready_asset()
        asset_directory = Path(self.temporary_directory.name) / "images" / asset.id

        response = self.client.delete(f"/api/v1/images/{asset.id}")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ImageAsset.objects.filter(id=asset.id).exists())
        self.assertFalse(asset_directory.exists())
        self.assertEqual(self.client.get(f"/api/v1/images/{asset.id}").status_code, 404)

    def test_delete_failure_keeps_database_record(self):
        asset = self.create_ready_asset()
        storage = Mock()
        storage.delete_asset_tree.side_effect = OSError("disk failure")

        with patch("images.views.get_image_storage", return_value=storage):
            response = self.client.delete(f"/api/v1/images/{asset.id}")

        self.assertEqual((response.status_code, response.json()["code"]), (500, "deletion_failed"))
        self.assertTrue(ImageAsset.objects.filter(id=asset.id).exists())
