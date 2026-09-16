# Giai đoạn 6 — Test, benchmark và tiêu chí bàn giao

## Test suite tối thiểu

| Nhóm | Ca kiểm thử bắt buộc |
| --- | --- |
| Validation | thiếu file, empty, vượt byte, MIME sai, corrupt, vượt width/height/pixel, JPEG/PNG/WebP hợp lệ |
| Processing | đủ 5 WebP, đúng width/quality policy, preserve ratio, không upscale, cleanup khi lỗi |
| API | upload 201, metadata 200, từng preset 200 WebP, ID/preset sai 404, delete 204, GET sau delete 404 |
| Isolation | upload hai asset không ghi/xóa chéo; path traversal bị từ chối |
| Regression | GET variant chỉ đọc file có sẵn, không gọi pyvips/resize |

Test phải override `MEDIA_ROOT` tới temporary directory (và theo đó `IMAGE_STORAGE_ROOT=MEDIA_ROOT/images`) cùng database test; không ghi vào `media/` của môi trường dev/benchmark thật. Fixture ảnh phải được version control hoặc có script tạo lại deterministically.

## Benchmark Canvas frontend bổ sung

Đo riêng bước Vue 3 Canvas với cùng bộ ảnh 2K/4K/8K/12K: thời gian `createImageBitmap + drawImage + toBlob`, byte trước/sau và dimensions output. Test tối thiểu phải xác nhận Canvas giữ tỷ lệ, không upscale và chỉ upload `File` WebP đã tạo. Không trộn số Canvas client vào benchmark server hiện tại; báo cáo hai pha riêng để biết bottleneck nằm ở browser hay Image API.

## Dataset benchmark

Chuẩn bị cùng một nội dung ảnh cho bốn nhóm input: 2K, 4K, 8K, 12K. Ghi rõ width × height, format, byte size và checksum của từng file trong manifest. Chạy mỗi case ít nhất 3 lần sau một warm-up; báo cáo median và max thay vì chỉ một lần chạy.

## Metrics cần thu

| Metric | Cách tính |
| --- | --- |
| Upload latency | từ lúc request POST bắt đầu đến response `201` |
| Processing time | validate + save + generate, log theo asset ID |
| Peak RAM | process RSS cực đại trong lúc POST |
| CPU | CPU utilization/process CPU time và cách đo |
| Storage | bytes original + toàn bộ variants |
| File count | expected 6 file/asset (1 original + 5 variants) |
| First/second GET | latency GET cùng preset, xác nhận không resize |

Lưu command, môi trường (CPU, RAM, OS, Python, libvips version), concurrency và raw samples trong `benchmarks/` hoặc thư mục đã quyết định. Không so sánh kết quả giữa máy/môi trường khác nhau mà không ghi chú.

## Exit criteria

- Toàn bộ automated test pass.
- Bốn kích thước input đều upload và có đủ outputs.
- Báo cáo benchmark tái lập được, có số peak RAM, latency, storage và file count.
- Không có request GET nào thực hiện xử lý pyvips.
