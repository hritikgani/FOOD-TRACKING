from app.db import get_db
from app.utils.normalize import normalize_name


def get_or_create_restaurant(name: str) -> int:
    """Return the id of the restaurant matching `name` (by normalized form),
    creating it if it doesn't exist yet."""
    name = (name or "").strip()
    normalized = normalize_name(name)
    if not normalized:
        raise ValueError("Restaurant name is required")

    db = get_db()
    row = db.execute(
        "SELECT id FROM restaurants WHERE normalized_name = ?", (normalized,)
    ).fetchone()
    if row:
        return row["id"]

    cur = db.execute(
        "INSERT INTO restaurants (name, normalized_name) VALUES (?, ?) RETURNING id",
        (name, normalized),
    )
    new_id = cur.fetchone()["id"]
    db.commit()
    return new_id


def list_restaurants():
    db = get_db()
    return db.execute("SELECT * FROM restaurants ORDER BY name").fetchall()


def get_restaurant(restaurant_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)
    ).fetchone()


def restaurant_summaries(sort_by: str = "orders", order: str = "desc"):
    """Per-restaurant aggregate stats used by the Restaurants page."""
    db = get_db()
    sort_columns = {
        "orders": "order_count",
        "spending": "total_spent",
        "avg_order": "avg_order_value",
        "recent": "last_order_date",
        "name": "r.name",
    }
    column = sort_columns.get(sort_by, "order_count")
    direction = "ASC" if order == "asc" else "DESC"

    total_orders_row = db.execute("SELECT COUNT(*) AS c FROM orders").fetchone()
    total_orders = total_orders_row["c"] or 1

    rows = db.execute(
        f"""
        SELECT
            r.id,
            r.name,
            COUNT(o.id) AS order_count,
            COALESCE(SUM(o.total_amount), 0) AS total_spent,
            COALESCE(AVG(o.total_amount), 0) AS avg_order_value,
            MIN(o.order_date) AS first_order_date,
            MAX(o.order_date) AS last_order_date
        FROM restaurants r
        JOIN orders o ON o.restaurant_id = r.id
        GROUP BY r.id, r.name
        ORDER BY {column} {direction}
        """
    ).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        d["percentage_of_orders"] = round((d["order_count"] / total_orders) * 100, 1)
        results.append(d)
    return results


def restaurant_detail(restaurant_id: int):
    db = get_db()
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        return None

    stats = db.execute(
        """
        SELECT
            COUNT(*) AS order_count,
            COALESCE(SUM(total_amount), 0) AS total_spent,
            COALESCE(AVG(total_amount), 0) AS avg_order_value,
            MIN(order_date) AS first_order_date,
            MAX(order_date) AS last_order_date
        FROM orders WHERE restaurant_id = ?
        """,
        (restaurant_id,),
    ).fetchone()

    orders = db.execute(
        """
        SELECT o.*, c.name AS cuisine_name
        FROM orders o
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        WHERE o.restaurant_id = ?
        ORDER BY o.order_date DESC, o.order_time DESC
        """,
        (restaurant_id,),
    ).fetchall()

    return {
        "restaurant": dict(restaurant),
        "stats": dict(stats),
        "orders": [dict(o) for o in orders],
    }
