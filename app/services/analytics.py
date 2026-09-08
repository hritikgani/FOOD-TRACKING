from __future__ import annotations

from datetime import date, timedelta

from app.db import get_db
from app.utils.dates import WEEKDAY_NAMES, is_weekend, time_bucket, weekday_name

PERIOD_DAYS = {
    "7d": 7,
    "30d": 30,
    "3m": 90,
    "6m": 182,
    "12m": 365,
}


def period_to_date_from(period: str) -> str | None:
    """Translate a period key ('7d'/'30d'/'3m'/'6m'/'12m'/'all') into an
    ISO start date, or None for 'all time'."""
    if not period or period == "all":
        return None
    days = PERIOD_DAYS.get(period)
    if not days:
        return None
    return (date.today() - timedelta(days=days)).isoformat()


def kpi_summary(date_from=None, date_to=None) -> dict:
    db = get_db()
    where, params = _date_where(date_from, date_to)

    totals = db.execute(
        f"""
        SELECT COUNT(*) AS total_orders,
               COALESCE(SUM(total_amount), 0) AS total_spent,
               COALESCE(AVG(total_amount), 0) AS avg_order_value,
               COUNT(DISTINCT restaurant_id) AS unique_restaurants
        FROM orders {where}
        """,
        params,
    ).fetchone()

    today = date.today()
    month_start = today.replace(day=1).isoformat()
    this_month = db.execute(
        """
        SELECT COUNT(*) AS orders_this_month,
               COALESCE(SUM(total_amount), 0) AS spending_this_month
        FROM orders WHERE order_date >= ?
        """,
        (month_start,),
    ).fetchone()

    total_orders = totals["total_orders"] or 0
    repeat_row = db.execute(
        f"""
        SELECT COUNT(*) AS repeat_orders FROM (
            SELECT o.id,
                   ROW_NUMBER() OVER (PARTITION BY o.restaurant_id ORDER BY o.order_date, o.id) AS rn
            FROM orders o {where}
        ) t WHERE t.rn > 1
        """,
        params,
    ).fetchone()
    repeat_orders = repeat_row["repeat_orders"] or 0
    repeat_order_pct = round((repeat_orders / total_orders) * 100, 1) if total_orders else 0

    most_restaurant = db.execute(
        f"""
        SELECT r.name AS name, COUNT(*) AS c FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        {where}
        GROUP BY o.restaurant_id ORDER BY c DESC LIMIT 1
        """,
        params,
    ).fetchone()

    most_cuisine = db.execute(
        f"""
        SELECT c.name AS name, COUNT(*) AS cnt FROM orders o
        JOIN cuisines c ON c.id = o.cuisine_id
        {where}
        GROUP BY o.cuisine_id ORDER BY cnt DESC LIMIT 1
        """,
        params,
    ).fetchone()

    return {
        "total_orders": total_orders,
        "total_spent": totals["total_spent"],
        "avg_order_value": totals["avg_order_value"],
        "unique_restaurants": totals["unique_restaurants"],
        "orders_this_month": this_month["orders_this_month"],
        "spending_this_month": this_month["spending_this_month"],
        "repeat_order_percentage": repeat_order_pct,
        "most_ordered_restaurant": most_restaurant["name"] if most_restaurant else None,
        "most_ordered_cuisine": most_cuisine["name"] if most_cuisine else None,
    }


def _date_where(date_from=None, date_to=None):
    conditions = []
    params: list = []
    if date_from:
        conditions.append("order_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("order_date <= ?")
        params.append(date_to)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


def platform_stats(date_from=None, date_to=None) -> list[dict]:
    db = get_db()
    where, params = _date_where(date_from, date_to)
    rows = db.execute(
        f"""
        SELECT platform,
               COUNT(*) AS order_count,
               COALESCE(SUM(total_amount), 0) AS total_spent
        FROM orders {where}
        GROUP BY platform
        """,
        params,
    ).fetchall()

    total_orders = sum(r["order_count"] for r in rows) or 1
    total_spent = sum(r["total_spent"] for r in rows) or 1

    results = {row["platform"]: dict(row) for row in rows}
    for platform in ("zomato", "swiggy"):
        entry = results.setdefault(
            platform, {"platform": platform, "order_count": 0, "total_spent": 0}
        )
        entry["order_percentage"] = round((entry["order_count"] / total_orders) * 100, 1)
        entry["spending_percentage"] = round((entry["total_spent"] / total_spent) * 100, 1)

    return [results["zomato"], results["swiggy"]]


def monthly_spending(months_back=12) -> list[dict]:
    db = get_db()
    start = (date.today().replace(day=1) - timedelta(days=months_back * 31)).replace(day=1).isoformat()
    rows = db.execute(
        """
        SELECT strftime('%Y-%m', order_date) AS month,
               COUNT(*) AS order_count,
               COALESCE(SUM(total_amount), 0) AS total_spent
        FROM orders
        WHERE order_date >= ?
        GROUP BY month
        ORDER BY month
        """,
        (start,),
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["label"] = date.fromisoformat(f"{d['month']}-01").strftime("%b %Y")
        results.append(d)
    return results


def top_restaurants(limit=5, sort_by="orders") -> list[dict]:
    db = get_db()
    sort_columns = {
        "orders": "order_count",
        "spending": "total_spent",
        "avg_order": "avg_order_value",
        "recent": "last_order_date",
    }
    column = sort_columns.get(sort_by, "order_count")
    total_orders_row = db.execute("SELECT COUNT(*) AS c FROM orders").fetchone()
    total_orders = total_orders_row["c"] or 1
    rows = db.execute(
        f"""
        SELECT r.id, r.name,
               COUNT(o.id) AS order_count,
               COALESCE(SUM(o.total_amount), 0) AS total_spent,
               COALESCE(AVG(o.total_amount), 0) AS avg_order_value,
               MAX(o.order_date) AS last_order_date
        FROM restaurants r
        JOIN orders o ON o.restaurant_id = r.id
        GROUP BY r.id
        ORDER BY {column} DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["percentage_of_orders"] = round((d["order_count"] / total_orders) * 100, 1)
        results.append(d)
    return results


def cuisine_distribution() -> list[dict]:
    db = get_db()
    total_row = db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total_amount),0) AS s FROM orders WHERE cuisine_id IS NOT NULL"
    ).fetchone()
    total_orders = total_row["c"] or 1
    total_spent = total_row["s"] or 1

    rows = db.execute(
        """
        SELECT c.id, c.name,
               COUNT(o.id) AS order_count,
               COALESCE(SUM(o.total_amount), 0) AS total_spent
        FROM cuisines c
        JOIN orders o ON o.cuisine_id = c.id
        GROUP BY c.id
        ORDER BY order_count DESC
        """
    ).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        d["order_percentage"] = round((d["order_count"] / total_orders) * 100, 1)
        d["spending_percentage"] = round((d["total_spent"] / total_spent) * 100, 1)
        results.append(d)
    return results


def top_food_items(limit=10) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT
            oi.normalized_item_name,
            MIN(oi.item_name) AS item_name,
            COUNT(*) AS times_ordered,
            COALESCE(SUM(oi.total_price), 0) AS total_spent,
            MAX(o.order_date) AS last_ordered_date,
            COUNT(DISTINCT o.restaurant_id) AS restaurant_count
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        GROUP BY oi.normalized_item_name
        ORDER BY times_ordered DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def ordering_time_distribution() -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT order_date, order_time, total_amount FROM orders WHERE order_time IS NOT NULL"
    ).fetchall()

    buckets = {"Morning": [0, 0], "Afternoon": [0, 0], "Evening": [0, 0], "Night": [0, 0], "Late Night": [0, 0]}
    for row in rows:
        bucket = time_bucket(row["order_time"])
        if bucket:
            buckets[bucket][0] += 1
            buckets[bucket][1] += row["total_amount"] or 0

    total_orders = sum(v[0] for v in buckets.values()) or 1
    result = []
    for name, (count, spent) in buckets.items():
        result.append(
            {
                "period": name,
                "order_count": count,
                "total_spent": round(spent, 2),
                "percentage": round((count / total_orders) * 100, 1),
            }
        )
    return result


def day_of_week_distribution() -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT order_date, COUNT(*) AS order_count, COALESCE(SUM(total_amount),0) AS total_spent
        FROM orders GROUP BY order_date
        """
    ).fetchall()

    buckets = {name: [0, 0] for name in WEEKDAY_NAMES}
    for row in rows:
        day = weekday_name(row["order_date"])
        buckets[day][0] += row["order_count"]
        buckets[day][1] += row["total_spent"]

    total_orders = sum(v[0] for v in buckets.values()) or 1
    result = []
    for name in WEEKDAY_NAMES:
        count, spent = buckets[name]
        result.append(
            {
                "day": name,
                "order_count": count,
                "total_spent": round(spent, 2),
                "percentage": round((count / total_orders) * 100, 1),
            }
        )
    return result


def weekday_vs_weekend() -> dict:
    db = get_db()
    rows = db.execute("SELECT order_date, total_amount FROM orders").fetchall()

    weekday = {"orders": 0, "total_spent": 0.0}
    weekend = {"orders": 0, "total_spent": 0.0}
    for row in rows:
        bucket = weekend if is_weekend(row["order_date"]) else weekday
        bucket["orders"] += 1
        bucket["total_spent"] += row["total_amount"] or 0

    for bucket in (weekday, weekend):
        bucket["total_spent"] = round(bucket["total_spent"], 2)
        bucket["avg_order_value"] = round(bucket["total_spent"] / bucket["orders"], 2) if bucket["orders"] else 0

    return {"weekday": weekday, "weekend": weekend}


def repeat_restaurant_stats() -> dict:
    db = get_db()
    rows = db.execute(
        """
        SELECT r.id, r.name, COUNT(o.id) AS order_count,
               COALESCE(SUM(o.total_amount),0) AS total_spent,
               MIN(o.order_date) AS first_order_date,
               MAX(o.order_date) AS last_order_date
        FROM restaurants r
        JOIN orders o ON o.restaurant_id = r.id
        GROUP BY r.id
        """
    ).fetchall()

    total_restaurants = len(rows)
    repeat_rows = [r for r in rows if r["order_count"] > 1]
    repeat_restaurants = len(repeat_rows)
    rate = round((repeat_restaurants / total_restaurants) * 100, 1) if total_restaurants else 0

    most_repeated = max(rows, key=lambda r: r["order_count"], default=None)
    longest_history = None
    highest_spending = max(rows, key=lambda r: r["total_spent"], default=None)

    longest_days = -1
    for r in rows:
        first = date.fromisoformat(r["first_order_date"])
        last = date.fromisoformat(r["last_order_date"])
        span = (last - first).days
        if span > longest_days:
            longest_days = span
            longest_history = r

    return {
        "total_restaurants": total_restaurants,
        "repeat_restaurants": repeat_restaurants,
        "repeat_restaurant_rate": rate,
        "most_repeated_restaurant": dict(most_repeated) if most_repeated else None,
        "longest_history_restaurant": dict(longest_history) if longest_history else None,
        "highest_spending_restaurant": dict(highest_spending) if highest_spending else None,
    }


def recent_orders(limit=10) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT o.id, o.order_date, o.platform, o.total_amount,
               r.name AS restaurant_name, c.name AS cuisine_name
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        ORDER BY o.order_date DESC, o.order_time DESC, o.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def monthly_growth() -> float | None:
    db = get_db()
    rows = db.execute(
        """
        SELECT strftime('%Y-%m', order_date) AS month, COALESCE(SUM(total_amount),0) AS total
        FROM orders GROUP BY month ORDER BY month DESC LIMIT 2
        """
    ).fetchall()
    if len(rows) < 2:
        return None
    current, previous = rows[0]["total"], rows[1]["total"]
    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 1)
