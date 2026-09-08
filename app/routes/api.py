from flask import Blueprint, jsonify, request

from app.services import analytics

bp = Blueprint("api", __name__, url_prefix="/api")

MONTHS_BACK_BY_PERIOD = {"7d": 1, "30d": 1, "3m": 3, "6m": 6, "12m": 12, "all": 60}


@bp.route("/monthly-spending")
def monthly_spending():
    period = request.args.get("period", "12m")
    months_back = MONTHS_BACK_BY_PERIOD.get(period, 12)
    data = analytics.monthly_spending(months_back=months_back)
    return jsonify(data)
