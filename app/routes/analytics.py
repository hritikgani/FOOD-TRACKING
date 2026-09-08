from flask import Blueprint, render_template, request

from app.services import analytics

bp = Blueprint("analytics", __name__, url_prefix="/analytics")

PERIOD_LABELS = {
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "3m": "Last 3 months",
    "6m": "Last 6 months",
    "12m": "Last 12 months",
    "all": "All time",
}


@bp.route("/")
def index():
    kpis = analytics.kpi_summary()
    if kpis["total_orders"] == 0:
        return render_template("analytics.html", has_data=False)

    period = request.args.get("period", "12m")
    if period not in PERIOD_LABELS:
        period = "12m"

    months_back = {"7d": 1, "30d": 1, "3m": 3, "6m": 6, "12m": 12, "all": 60}[period]

    context = {
        "has_data": True,
        "period": period,
        "period_labels": PERIOD_LABELS,
        "kpis": kpis,
        "monthly": analytics.monthly_spending(months_back=months_back),
        "monthly_growth": analytics.monthly_growth(),
        "platforms": analytics.platform_stats(),
        "restaurants": analytics.top_restaurants(limit=10, sort_by=request.args.get("restaurant_sort", "orders")),
        "restaurant_sort": request.args.get("restaurant_sort", "orders"),
        "cuisines": analytics.cuisine_distribution(),
        "food_items": analytics.top_food_items(limit=15),
        "time_distribution": analytics.ordering_time_distribution(),
        "day_distribution": analytics.day_of_week_distribution(),
        "weekday_vs_weekend": analytics.weekday_vs_weekend(),
        "repeat_stats": analytics.repeat_restaurant_stats(),
    }
    return render_template("analytics.html", **context)
