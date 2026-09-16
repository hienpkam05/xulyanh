# Giai đoạn 4 — Lưu original và pregenerate variants

## Mục tiêu

Thực hiện pipeline đồng bộ, atomic ở mức quan sát được: upload chỉ thành công khi original và cả năm preset đã tồn tại.

## Orchestrator

Tạo `images/services/processor.py` với một use case, ví dụ `create_image_asset(uploaded_file)`. View không tự save file hay gọi pyvips.

Trình tự bắt buộc:

1. Gọi validation và nhận metadata tin cậy.
2. Tạo `asset_id`; tạo `ImageAsset(status="processing")` trong DB transaction.
3. Copy stream upload sang `original.<safe-extension>` qua storage.
4. Mở original bằng `pyvips.Image.new_from_file(..., access="sequential")`.
5. Với từng preset theo thứ tự `thumb`, `small`, `medium`, `large`, `xlarge`, ghi `variants/<preset>.webp`.
6. Đặt `status="ready"`, lưu record và commit.
7. Chỉ lúc này mới trả dữ liệu success.

Khi Vue 3 Canvas đã gửi `image/webp`, original lưu tại đây là `original.webp`; processor không resize lại theo cấu hình Canvas. Processor chỉ tạo năm preset backend cố định từ original đã nhận.

## Quy tắc resize/output

```python
target_width = min(original.width, preset["width"])
if target_width < original.width:
    image = image.resize(target_width / original.width)
image.write_to_file(output_path, Q=preset["quality"])
```

- Luôn trả file `.webp`; cần đặt option libvips để encode WebP với `Q` của preset.
- Preserve aspect ratio; chiều cao suy ra từ scale.
- Không upscale. Với original rộng 500, variants `large` và `xlarge` có width 500 (vẫn phải tạo file riêng để đủ contract).
- Không overwrite asset đã ready; ID mới cho mỗi upload.

## Cleanup và tính nhất quán

Nếu save original, decode hoặc bất kỳ preset nào thất bại:

- log lỗi kỹ thuật ở server kèm asset ID;
- rollback transaction database;
- gọi `delete_asset_tree(asset_id)` để xóa file partial;
- trả 500 `processing_failed` với message tổng quát;
- nếu cleanup thất bại, log mức error và tạo/giữ record `failed` để có thể chạy cleanup thủ công. Không trả ID như một asset usable.

Đóng/giải phóng file handle ở mọi nhánh. Không dùng background task ở giai đoạn này.

## Done

- Một upload hợp lệ tạo 1 original + chính xác 5 WebP files.
- Metadata `ready` chỉ xuất hiện sau khi tất cả output được ghi.
- Test ảnh 500 px xác nhận variants lớn không upscale.
- Test inject lỗi khi ghi variant thứ ba xác nhận không còn file partial/ready asset.
