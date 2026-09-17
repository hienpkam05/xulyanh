"""Settings for the standalone Image API POC."""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file without overriding real env vars."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_local_env(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key-change-before-production")
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "images.apps.ImagesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

def database_config() -> dict:
    """Build Django's database setting from one DATABASE_URL environment variable."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql"}:
        database_name = parsed.path.lstrip("/")
        if not database_name:
            raise ValueError("DATABASE_URL must include a PostgreSQL database name.")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(database_name),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "localhost",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }

    if scheme == "sqlite":
        database_name = unquote(parsed.path.lstrip("/"))
        if database_name == ":memory:":
            return {"ENGINE": "django.db.backends.sqlite3", "NAME": database_name}
        if not database_name:
            raise ValueError("DATABASE_URL must include a SQLite database path.")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / database_name)}

    raise ValueError("DATABASE_URL must start with postgresql:// or sqlite:///")


DATABASES = {"default": database_config()}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))).resolve()
IMAGE_STORAGE_ROOT = Path(
    os.getenv("IMAGE_STORAGE_ROOT", str(MEDIA_ROOT / "images"))
).resolve()

# File uploads larger than this are streamed to a temporary file rather than RAM.
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024)))
MAX_WIDTH = int(os.getenv("MAX_WIDTH", "16000"))
MAX_HEIGHT = int(os.getenv("MAX_HEIGHT", "16000"))
MAX_PIXELS = int(os.getenv("MAX_PIXELS", "120000000"))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(MAX_FILE_SIZE + 5 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(2_621_440)))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
