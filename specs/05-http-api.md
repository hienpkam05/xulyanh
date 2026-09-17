# Giai đoạn 5 — HTTP API contract

Base path: `/api/v1/images`. API không cần authentication ở POC; trước production phải đặt lớp auth/gateway ở service boundary mà không thay body contract.

## 1. Upload

```http
POST /api/v1/images
Content-Type: multipart/form-data

file=<image>
```

Vue 3 test UI gửi WebP do Canvas tạo vào field này. Contract vẫn hỗ trợ JPEG/PNG/WebP trực tiếp để client không có Canvas hoặc Main Backend vẫn có thể tích hợp; không thêm field `width`, `quality` hay resize options vào API.

Success `201 Created`:

```json
{
  "id": "img_123",
  "width": 12000,
  "height": 6000,
  "status": "ready",
  "presets": ["thumb", "small", "medium", "large", "xlarge"]
}
```

Response chỉ được phát sau processing thành công. Áp dụng lỗi validation ở spec 03 và `500 processing_failed` cho lỗi engine/storage bất ngờ.

## 2. Metadata

```http
GET /api/v1/images/{id}
```

Success `200 OK`:

```json
{
  "id": "img_123",
  "width": 12000,
  "height": 6000,
  "status": "ready",
  "available_presets": ["thumb", "small", "medium", "large", "xlarge"]
}
```

Asset không tồn tại: `404 asset_not_found`. Với `processing`/`failed`, không liệt kê variant chưa được đảm bảo tồn tại.

## 3. Lấy variant

```http
GET /api/v1/images/{id}/{preset}
```

- `preset` ngoài allowlist: `404 preset_not_found` (tránh lộ nội bộ và phân biệt với query resize không hỗ trợ).
- Asset không tồn tại: `404 asset_not_found`.
- Record chưa `ready` hoặc file bị thiếu: `404 variant_not_available`; log inconsistency nếu status là ready.
- Success: stream file, `200`, `Content-Type: image/webp`, `Content-Length` nếu biết, `X-Content-Type-Options: nosniff`.
- Không chạy pyvips trong endpoint này. Có thể thêm `Cache-Control: public, max-age=31536000, immutable` khi URL/ID immutable.

## 4. Lấy ảnh gốc

```http
GET /api/v1/images/{id}/original
```

- Trả đúng file gốc đã upload và xác thực, giữ nguyên định dạng JPEG/PNG/WebP (`Content-Type` tương ứng).
- Endpoint này không chuyển đổi, resize hoặc sinh ảnh mới.
- Asset không tồn tại: `404 asset_not_found`; original không còn: `404 original_not_available`.
- Response có `X-Content-Type-Options: nosniff`; có thể cache immutable vì ID không thay đổi.

## 5. Delete

```http
DELETE /api/v1/images/{id}
```

Luồng: khóa/lấy record → xóa asset directory storage → xóa DB record. Success `204 No Content`; asset không tồn tại `404 asset_not_found`. Nếu storage delete lỗi thì giữ DB record, trả `500 deletion_failed`, để retry an toàn.

## Routing và serializer

- Khai báo route tĩnh/chi tiết trước route metadata nếu router có nguy cơ match nhầm.
- Serializer response chỉ expose public fields phía trên; tuyệt đối không expose `original_path`, filesystem root hay original filename trừ khi contract được mở rộng.
- Viết integration tests cho status, JSON body, `Content-Type` và đảm bảo GET variant không gọi processor.

## Done

- Bốn endpoint hoạt động đúng status/body/error contract.
- Client có thể chỉ lưu `id` và tự xây URL variant từ contract.
- DELETE xóa cả file và record; GET sau delete trả 404.
