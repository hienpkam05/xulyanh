from django.test import TestCase

from images.models import ImageAsset


class ImageAssetTests(TestCase):
    def create_asset(self) -> ImageAsset:
        return ImageAsset.objects.create(
            original_filename="source.jpg",
            original_path="images/pending/original.jpg",
            original_width=1200,
            original_height=800,
            original_size=1024,
            mime_type="image/jpeg",
        )

    def test_default_public_id_uses_img_prefix(self):
        asset = self.create_asset()

        self.assertTrue(asset.id.startswith("img_"))
        self.assertEqual(len(asset.id), 36)

    def test_generated_ids_are_unique(self):
        first = self.create_asset()
        second = self.create_asset()

        self.assertNotEqual(first.id, second.id)

