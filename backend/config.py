import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "ppt_generator.db").replace("\\", "/")


def _resolve_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        return f"sqlite:///{DEFAULT_DB_PATH}"

    # Normalize relative sqlite paths against backend directory so the app
    # doesn't switch databases based on process working directory.
    if raw.startswith("sqlite:///"):
        db_path = raw.replace("sqlite:///", "", 1)
        is_windows_abs = len(db_path) >= 2 and db_path[1] == ":"
        is_unix_abs = db_path.startswith("/")
        if not is_windows_abs and not is_unix_abs:
            abs_path = os.path.abspath(os.path.join(BASE_DIR, db_path)).replace("\\", "/")
            return f"sqlite:///{abs_path}"

    return raw


DATABASE_URL = _resolve_database_url()

# Default API keys (can be overridden per-user via settings)
DEFAULT_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
DEFAULT_PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
DEFAULT_UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
DEFAULT_UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY", "")

# Encryption key for storing user API keys
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
