"""The finite, public set of pregenerated image sizes."""

IMAGE_PRESETS = {
    "thumb": {"width": 128, "quality": 80},
    "small": {"width": 320, "quality": 80},
    "medium": {"width": 640, "quality": 82},
    "large": {"width": 1280, "quality": 82},
    "xlarge": {"width": 1920, "quality": 84},
}


def is_valid_preset(name: str) -> bool:
    return name in IMAGE_PRESETS


def preset_names() -> tuple[str, ...]:
    return tuple(IMAGE_PRESETS.keys())

