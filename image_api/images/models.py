import uuid

from django.db import models


def generate_asset_id() -> str:
    """Return an opaque, public identifier that never exposes a DB sequence."""
    return f"img_{uuid.uuid4().hex}"


class ImageAsset(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.CharField(max_length=36, primary_key=True, default=generate_asset_id, editable=False)
    original_filename = models.CharField(max_length=255)
    original_path = models.CharField(max_length=500)
    original_width = models.PositiveIntegerField()
    original_height = models.PositiveIntegerField()
    original_size = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=100)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROCESSING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.id

