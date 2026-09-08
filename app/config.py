import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-if-deployed")
    DATABASE_PATH = str(BASE_DIR / "data" / "food_orders.db")
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
