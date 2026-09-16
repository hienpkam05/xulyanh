# PIPELINE CŨ — API XỬ LÝ ẢNH RIÊNG — PREGENERATE VARIANTS

## 0.1 Bước tiền xử lý ở Vue 3 — HTML5 Canvas

Trước khi gọi Image API, giao diện Vue 3 thực hiện resize và nén trên trình duyệt bằng **HTML5 Canvas**:

```text
User chọn ảnh gốc
        ↓
Hiển thị dung lượng gốc
        ↓
createImageBitmap + Canvas resize (giữ tỷ lệ, không upscale)
        ↓
Canvas encode WebP
        ↓
Hiển thị dung lượng sau Canvas
        ↓
POST file WebP đã xử lý vào Image API
```

Thiết lập UI mặc định: max width 4096 px (có thể chỉnh 1280–8192) và WebP quality 86% (có thể chỉnh 50–100). Canvas giảm byte upload, thời gian server và dung lượng original. Image API vẫn phải validate MIME/size/dimensions: client có thể bypass Canvas và API không tin metadata do browser gửi.

## 0. Phạm vi hiện tại

Hiện tại phần tối ưu ảnh được làm thành **một API/service riêng**, không nhét logic `pyvips` trực tiếp vào API Media/Tour hiện có.

Mục tiêu của tài liệu này là để Codex có thể triển khai và benchmark pipeline cũ độc lập.

```text
Main Backend / FE
        ↓ HTTP
Standalone Image API
        ↓
pyvips
        ↓
Storage
```

Trong giai đoạn POC:

- Chỉ làm Image API.
- Chưa cần sửa Viewer / Tour Builder.
- Chưa cần CDN.
- Chưa bắt buộc Redis / Celery.
- Có thể dùng local disk để benchmark.
- API contract nên giữ ổn định để sau này đổi pipeline mà client không phải đổi.

---

# 1. Ý tưởng pipeline cũ

Pipeline cũ sinh sẵn toàn bộ kích thước ngay khi upload:

```text
POST ảnh vào Image API
        ↓
Validate
        ↓
Save Original
        ↓
pyvips
        ↓
Generate ALL presets
        ↓
thumb.webp
small.webp
medium.webp
large.webp
xlarge.webp
        ↓
Save Storage
        ↓
Return asset_id
```

Khi client cần ảnh:

```text
GET /api/v1/images/{asset_id}/medium
        ↓
File đã tồn tại
        ↓
Return ngay
```

Không có resize lúc view.

---

# 2. Kiến trúc service riêng

```text
┌──────────────────────┐
│ Main Django / Client │
└──────────┬───────────┘
           │ HTTP
           ▼
┌──────────────────────┐
│    IMAGE API         │
│ Django + DRF         │
│                      │
│ upload               │
│ validate             │
│ generate variants    │
│ serve image          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ pyvips / libvips     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Local/Object Storage │
└──────────────────────┘
```

Main backend không cần biết cách resize.

Nó chỉ cần biết:

```text
asset_id
```

hoặc URL ảnh trả về từ Image API.

---

# 3. Công nghệ

Image API:

```text
Python
Django
Django REST Framework
```

Image engine:

```bash
pip install "pyvips[binary]"
```

Code:

```python
import pyvips
```

POC storage:

```text
local disk
```

Production sau này:

```text
S3 / MinIO / R2
```

---

# 4. Public API contract

Nên giữ API contract giống pipeline mới để dễ so sánh.

## 4.1 Upload

```http
POST /api/v1/images
Content-Type: multipart/form-data
```

Body:

```text
file=<image>
```

Response:

```json
{
  "id": "img_123",
  "width": 12000,
  "height": 6000,
  "status": "ready",
  "presets": [
    "thumb",
    "small",
    "medium",
    "large",
    "xlarge"
  ]
}
```

Pipeline cũ chỉ trả `ready` sau khi toàn bộ preset đã được generate xong.

---

## 4.2 Lấy ảnh theo preset

```http
GET /api/v1/images/{id}/{preset}
```

Ví dụ:

```http
GET /api/v1/images/img_123/medium
```

Response:

```text
Content-Type: image/webp
```

---

## 4.3 Metadata

```http
GET /api/v1/images/{id}
```

Response:

```json
{
  "id": "img_123",
  "width": 12000,
  "height": 6000,
  "status": "ready",
  "available_presets": [
    "thumb",
    "small",
    "medium",
    "large",
    "xlarge"
  ]
}
```

---

## 4.4 Delete

```http
DELETE /api/v1/images/{id}
```

Phải xóa:

```text
original
+
toàn bộ variants
+
metadata record
```

---

# 5. Preset cố định

```python
IMAGE_PRESETS = {
    "thumb": {
        "width": 128,
        "quality": 80,
    },
    "small": {
        "width": 320,
        "quality": 80,
    },
    "medium": {
        "width": 640,
        "quality": 82,
    },
    "large": {
        "width": 1280,
        "quality": 82,
    },
    "xlarge": {
        "width": 1920,
        "quality": 84,
    },
}
```

Không cho client truyền:

```text
?w=437
?w=821
```

Mục đích:

- API contract ổn định.
- Không sinh vô hạn kích thước.
- Dễ benchmark với pipeline mới.

---

# 6. Pipeline POST /images

```text
[1] API nhận multipart file
        ↓
[2] Validate MIME / size
        ↓
[3] Decode test
        ↓
[4] Validate dimensions / max pixels
        ↓
[5] Tạo image_id
        ↓
[6] Save original
        ↓
[7] Load original bằng pyvips
        ↓
[8] Generate thumb
        ↓
[9] Generate small
        ↓
[10] Generate medium
        ↓
[11] Generate large
        ↓
[12] Generate xlarge
        ↓
[13] Save metadata
        ↓
[14] Return status=ready
```

---

# 7. Validate ảnh

Config ví dụ:

```python
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_WIDTH = 16000
MAX_HEIGHT = 16000
MAX_PIXELS = 120_000_000
```

Phải kiểm tra:

```text
MIME
file size
width
height
width × height
decode được
```

Không chỉ kiểm tra extension.

---

# 8. Không upscale

Ví dụ:

```text
original width = 500
xlarge target = 1920
```

Không generate ảnh 1920.

Output tối đa:

```text
500
```

Rule:

```python
target_width = min(
    original_width,
    preset_width,
)
```

---

# 9. Resize bằng pyvips

Pseudo-code:

```python
import pyvips

def resize_variant(original_path, output_path, width, quality):
    image = pyvips.Image.new_from_file(
        original_path,
        access="sequential",
    )

    target_width = min(width, image.width)

    if target_width < image.width:
        scale = target_width / image.width
        image = image.resize(scale)

    image.write_to_file(
        output_path,
        Q=quality,
    )
```

Output ưu tiên:

```text
WebP
```

---

# 10. Storage structure

```text
image-storage/
└── img_123/
    ├── original.jpg
    └── variants/
        ├── thumb.webp
        ├── small.webp
        ├── medium.webp
        ├── large.webp
        └── xlarge.webp
```

Ngay sau upload, tất cả variant đều tồn tại.

---

# 11. Model riêng của Image API

Ví dụ:

```text
ImageAsset
--------------------------------
id
original_path
original_width
original_height
original_size
mime_type
status
created_at
updated_at
```

Không bắt buộc tạo row cho từng variant.

Có thể suy ra path bằng convention:

```text
{asset_id}/variants/{preset}.webp
```

---

# 12. Main Backend tích hợp như nào?

Main Backend không gọi `pyvips`.

Flow:

```text
Main Backend
↓
POST file → Image API
↓
Image API trả:
id = img_123
↓
Main Backend lưu:
image_service_id = img_123
```

Khi cần URL:

```text
/api/v1/images/img_123/medium
```

Hoặc Main Backend có thể trả URL này về FE.

---

# 13. Ưu điểm của API riêng

```text
Main project không chứa logic xử lý pixel.
Có thể test riêng.
Có thể benchmark riêng.
Có thể thay pipeline mà API contract giữ nguyên.
Có thể scale Image API độc lập sau này.
Lỗi xử lý ảnh không làm code Media/Tour phình ra.
```

---

# 14. RAM / CPU

Pipeline cũ vẫn dùng CPU/RAM khi upload:

```text
12K upload
↓
generate 5 presets
↓
CPU/RAM tăng
↓
generate xong
↓
RAM giải phóng
```

Nhưng lúc GET:

```text
GET medium
↓
return file có sẵn
```

không chạy pyvips.

---

# 15. Điểm yếu lớn nhất: Storage

Ví dụ:

```text
100.000 original
5 presets
```

Có thể có:

```text
100.000 original
+
500.000 derived files
=
600.000 files
```

Kể cả `xlarge` chưa từng được client request.

---

# 16. Upload đồng thời

API riêng vẫn có thể quá tải nếu nhiều ảnh lớn cùng upload.

Ví dụ:

```text
100 ảnh 12K
↓
100 request generate 5 preset
↓
CPU/RAM tăng mạnh
```

POC:

```text
benchmark trước
```

Production có thể thêm:

```text
queue
worker
concurrency limit
```

Nhưng đây chưa phải yêu cầu bắt buộc cho bản API benchmark đầu tiên.

---

# 17. Cấu trúc code cho Codex

```text
image_api/
├── manage.py
├── config/
└── images/
    ├── models.py
    ├── serializers.py
    ├── urls.py
    ├── views.py
    ├── services/
    │   ├── validation.py
    │   ├── presets.py
    │   ├── processor.py
    │   └── storage.py
    └── tests/
        ├── test_upload.py
        ├── test_presets.py
        └── test_validation.py
```

Không viết toàn bộ xử lý ảnh trong `views.py`.

`views.py` chỉ:

```text
parse request
→ gọi service
→ trả response
```

---

# 18. Acceptance Criteria cho Codex

```text
[ ] Đây là API/service riêng.
[ ] Không sửa logic Media/Tour hiện tại để xử lý ảnh.
[ ] POST /api/v1/images hoạt động.
[ ] Validate ảnh.
[ ] Lưu original.
[ ] Generate tất cả presets lúc POST.
[ ] WebP output.
[ ] Không upscale.
[ ] GET /api/v1/images/{id}/{preset} hoạt động.
[ ] Invalid preset → 400/404.
[ ] GET metadata hoạt động.
[ ] DELETE xóa original + variants.
[ ] Test ảnh 2K.
[ ] Test ảnh 4K.
[ ] Test ảnh 8K.
[ ] Test ảnh 12K.
[ ] Benchmark peak RAM.
[ ] Benchmark processing time.
[ ] Benchmark storage generated.
```

---

# 19. Benchmark

Dùng cùng một bộ test cho pipeline cũ và mới:

```text
2K
4K
8K
12K
```

Đo:

| Metric | Ý nghĩa |
|---|---|
| Upload latency | POST mất bao lâu |
| Peak RAM | RAM cao nhất |
| CPU | tải CPU |
| Storage | tổng dung lượng sinh ra |
| File count | tổng số file |
| First GET | GET đầu tiên |
| Second GET | GET lần sau |

Pipeline cũ kỳ vọng:

```text
Upload chậm hơn
Storage cao hơn
First GET rất nhanh
Second GET rất nhanh
```

---

# 20. Pipeline cuối cùng

```text
CLIENT / MAIN BACKEND
        ↓
POST /api/v1/images
        ↓
STANDALONE IMAGE API
        ↓
VALIDATE
        ↓
SAVE ORIGINAL
        ↓
PYVIPS
        ↓
GENERATE ALL PRESETS
        ↓
SAVE ALL VARIANTS
        ↓
RETURN asset_id
```

View:

```text
GET /api/v1/images/{id}/medium
        ↓
IMAGE API
        ↓
medium.webp đã có
        ↓
RETURN
```

Đây là baseline để so sánh với pipeline mới.
