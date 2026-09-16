# Giai đoạn 1 — Khởi tạo service và cấu hình

## Mục tiêu

Tạo một Django service có thể chạy độc lập, không import model, settings hay URL từ Main Backend.

## Cấu trúc cần tạo

```text
image_api/
├── manage.py
├── requirements.txt
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── images/
    ├── models.py
    ├── serializers.py
    ├── urls.py
    ├── views.py
    ├── services/
    └── tests/
```

## Dependencies và cấu hình

- Python version được pin trong `requirements.txt`/runtime documentation; cài `Django`, `djangorestframework`, `pyvips[binary]`.
- `INSTALLED_APPS` gồm `rest_framework` và `images`.
- POC dùng SQLite. Cấu hình `MEDIA_ROOT=<project-root>/media` và `MEDIA_URL=/media/`; không hard-code đường dẫn trong service.
- `IMAGE_STORAGE_ROOT` phải suy ra từ `MEDIA_ROOT / "images"`. Giá trị development mặc định là `<project-root>/media/images`; thư mục được tạo lúc khởi động hoặc lúc storage dùng lần đầu.
- Trong development, URL config phải serve `MEDIA_URL` từ `MEDIA_ROOT`. Đây chỉ là tiện ích phát triển; production để reverse proxy/object storage serve file, còn endpoint API vẫn là contract chính.
- Giới hạn request upload phải lớn hơn hoặc bằng `MAX_FILE_SIZE` và được cấu hình ở Django (`DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE`). Upload lớn cần streamed temporary file, không đọc toàn bộ file vào RAM.
- Bổ sung `GET /healthz`: trả 200 `{ "status": "ok" }`; không cần truy cập storage hay database ở POC.
- Root URL include `path("api/v1/", include("images.urls"))`.

## Done

- `python manage.py check` và `python manage.py migrate` thành công.
- `GET /healthz` trả 200.
- Service khởi động khi chưa có file trong `media/images`.
- Không có import nào từ ứng dụng Media/Tour hiện có.
