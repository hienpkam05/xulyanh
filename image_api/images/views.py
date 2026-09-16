from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from images.services.processor import ImageProcessingError, create_image_asset
from images.models import ImageAsset
from images.services.presets import is_valid_preset, preset_names
from images.services.storage import StoragePathError, get_image_storage
from images.services.validation import ImageValidationError


@require_GET
def health_check(request):
    """Liveness endpoint: it intentionally does not depend on DB or storage."""
    return JsonResponse({"status": "ok"})


def error_response(code: str, detail: str, status_code: int) -> Response:
    return Response({"code": code, "detail": detail}, status=status_code)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def image_collection(request):
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return error_response("invalid_file", "A non-empty file is required.", status.HTTP_400_BAD_REQUEST)

    try:
        asset = create_image_asset(uploaded_file)
    except ImageValidationError as error:
        return error_response(error.code, error.detail, error.status_code)
    except ImageProcessingError:
        return error_response(
            "processing_failed",
            "The image could not be processed.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "id": asset.id,
            "width": asset.original_width,
            "height": asset.original_height,
            "status": asset.status,
            "presets": ["thumb", "small", "medium", "large", "xlarge"],
        },
        status=status.HTTP_201_CREATED,
    )


def get_asset_or_404(asset_id: str) -> ImageAsset | None:
    try:
        return ImageAsset.objects.get(id=asset_id)
    except ImageAsset.DoesNotExist:
        return None


def metadata_response(asset: ImageAsset) -> Response:
    available_presets = list(preset_names()) if asset.status == ImageAsset.Status.READY else []
    return Response(
        {
            "id": asset.id,
            "width": asset.original_width,
            "height": asset.original_height,
            "status": asset.status,
            "available_presets": available_presets,
        }
    )


@api_view(["GET", "DELETE"])
def image_detail(request, asset_id: str):
    asset = get_asset_or_404(asset_id)
    if asset is None:
        return error_response("asset_not_found", "Image asset was not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return metadata_response(asset)

    try:
        get_image_storage().delete_asset_tree(asset.id)
    except (OSError, StoragePathError):
        return error_response(
            "deletion_failed",
            "The image asset could not be deleted.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    asset.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def image_variant(request, asset_id: str, preset: str):
    if not is_valid_preset(preset):
        return error_response("preset_not_found", "Image preset was not found.", status.HTTP_404_NOT_FOUND)

    asset = get_asset_or_404(asset_id)
    if asset is None:
        return error_response("asset_not_found", "Image asset was not found.", status.HTTP_404_NOT_FOUND)
    if asset.status != ImageAsset.Status.READY:
        return error_response("variant_not_available", "Image variant is not available.", status.HTTP_404_NOT_FOUND)

    try:
        variant_path = get_image_storage().open_variant(asset.id, preset)
    except StoragePathError:
        return error_response("variant_not_available", "Image variant is not available.", status.HTTP_404_NOT_FOUND)

    if not variant_path.is_file():
        return error_response("variant_not_available", "Image variant is not available.", status.HTTP_404_NOT_FOUND)

    response = FileResponse(variant_path.open("rb"), content_type="image/webp")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
