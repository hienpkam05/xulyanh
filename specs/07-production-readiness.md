# Giai đoạn 7 — Vận hành và đường mở rộng

## Checklist trước khi đưa ra môi trường dùng chung

- Cấu hình `DEBUG=False`, `ALLOWED_HOSTS`, CORS, authentication/authorization và rate limit tại service/gateway.
- `MEDIA_ROOT` (đặc biệt `MEDIA_ROOT/images`) là persistent volume; backup database và media storage phải cùng chiến lược khôi phục.
- Log structured gồm request/asset ID, kích thước, preset, processing duration và lỗi; không log file bytes hay đường dẫn nhạy cảm.
- Giới hạn upload đồng thời theo CPU/RAM thực đo; timeout, reverse-proxy body limit và disk quota phù hợp `MAX_FILE_SIZE`.
- Monitoring: error rate POST, processing duration, disk usage, số `failed`, file-missing inconsistency, 5xx và health check.
- Kiểm tra quyền filesystem: process chỉ có quyền trên storage root; không serve arbitrary local paths.

## Các thay đổi tương lai không được phá contract

| Nhu cầu | Hướng triển khai |
| --- | --- |
| Object storage | thay local implementation của storage interface, giữ asset ID/URL/preset |
| Nhiều upload lớn | queue + worker + concurrency limit; lúc đó bổ sung status `processing`/polling nhưng vẫn giữ `ready` semantics |
| CDN | CDN cache endpoint GET variant; file đã immutable theo asset ID |
| Reprocess | endpoint/admin command nội bộ phiên bản hóa pipeline, không ghi đè im lặng output đang serve |
| Dọn orphan | management command quét record `failed` và asset directories không có DB record, dry-run mặc định |

Không thêm resize query động vào service baseline. Khi cần pipeline lazy/on-demand, tạo implementation khác phía sau cùng HTTP contract và benchmark với dataset của giai đoạn 6.
