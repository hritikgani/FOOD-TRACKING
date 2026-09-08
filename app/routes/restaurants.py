from flask import Blueprint, abort, render_template, request

from app.services import restaurants as restaurants_service

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


@bp.route("/")
def index():
    sort_by = request.args.get("sort", "orders")
    order = request.args.get("order", "desc")
    summaries = restaurants_service.restaurant_summaries(sort_by=sort_by, order=order)
    return render_template(
        "restaurants/list.html",
        restaurants=summaries,
        sort_by=sort_by,
        order=order,
        has_data=len(summaries) > 0,
    )


@bp.route("/<int:restaurant_id>")
def detail(restaurant_id):
    data = restaurants_service.restaurant_detail(restaurant_id)
    if not data:
        abort(404)
    return render_template("restaurants/detail.html", **data)
