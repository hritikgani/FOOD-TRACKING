# Food Order Tracker

A personal analytics app for understanding your Zomato/Swiggy food-ordering habits: spending, platform mix, favorite restaurants and cuisines, ordering times, and repeat-order behavior. Not a food-ordering app -- it only tracks orders you've already placed.

## Stack

Flask + SQLite (stdlib `sqlite3`, no ORM) + server-rendered Jinja templates + Tailwind (CDN) + Chart.js (CDN) + `openpyxl` for Excel import/export. No Node/JS build step required.

## Running it

```bash
source venv/bin/activate
python run.py
```

Then open http://localhost:5050. The SQLite database lives at `data/food_orders.db` and is created automatically on first run.

## Running tests

```bash
source venv/bin/activate
python -m unittest discover -s tests -v
```

Covers the analytics aggregations (KPIs, platform split, repeat-restaurant rate, weekday/weekend, time-of-day buckets), restaurant-name normalization, order validation, duplicate detection, and CSV/Excel column auto-mapping.

## Project layout

```
app/
  db.py, schema.sql       SQLite schema + connection handling
  services/               business logic (analytics, orders, importer, exporter, insights, validation)
  routes/                 Flask blueprints (dashboard, orders, analytics, restaurants, settings, import, api)
  templates/               Jinja templates (Tailwind classes, Chart.js via inline scripts)
  static/                 CSS + vanilla JS (charts.js, orders.js, main.js)
tests/                    unittest suite for the calculation/validation layer
data/                     SQLite DB + in-progress import sessions (gitignored)
```

## Notes

- Importing a CSV/XLSX walks through: upload -> map columns -> preview & validate -> confirm. Invalid rows are always skipped automatically (fix the source file and re-upload to include them); duplicates (same date + restaurant + amount + platform) can be skipped or imported anyway.
- Restaurant names are normalized (case/punctuation-insensitive) so "Domino's", "Dominos", and "Domino's" collapse into one restaurant.
- Settings -> Clear All Data permanently deletes everything (type DELETE to confirm). Export first if you want a backup.
