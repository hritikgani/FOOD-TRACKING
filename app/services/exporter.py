from __future__ import annotations

import csv
import io

from openpyxl import Workbook

from app.db import get_db

EXPORT_COLUMNS = [
    ("order_date", "Order Date"),
    ("order_time", "Order Time"),
    ("platform", "Platform"),
    ("restaurant_name", "Restaurant"),
    ("cuisine_name", "Cuisine"),
    ("items", "Food Items"),
    ("subtotal", "Subtotal"),
    ("discount", "Discount"),
    ("delivery_fee", "Delivery Fee"),
    ("platform_fee", "Platform Fee"),
    ("tax", "Tax"),
    ("total_amount", "Total Amount"),
    ("notes", "Notes"),
]


def _fetch_all_orders_for_export() -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT o.*, r.name AS restaurant_name, c.name AS cuisine_name
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        LEFT JOIN cuisines c ON c.id = o.cuisine_id
        ORDER BY o.order_date DESC
        """
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        items = db.execute(
            "SELECT item_name FROM order_items WHERE order_id = ? ORDER BY id", (d["id"],)
        ).fetchall()
        d["items"] = ", ".join(i["item_name"] for i in items)
        results.append(d)
    return results


def export_csv() -> str:
    rows = _fetch_all_orders_for_export()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([label for _, label in EXPORT_COLUMNS])
    for row in rows:
        writer.writerow([row.get(key, "") for key, _ in EXPORT_COLUMNS])
    return output.getvalue()


def export_xlsx() -> bytes:
    rows = _fetch_all_orders_for_export()
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append([label for _, label in EXPORT_COLUMNS])
    for row in rows:
        ws.append([row.get(key, "") for key, _ in EXPORT_COLUMNS])
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 40)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
