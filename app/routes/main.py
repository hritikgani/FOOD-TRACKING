from flask import Blueprint, render_template

from app.services import analytics, insights
from app.services.settings import get_setting

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    kpis = analytics.kpi_summary()

    if kpis["total_orders"] == 0:
        return render_template("dashboard.html", has_data=False)

    currency = get_setting("currency_symbol", "₹")

    context = {
        "has_data": True,
        "kpis": kpis,
        "platforms": analytics.platform_stats(),
        "monthly": analytics.monthly_spending(months_back=12),
        "top_restaurants": analytics.top_restaurants(limit=5),
        "cuisines": analytics.cuisine_distribution()[:6],
        "top_items": analytics.top_food_items(limit=6),
        "time_distribution": analytics.ordering_time_distribution(),
        "recent_orders": analytics.recent_orders(limit=8),
        "insights": insights.generate_insights(currency),
    }
    return render_template("dashboard.html", **context)
