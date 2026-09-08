from __future__ import annotations

from app.db import get_db
from app.services.cuisines import get_or_create_cuisine
from app.services.restaurants import get_or_create_restaurant
from app.utils.normalize import normalize_name


def parse_food_items(raw) -> list[dict]:
    """Turn a raw food-items value (comma separated string, or a list of
    dicts/strings) into a normalized list of item dicts."""
    if not raw:
        return []
    if isinstance(raw, str):
        names = [n.strip() for n in raw.split(",") if n.strip()]
        return [{"item_name": n, "quantity": 1, "unit_price": None, "total_price": None} for n in names]
    items = []
    for entry in raw:
        if isinstance(entry, str):
            name = entry.strip()
            if name:
                items.append({"item_name": name, "quantity": 1, "unit_price": None, "total_price": None})
        elif isinstance(entry, dict):
            name = str(entry.get("item_name") or "").strip()
            if name:
                items.append(
                    {
                        "item_name": name,
                        "quantity": entry.get("quantity") or 1,
                        "unit_price": entry.get("unit_price"),
                        "total_price": entry.get("total_price"),
                    }
                )
    return items


def _replace_items(db, order_id: int, items: list[dict]):
    db.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    for item in items:
        db.execute(
            """
            INSERT INTO order_items
                (order_id, item_name, normalized_item_name, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                item["item_name"],
                normalize_name(item["item_name"]),
                item.get("quantity") or 1,
                item.get("unit_price"),
                item.get("total_price"),
            ),
        )


def create_order(cleaned: dict) -> int:
    db = get_db()
    restaurant_id = get_or_create_restaurant(cleaned["restaurant"])
    cuisine_id = get_or_create_cuisine(cleaned["cuisine"]) if cleaned.get("cuisine") else None

    cur = db.execute(
        """
        INSERT INTO orders (
            order_date, order_time, platform, restaurant_id, cuisine_id,
            subtotal, discount, delivery_fee, platform_fee, tax, total_amount, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cleaned["order_date"],
            cleaned["order_time"],
            cleaned["platform"],
            restaurant_id,
            cuisine_id,
            cleaned.get("subtotal"),
            cleaned.get("discount"),
            cleaned.get("delivery_fee"),
            cleaned.get("platform_fee"),
            cleaned.get("tax"),
            cleaned["total_amount"],
            cleaned.get("notes"),
        ),
    )
    order_id = cur.lastrowid

    items = parse_food_items(cleaned.get("food_items"))
    if items:
        _replace_items(db, order_id, items)

    db.commit()
    return order_id


def update_order(order_id: int, cleaned: dict) -> None:
    db = get_db()
    restaurant_id = get_or_create_restaurant(cleaned["restaurant"])
    cuisine_id = get_or_create_cuisine(cleaned["cuisine"]) if cleaned.get("cuisine") else None

    db.execute(
        """
        UPDATE orders SET
            order_date = ?, order_time = ?, platform = ?, restaurant_id = ?, cuisine_id = ?,
            subtotal = ?, discount = ?, delivery_fee = ?, platform_fee = ?, tax = ?,
            total_amount = ?, notes = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            cleaned["order_date"],
            cleaned["order_time"],
            cleaned["platform"],
            restaurant_id,
            cuisine_id,
            cleaned.get("subtotal"),
            cleaned.get("discount"),
            cleaned.get("delivery_fee"),
            cleaned.get("platform_fee"),
            cleaned.get("tax"),
            cleaned["total_amount"],
            cleaned.get("notes"),
            order_id,
        ),
    )

    if cleaned.get("food_items") is not None:
        items = parse_food_items(cleaned.get("food_items"))
        _replace_items(db, order_id, items)

    db.commit()


def delete_order(order_id: int) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    db.commit()
    return cur.rowcount > 0


def get_order(order_id: int):
    db = get_db()
    order = db.execute(
        """
        SELECT o.*, r.name AS restaurant_name, c.name AS cuisine_name
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        WHERE o.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        return None
    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()
    result = dict(order)
    # "items" collides with dict.items() when accessed as order.items in
    # Jinja, so the line items live under a differently-named key.
    result["line_items"] = [dict(i) for i in items]
    return result


def list_orders(
    platform=None,
    restaurant_id=None,
    cuisine_id=None,
    date_from=None,
    date_to=None,
    min_amount=None,
    max_amount=None,
    search=None,
    sort_by="order_date",
    sort_dir="desc",
    page=1,
    page_size=25,
):
    db = get_db()

    conditions = []
    params: list = []

    if platform:
        conditions.append("o.platform = ?")
        params.append(platform)
    if restaurant_id:
        conditions.append("o.restaurant_id = ?")
        params.append(restaurant_id)
    if cuisine_id:
        conditions.append("o.cuisine_id = ?")
        params.append(cuisine_id)
    if date_from:
        conditions.append("o.order_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("o.order_date <= ?")
        params.append(date_to)
    if min_amount is not None:
        conditions.append("o.total_amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        conditions.append("o.total_amount <= ?")
        params.append(max_amount)
    if search:
        like = f"%{search.strip()}%"
        conditions.append(
            """
            (r.name LIKE ? OR c.name LIKE ? OR EXISTS (
                SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.item_name LIKE ?
            ))
            """
        )
        params.extend([like, like, like])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sort_columns = {
        "date": "o.order_date",
        "order_date": "o.order_date",
        "amount": "o.total_amount",
        "restaurant": "r.name",
        "platform": "o.platform",
    }
    sort_column = sort_columns.get(sort_by, "o.order_date")
    direction = "ASC" if sort_dir == "asc" else "DESC"

    count_row = db.execute(
        f"""
        SELECT COUNT(*) AS c
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        {where_clause}
        """,
        params,
    ).fetchone()
    total = count_row["c"]

    offset = max(page - 1, 0) * page_size
    rows = db.execute(
        f"""
        SELECT o.*, r.name AS restaurant_name, c.name AS cuisine_name
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        {where_clause}
        ORDER BY {sort_column} {direction}, o.order_time {direction}
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()

    return {
        "orders": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def check_possible_duplicate(order_date, restaurant_name, total_amount, platform) -> bool:
    db = get_db()
    normalized = normalize_name(restaurant_name)
    row = db.execute(
        """
        SELECT 1 FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        WHERE o.order_date = ? AND r.normalized_name = ?
          AND o.total_amount = ? AND o.platform = ?
        LIMIT 1
        """,
        (order_date, normalized, total_amount, platform),
    ).fetchone()
    return row is not None
