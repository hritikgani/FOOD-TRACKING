from __future__ import annotations

from app.db import get_db


def get_or_create_cuisine(name: str) -> int | None:
    name = (name or "").strip()
    if not name:
        return None

    db = get_db()
    row = db.execute(
        "SELECT id FROM cuisines WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if row:
        return row["id"]

    cur = db.execute("INSERT INTO cuisines (name) VALUES (?) RETURNING id", (name,))
    new_id = cur.fetchone()["id"]
    db.commit()
    return new_id


def list_cuisines():
    db = get_db()
    return db.execute("SELECT * FROM cuisines ORDER BY name").fetchall()


def seed_default_cuisines(names: list[str]):
    db = get_db()
    for name in names:
        db.execute(
            "INSERT INTO cuisines (name) VALUES (?) ON CONFLICT (name) DO NOTHING", (name,)
        )
    db.commit()
