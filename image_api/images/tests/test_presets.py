from django.test import SimpleTestCase

from images.services.presets import IMAGE_PRESETS, is_valid_preset, preset_names


class PresetTests(SimpleTestCase):
    def test_fixed_presets_match_public_contract(self):
        self.assertEqual(preset_names(), ("thumb", "small", "medium", "large", "xlarge"))
        self.assertEqual(IMAGE_PRESETS["thumb"], {"width": 128, "quality": 80})
        self.assertEqual(IMAGE_PRESETS["xlarge"], {"width": 1920, "quality": 84})

    def test_only_allowlisted_presets_are_valid(self):
        self.assertTrue(is_valid_preset("medium"))
        self.assertFalse(is_valid_preset("custom"))
        self.assertFalse(is_valid_preset("../../secret"))
