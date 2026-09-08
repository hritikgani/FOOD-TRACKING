import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-if-deployed")

    # Production/Vercel: set DATABASE_URL to a real Postgres instance (e.g. a
    # Neon connection string from the Vercel Postgres/Neon integration).
    # Local dev: leave it unset -- app/db.py spins up (and reuses) a local
    # embedded Postgres via `pgserver` under data/pgdata/, so there's no
    # separate local database to install or configure, and no SQL dialect
    # drift between what you test locally and what runs in production.
    DATABASE_URL = os.environ.get("DATABASE_URL")
    LOCAL_PGDATA_DIR = str(BASE_DIR / "data" / "pgdata")

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload cap
    UPLOAD_EXTENSIONS = {".csv", ".xlsx", ".xls"}
    DEFAULT_CURRENCY_SYMBOL = "₹"
    DEFAULT_CUISINES = [
        "Indian",
        "North Indian",
        "South Indian",
        "Chinese",
        "Italian",
        "Fast Food",
        "Biryani",
        "Burgers",
        "Pizza",
        "Desserts",
        "Beverages",
        "Other",
    ]
