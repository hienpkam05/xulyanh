# Generated manually for the initial standalone Image API schema.

import images.models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ImageAsset",
            fields=[
                ("id", models.CharField(default=images.models.generate_asset_id, editable=False, max_length=36, primary_key=True, serialize=False)),
                ("original_filename", models.CharField(max_length=255)),
                ("original_path", models.CharField(max_length=500)),
                ("original_width", models.PositiveIntegerField()),
                ("original_height", models.PositiveIntegerField()),
                ("original_size", models.PositiveBigIntegerField()),
                ("mime_type", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("processing", "Processing"), ("ready", "Ready"), ("failed", "Failed")], default="processing", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

