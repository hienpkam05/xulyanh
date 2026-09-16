# Vue 3 test UI

Start the Django API first from `../image_api`:

```powershell
..\venv\Scripts\python.exe manage.py runserver
```

Then start this UI:

```powershell
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The Vite proxy sends `/api` and `/healthz` requests to Django on port 8000, so no development CORS configuration is needed.

Before upload, the UI always uses HTML5 Canvas to resize and encode the selected image as WebP. It displays the original file size and the generated file size; only the generated WebP is sent to Django. The default maximum width is 4096 px and WebP quality is 86%; both can be changed in the UI. Canvas preserves aspect ratio and never upscales.

For a deployed UI at another origin, set the API base URL in the screen and configure CORS/authentication on the Django deployment first.
