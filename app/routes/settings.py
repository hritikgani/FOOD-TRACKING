from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from app.services import exporter
from app.services.cuisines import list_cuisines
from app.services.settings import clear_all_data, get_all_settings, set_setting

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
def index():
    return render_template("settings.html", settings=get_all_settings(), cuisines=list_cuisines())


@bp.route("/update", methods=["POST"])
def update():
    currency_symbol = request.form.get("currency_symbol", "₹").strip() or "₹"
    theme = request.form.get("theme", "system")
    set_setting("currency_symbol", currency_symbol)
    set_setting("theme", theme)
    flash("Settings saved.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/theme", methods=["POST"])
def set_theme():
    """Lightweight endpoint the nav's quick theme toggle calls via fetch --
    persists the choice server-side without a page navigation/reload."""
    theme = request.form.get("theme", "").strip().lower()
    if theme not in ("light", "dark", "system"):
        return {"error": "invalid theme"}, 400
    set_setting("theme", theme)
    return "", 204


@bp.route("/clear-data", methods=["POST"])
def clear_data():
    confirmation = request.form.get("confirm", "")
    if confirmation != "DELETE":
        flash('Type "DELETE" exactly to confirm clearing all data.', "error")
        return redirect(url_for("settings.index"))
    clear_all_data()
    flash("All order data has been deleted.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/export/csv")
def export_csv():
    csv_data = exporter.export_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=food_orders_export.csv"},
    )


@bp.route("/export/xlsx")
def export_xlsx():
    xlsx_data = exporter.export_xlsx()
    return Response(
        xlsx_data,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=food_orders_export.xlsx"},
    )
