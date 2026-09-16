# Backlog giao việc — Standalone Image API

Tài liệu này chia công việc triển khai theo thứ tự phụ thuộc. Chi tiết kỹ thuật là các spec được liên kết ở từng task. Đánh dấu `[x]` chỉ sau khi code, test và tiêu chí nghiệm thu đều đạt.

## Quy tắc giao việc

- Một task chỉ được bắt đầu khi mọi task trong cột **Phụ thuộc** đã hoàn thành.
- Không gộp logic xử lý ảnh vào `views.py`; view chỉ nhận request, gọi service và trả response.
- Storage của POC là `MEDIA_ROOT/images` (mặc định `media/images`), không phải Media/Tour của hệ thống khác.
- Vue 3 xử lý Canvas trước `POST`: phải hiển thị dung lượng gốc → dung lượng WebP sau Canvas, giữ tỷ lệ, không upscale và upload file WebP đã tạo. Đây không được dùng để bỏ validation server-side.
- Mỗi PR/task phải kèm test phù hợp; không sửa HTTP contract nếu chưa cập nhật spec và có quyết định rõ ràng.

## Sprint 1 — Nền tảng

| ID | Task | Phụ thuộc | Đầu ra / nghiệm thu | Spec |
| --- | --- | --- | --- | --- |
| [x] IMG-01 | Khởi tạo Django project độc lập | — | Có `config/`, app `images/`, DRF, `requirements.txt`; `manage.py check` chạy thành công | [01-bootstrap](01-bootstrap.md) |
| [x] IMG-02 | Thiết lập settings POC | IMG-01 | SQLite; `MEDIA_ROOT=<project>/media`, `MEDIA_URL=/media/`, `IMAGE_STORAGE_ROOT=MEDIA_ROOT/images`; upload limits từ settings | [01-bootstrap](01-bootstrap.md) |
| [x] IMG-03 | Thêm health check và routing gốc | IMG-01 | `GET /healthz` trả `200 {"status":"ok"}`; `/api/v1/` include app URLs | [01-bootstrap](01-bootstrap.md) |
| [x] IMG-04 | Tạo model và migration `ImageAsset` | IMG-01 | Có public ID `img_<uuid>`, metadata original, status, timestamps; migration chạy được | [02-domain-storage](02-domain-storage.md) |
| [x] IMG-05 | Tạo preset module | IMG-01 | Allowlist cố định gồm 5 preset với đúng width/quality; helper validate preset có test | [02-domain-storage](02-domain-storage.md) |

## Sprint 2 — Storage và validation

| ID | Task | Phụ thuộc | Đầu ra / nghiệm thu | Spec |
| --- | --- | --- | --- | --- |
| [x] IMG-06 | Implement local media storage | IMG-02, IMG-04, IMG-05 | Lưu đúng layout `media/images/<asset_id>/`; có save/open/path/delete interface | [02-domain-storage](02-domain-storage.md) |
| [x] IMG-07 | Hardening storage path | IMG-06 | Không thể path traversal; delete chỉ tác động 1 asset tree bên trong `MEDIA_ROOT/images` | [02-domain-storage](02-domain-storage.md) |
| [x] IMG-08 | Implement validation service | IMG-02 | Kiểm tra file field, empty, byte limit, MIME tin cậy, decode và dimensions bằng pyvips | [03-validation](03-validation.md) |
| [x] IMG-09 | Test validation | IMG-08 | Test JPG/PNG/WebP hợp lệ, extension giả, corrupt, MIME sai và toàn bộ lỗi 400/413/415/422 | [03-validation](03-validation.md) |

## Sprint 3 — Xử lý ảnh và upload

| ID | Task | Phụ thuộc | Đầu ra / nghiệm thu | Spec |
| --- | --- | --- | --- | --- |
| [x] IMG-10 | Implement processor orchestration | IMG-04, IMG-06, IMG-08 | Validate → save original → 5 variants → status ready; code nằm trong `services/processor.py` | [04-processing](04-processing.md) |
| [x] IMG-11 | Implement pyvips WebP variants | IMG-05, IMG-10 | Sinh đủ `thumb`…`xlarge` WebP; preserve ratio và tuyệt đối không upscale | [04-processing](04-processing.md) |
| [x] IMG-12 | Xử lý failure/cleanup | IMG-10 | Lỗi giữa pipeline rollback DB và xóa file partial; response không phát asset usable | [04-processing](04-processing.md) |
| [x] IMG-13 | Implement upload endpoint | IMG-09, IMG-11, IMG-12 | `POST /api/v1/images` trả `201` với `id`, dimensions, `ready`, 5 presets; contract lỗi đúng spec | [05-http-api](05-http-api.md) |
| [x] IMG-14 | Test upload end-to-end | IMG-13 | Upload hợp lệ có 1 original + 5 WebP; ảnh 500px không bị upscale; inject lỗi ghi file cleanup đúng | [04-processing](04-processing.md) |

## Sprint 4 — Đọc, xóa và regression test

| ID | Task | Phụ thuộc | Đầu ra / nghiệm thu | Spec |
| --- | --- | --- | --- | --- |
| [x] IMG-15 | Implement metadata endpoint | IMG-13 | `GET /api/v1/images/{id}` trả đúng public metadata và 404 asset không tồn tại | [05-http-api](05-http-api.md) |
| [x] IMG-16 | Implement variant endpoint | IMG-11, IMG-13 | `GET /api/v1/images/{id}/{preset}` stream `image/webp`; invalid ID/preset/file thiếu trả đúng 404 | [05-http-api](05-http-api.md) |
| [x] IMG-17 | Implement delete endpoint | IMG-06, IMG-13 | `DELETE` xóa storage + record, trả 204; storage delete lỗi giữ record và trả 500 | [05-http-api](05-http-api.md) |
| [x] IMG-18 | API integration/regression suite | IMG-15, IMG-16, IMG-17 | Test status/body/header các endpoint; GET variant không gọi pyvips hay processor | [05-http-api](05-http-api.md), [06-tests-benchmark](06-tests-benchmark.md) |

## Sprint 5 — Benchmark và sẵn sàng vận hành

| ID | Task | Phụ thuộc | Đầu ra / nghiệm thu | Spec |
| --- | --- | --- | --- | --- |
| [x] IMG-19 | Chuẩn bị dataset benchmark | IMG-18 | Manifest/checksum cho ảnh 2K, 4K, 8K, 12K; fixture tái lập được | [06-tests-benchmark](06-tests-benchmark.md) |
| [x] IMG-20 | Viết/runs benchmark | IMG-19 | Ít nhất 3 lần/case sau warm-up; ghi latency, peak RAM, CPU, storage, file count, GET lần 1/2 | [06-tests-benchmark](06-tests-benchmark.md) |
| [x] IMG-21 | Báo cáo benchmark | IMG-20 | Có environment, commands, raw samples, median và max; xác nhận 6 files/asset, GET không resize | [06-tests-benchmark](06-tests-benchmark.md) |
| [x] IMG-22 | Review production readiness | IMG-21 | Hoàn tất checklist persistent media, access control, rate limit, monitoring và backup | [07-production-readiness](07-production-readiness.md) |

## Definition of Done toàn dự án

- [ ] IMG-01 đến IMG-22 hoàn thành.
- [ ] Full test suite pass trên môi trường sạch.
- [ ] Upload đồng bộ chỉ trả `ready` khi original và cả 5 variants đã có.
- [ ] Mọi variant lưu dưới `media/images/<asset_id>/variants/` và là WebP.
- [ ] GET không chạy pyvips; DELETE không để lại original/variant/record.
- [ ] Báo cáo benchmark 2K/4K/8K/12K được lưu cùng source code.
