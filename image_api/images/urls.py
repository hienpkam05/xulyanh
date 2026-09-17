from django.urls import path

from images.views import image_collection, image_detail, image_original, image_variant


urlpatterns = [
    path("images", image_collection, name="image-collection"),
    # Accept the conventional trailing slash as well as the documented URL.
    path("images/", image_collection),
    path("images/<str:asset_id>", image_detail, name="image-detail"),
    path("images/<str:asset_id>/", image_detail),
    path("images/<str:asset_id>/original", image_original, name="image-original"),
    path("images/<str:asset_id>/original/", image_original),
    path("images/<str:asset_id>/<str:preset>", image_variant, name="image-variant"),
    path("images/<str:asset_id>/<str:preset>/", image_variant),
]
