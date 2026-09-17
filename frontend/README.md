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

Before upload, the UI uses HTML5 Canvas to show a resized WebP preview and its estimated size. The API receives and stores the original selected JPEG, PNG, or WebP file; Canvas output is not uploaded. The default preview maximum width is 4096 px and WebP quality is 86%; both can be changed in the UI. Canvas preserves aspect ratio and never upscales.

For a deployed UI at another origin, set the API base URL in the screen and configure CORS/authentication on the Django deployment first.
