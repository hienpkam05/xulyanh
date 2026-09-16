# Giai đoạn 2 — Domain, preset và local storage

## Mục tiêu

Định nghĩa dữ liệu bền vững và một abstraction storage đủ để thay local disk bằng S3/MinIO/R2 sau này mà không đổi HTTP contract.

## Model `ImageAsset`

| Field | Kiểu / ràng buộc | Ý nghĩa |
| --- | --- | --- |
| `id` | `CharField`, primary key, dạng `img_<uuid4 hex>` | ID public, không tuần tự |
| `original_filename` | string, chỉ basename đã làm sạch | Phục vụ audit/debug, không dùng tạo path |
| `original_path` | string | Relative key của original |
| `original_width`, `original_height` | positive integer | Kích thước đã decode |
| `original_size` | positive integer | Số byte request upload |
| `mime_type` | string | MIME đã xác thực/được decoder nhận |
| `status` | enum `processing`, `ready`, `failed` | Trạng thái lifecycle |
| `created_at`, `updated_at` | timezone-aware datetime | Audit |

Không tạo model variant trong POC: path variant suy ra từ convention. `failed` chỉ tồn tại nếu một record đã được tạo và cleanup không thể hoàn thành; POST lỗi không được trả `ready`.

## Preset cố định

```python
IMAGE_PRESETS = {
    "thumb": {"width": 128, "quality": 80},
    "small": {"width": 320, "quality": 80},
    "medium": {"width": 640, "quality": 82},
    "large": {"width": 1280, "quality": 82},
    "xlarge": {"width": 1920, "quality": 84},
}
```

Đặt hằng số trong `images/services/presets.py`, export helper `is_valid_preset(name)` và không cho URL query `w`/`h` ảnh hưởng output.

## Storage interface

Tạo `images/services/storage.py` với interface có các thao tác sau:

- `save_original(asset_id, uploaded_file, extension) -> relative_path`
- `variant_path(asset_id, preset) -> relative_path`
- `absolute_path(relative_path) -> Path` (chỉ local implementation)
- `open_variant(asset_id, preset) -> file handle/path`
- `asset_exists(asset_id) -> bool`
- `delete_asset_tree(asset_id) -> None`

Layout local disk trong `MEDIA_ROOT`:

```text
media/
└── images/
    └── img_<uuid>/
        ├── original.<safe-extension>
        └── variants/
            ├── thumb.webp
            ├── small.webp
            ├── medium.webp
            ├── large.webp
            └── xlarge.webp
```

`safe-extension` chỉ lấy từ MIME đã allowlist (không tin extension client). Resolver phải từ chối `asset_id`, preset hay relative path chứa separator/path traversal. Xóa chỉ được phép xóa chính xác thư mục asset dưới `MEDIA_ROOT/images` sau khi kiểm tra resolved path còn nằm trong root.

## Done

- Migration tạo model và test tạo được `img_` ID duy nhất.
- Unit test xác nhận mọi preset có path đúng, không có input client nào tạo được path outside storage root.
- Unit test `delete_asset_tree` xóa original và toàn bộ variants của duy nhất một asset.
