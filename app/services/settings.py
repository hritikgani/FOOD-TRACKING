from app.db import get_db

DEFAULTS = {
    "currency_symbol": "₹",
    "theme": "system",
}


def get_setting(key: str, default=None):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row:
        return row["value"]
    return DEFAULTS.get(key, default)


def get_all_settings() -> dict:
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    settings = dict(DEFAULTS)
    settings.update({row["key"]: row["value"] for row in rows})
    return settings


def set_setting(key: str, value: str):
    db = get_db()
    db.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    db.commit()


def clear_all_data():
    db = get_db()
    db.execute("DELETE FROM order_items")
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM restaurants")
    db.execute("DELETE FROM cuisines")
    db.execute("DELETE FROM import_sessions")
    for seq in ("orders_id_seq", "order_items_id_seq", "restaurants_id_seq", "cuisines_id_seq"):
        db.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
    db.commit()
