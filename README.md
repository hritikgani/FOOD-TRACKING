# Food Order Tracker

A personal analytics app for understanding your Zomato/Swiggy food-ordering habits: spending, platform mix, favorite restaurants and cuisines, ordering times, and repeat-order behavior. Not a food-ordering app -- it only tracks orders you've already placed.

## Stack

Flask + Postgres (via `psycopg2`, raw SQL, no ORM) + server-rendered Jinja templates + Tailwind (CDN) + Chart.js (CDN), with light/dark theme support. `openpyxl` handles Excel import/export. No Node/JS build step required.

## Running it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python run.py
```

Then open http://localhost:5050. No database setup needed: with `DATABASE_URL` unset, the app spins up (and reuses) a local embedded Postgres via the `pgserver` package, stored in `data/pgdata/` -- real Postgres semantics locally, zero manual setup, and no drift from what runs in production.

## Running tests

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Runs against the same embedded local Postgres (one shared instance for the whole run; tables are truncated between tests for isolation). Covers the analytics aggregations (KPIs, platform split, repeat-restaurant rate, weekday/weekend, time-of-day buckets, monthly grouping), restaurant-name normalization, order validation, duplicate detection, and CSV/Excel column auto-mapping.

## Deploying (Vercel + Postgres)

This app needs a real, persistent Postgres database in production -- Vercel's serverless filesystem is ephemeral/read-only outside `/tmp`, so SQLite (or any local-file storage) doesn't work there.

1. **Provision a Postgres database.** Easiest path: in your Vercel project, Storage tab -> add a Postgres database (backed by Neon). Or bring your own from [Neon](https://neon.tech), [Supabase](https://supabase.com), etc.
2. **Set environment variables** in Vercel project settings:
   - `DATABASE_URL` -- the connection string from step 1 (use the pooled connection string if your provider offers one, e.g. Neon's `-pooler` host, since serverless functions open a fresh connection per invocation).
   - `SECRET_KEY` -- any long random string (signs Flask's session/flash cookies).
3. **Deploy.** `requirements.txt` (production) intentionally excludes `pgserver` (a bundled Postgres binary, dev-only) -- Vercel installs only `Flask`, `openpyxl`, and `psycopg2-binary`. The schema (`app/schema.sql`) is applied automatically on first request via `CREATE TABLE IF NOT EXISTS`, so there's no separate migration step to run.

Vercel's Python/Flask support needs `[tool.vercel] entrypoint = "run:app"` in `pyproject.toml` (already set up in this repo) to find the app object.

## Project layout

```
app/
  db.py, schema.sql       Postgres schema + connection handling (psycopg2, sqlite3.Connection-shaped wrapper)
  services/               business logic (analytics, orders, importer, exporter, insights, validation)
  routes/                 Flask blueprints (dashboard, orders, analytics, restaurants, settings, import, api)
  templates/               Jinja templates (Tailwind classes, Chart.js via inline scripts)
  static/                 CSS + vanilla JS (charts.js, theme.js, orders.js, main.js)
tests/                    unittest suite for the calculation/validation layer
data/                     local embedded Postgres data dir when DATABASE_URL is unset (gitignored)
```

## Notes

- Importing a CSV/XLSX walks through: upload -> map columns -> preview & validate -> confirm. This is a multi-request flow, so the in-progress session is stored in Postgres (`import_sessions` table), not on local disk -- it survives landing on a different serverless container between requests. Invalid rows are always skipped automatically (fix the source file and re-upload to include them); duplicates (same date + restaurant + amount + platform) can be skipped or imported anyway.
- Restaurant names are normalized (case/punctuation-insensitive) so "Domino's", "Dominos", and "Domino's" collapse into one restaurant.
- Light/dark theme: a quick toggle (sidebar + mobile topbar) plus a System/Light/Dark option in Settings, both persisted to `localStorage` and to the database. Charts re-theme live on toggle, no page reload.
- Settings -> Clear All Data permanently deletes everything (type DELETE to confirm) and resets ID sequences. Export first if you want a backup.
