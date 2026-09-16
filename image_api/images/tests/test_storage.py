from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from images.services.storage import LocalImageStorage, StoragePathError


class LocalImageStorageTests(SimpleTestCase):
    asset_id = "img_0123456789abcdef0123456789abcdef"
    other_asset_id = "img_fedcba9876543210fedcba9876543210"

    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.storage = LocalImageStorage(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_save_original_uses_expected_media_layout(self):
        upload = SimpleUploadedFile("untrusted-name.jpg", b"image-data", content_type="text/plain")

        relative_path = self.storage.save_original(self.asset_id, upload, "jpg")

        self.assertEqual(relative_path, f"{self.asset_id}/original.jpg")
        self.assertEqual(self.storage.absolute_path(relative_path).read_bytes(), b"image-data")
        self.assertEqual(upload.read(), b"image-data")

    def test_variant_path_uses_only_allowlisted_preset(self):
        self.assertEqual(self.storage.variant_path(self.asset_id, "medium"), f"{self.asset_id}/variants/medium.webp")
        with self.assertRaises(StoragePathError):
            self.storage.variant_path(self.asset_id, "../../secret")

    def test_path_traversal_and_invalid_asset_id_are_rejected(self):
        with self.assertRaises(StoragePathError):
            self.storage.absolute_path("../outside")
        with self.assertRaises(StoragePathError):
            self.storage.save_original("../outside", SimpleUploadedFile("a.jpg", b"a"), "jpg")

    def test_delete_removes_only_requested_asset_tree(self):
        self.storage.save_original(self.asset_id, SimpleUploadedFile("a.jpg", b"first"), "jpg")
        self.storage.save_original(self.other_asset_id, SimpleUploadedFile("b.jpg", b"second"), "jpg")

        self.storage.delete_asset_tree(self.asset_id)

        self.assertFalse(self.storage.asset_exists(self.asset_id))
        self.assertTrue(self.storage.asset_exists(self.other_asset_id))

