# Giai đoạn 3 — Xác thực file ảnh

## Mục tiêu

Chặn input sai hoặc có rủi ro trước khi lưu original/sinh variants; không chỉ dựa vào filename hay `Content-Type` do client gửi.

Vue 3 thường gửi WebP đã được resize/nén bằng HTML5 Canvas. Đây vẫn là input không tin cậy: client khác có thể gửi JPEG/PNG/WebP gốc hoặc bypass Canvas hoàn toàn, nên toàn bộ validation dưới đây luôn bắt buộc.

## Cấu hình mặc định

```python
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_WIDTH = 16_000
MAX_HEIGHT = 16_000
MAX_PIXELS = 120_000_000
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
```

Các giá trị lấy từ settings để benchmark có thể thay đổi. Không hỗ trợ GIF/SVG/TIFF/HEIC trong POC trừ khi bổ sung đồng thời test và policy riêng.

## Trình tự validation

1. Field multipart bắt buộc là `file`; chỉ nhận đúng một file.
2. Kiểm tra non-empty và `uploaded_file.size <= MAX_FILE_SIZE` trước khi đọc/decode.
3. Xác định MIME từ bytes/header bằng decoder hoặc thư viện content detection đáng tin cậy; không dùng extension và không chỉ tin request header.
4. MIME phải nằm trong allowlist.
5. Decode metadata bằng pyvips; decoder exception là `invalid_image`.
6. Kiểm tra width, height > 0, từng chiều không quá giới hạn và `width * height <= MAX_PIXELS`.
7. Trả metadata đã xác thực gồm MIME, width, height, byte size và safe extension để storage dùng.

Validation không được load pixel raster đầy đủ nếu pyvips có thể đọc metadata theo cơ chế lazy/sequential. Sau khi inspect, reset/reopen upload stream trước khi copy sang original.

## Lỗi contract

| Tình huống | HTTP | `code` |
| --- | --- | --- |
| thiếu field/file rỗng | 400 | `invalid_file` |
| vượt byte limit | 413 | `file_too_large` |
| MIME không hỗ trợ | 415 | `unsupported_media_type` |
| không decode được | 422 | `invalid_image` |
| width/height/pixel vượt limit | 422 | `image_dimensions_exceeded` |

Không để exception pyvips, filesystem path, stack trace hoặc thông tin nội bộ xuất hiện trong response.

## Done

- Unit tests cho JPG/PNG/WebP hợp lệ và extension giả mạo.
- Test mỗi nhánh lỗi trong bảng, bao gồm ảnh corrupt và vượt pixel limit.
- Test chứng minh invalid upload không để lại directory/row database.
