# Đặc tả triển khai Standalone Image API

Thư mục này là kế hoạch kỹ thuật để triển khai hoàn chỉnh baseline **pregenerate variants** được mô tả trong `../Pipeline_cu_API_rieng_Pregenerate.md`.

## Phạm vi bản đầu tiên

- Service Django + Django REST Framework độc lập với Main Backend, Media và Tour.
- Vue 3 tiền xử lý ảnh bằng HTML5 Canvas trước upload: hiển thị byte gốc, resize giữ tỷ lệ/không upscale, encode WebP và hiển thị byte sau Canvas. File Canvas là payload `file` được gửi vào API.
- Upload ảnh, xác thực nội dung, lưu original, sinh đồng bộ toàn bộ WebP variants và trả `ready` khi hoàn tất.
- SQLite và local disk dưới thư mục `media/` của Django dành cho POC/benchmark.
- Không CDN, queue, Celery, Redis, xử lý resize khi GET, hay client-defined dimensions.

## Thứ tự thực hiện bắt buộc

| Giai đoạn | Spec | Kết quả bàn giao | Phụ thuộc |
| --- | --- | --- | --- |
| 1 | [01-bootstrap.md](01-bootstrap.md) | Django project chạy được, cấu hình và health check | — |
| 2 | [02-domain-storage.md](02-domain-storage.md) | Model, ID, storage abstraction, migration | 1 |
| 3 | [03-validation.md](03-validation.md) | Xác thực upload an toàn và có test | 1 |
| 4 | [04-processing.md](04-processing.md) | pyvips tạo original + 5 variants, rollback lỗi | 2, 3 |
| 5 | [05-http-api.md](05-http-api.md) | POST/GET metadata/GET preset/DELETE đúng contract | 2, 3, 4 |
| 6 | [06-tests-benchmark.md](06-tests-benchmark.md) | Test suite, dữ liệu benchmark, báo cáo đo đạc | 5 |
| 7 | [07-production-readiness.md](07-production-readiness.md) | Checklist vận hành và các bước mở rộng có kiểm soát | 6 |

Chỉ chuyển sang giai đoạn sau khi các tiêu chí “Done” của giai đoạn hiện tại đều đạt. Các hằng số và HTTP contract trong specs là nguồn chuẩn cho implementation; tài liệu pipeline cũ là tài liệu nền.

## Quy ước chung

- Múi giờ: lưu datetime UTC, trả ISO-8601 có timezone.
- Error response dùng JSON thống nhất: `{ "code": "...", "detail": "..." }`; lỗi field có thêm `fields`.
- Mọi đường dẫn storage phải do service tạo từ `asset_id`; không được nhận path từ client.
- Không đưa logic pyvips vào view; view chỉ parse request, gọi service và serialize response.
- Tên preset là allowlist cố định: `thumb`, `small`, `medium`, `large`, `xlarge`.
- Canvas là tối ưu UX/băng thông phía client, không thay thế validation server-side. Client có thể bypass Canvas nên API phải tiếp tục áp dụng mọi limit trong spec 03.
