from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.services import orders as orders_service
from app.services.cuisines import list_cuisines
from app.services.restaurants import list_restaurants
from app.services.validation import validate_order_fields

bp = Blueprint("orders", __name__, url_prefix="/orders")


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


SORT_OPTIONS = {
    "date_desc": ("order_date", "desc"),
    "date_asc": ("order_date", "asc"),
    "amount_desc": ("amount", "desc"),
    "amount_asc": ("amount", "asc"),
    "restaurant_asc": ("restaurant", "asc"),
}


@bp.route("/")
def index():
    args = request.args
    sort_key = args.get("sort", "date_desc")
    sort_by, sort_dir = SORT_OPTIONS.get(sort_key, SORT_OPTIONS["date_desc"])

    result = orders_service.list_orders(
        platform=args.get("platform") or None,
        restaurant_id=_int_or_none(args.get("restaurant_id")),
        cuisine_id=_int_or_none(args.get("cuisine_id")),
        date_from=args.get("date_from") or None,
        date_to=args.get("date_to") or None,
        min_amount=_float_or_none(args.get("min_amount")),
        max_amount=_float_or_none(args.get("max_amount")),
        search=args.get("search") or None,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=_int_or_none(args.get("page")) or 1,
        page_size=25,
    )
    return render_template(
        "orders/list.html",
        result=result,
        filters=args,
        sort_key=sort_key,
        restaurants=list_restaurants(),
        cuisines=list_cuisines(),
        has_any_orders=(orders_service.list_orders(page=1, page_size=1)["total"] > 0),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        cleaned, errors = validate_order_fields(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "orders/form.html", order=cleaned, errors=errors, cuisines=list_cuisines(),
                restaurants=list_restaurants(), mode="new"
            )
        order_id = orders_service.create_order(cleaned)
        flash("Order saved.", "success")
        return redirect(url_for("orders.detail", order_id=order_id))

    return render_template(
        "orders/form.html", order=None, errors=[], cuisines=list_cuisines(),
        restaurants=list_restaurants(), mode="new"
    )


@bp.route("/<int:order_id>")
def detail(order_id):
    order = orders_service.get_order(order_id)
    if not order:
        abort(404)
    return render_template("orders/detail.html", order=order)


@bp.route("/<int:order_id>/edit", methods=["GET", "POST"])
def edit(order_id):
    existing = orders_service.get_order(order_id)
    if not existing:
        abort(404)

    if request.method == "POST":
        cleaned, errors = validate_order_fields(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "orders/form.html", order=cleaned, errors=errors, cuisines=list_cuisines(),
                restaurants=list_restaurants(), mode="edit", order_id=order_id
            )
        orders_service.update_order(order_id, cleaned)
        flash("Order updated.", "success")
        return redirect(url_for("orders.detail", order_id=order_id))

    form_data = {
        "order_date": existing["order_date"],
        "order_time": existing["order_time"],
        "platform": existing["platform"],
        "restaurant": existing["restaurant_name"],
        "cuisine": existing["cuisine_name"],
        "subtotal": existing["subtotal"],
        "discount": existing["discount"],
        "delivery_fee": existing["delivery_fee"],
        "platform_fee": existing["platform_fee"],
        "tax": existing["tax"],
        "total_amount": existing["total_amount"],
        "notes": existing["notes"],
        "food_items": ", ".join(i["item_name"] for i in existing["line_items"]),
    }
    return render_template(
        "orders/form.html", order=form_data, errors=[], cuisines=list_cuisines(),
        restaurants=list_restaurants(), mode="edit", order_id=order_id
    )


@bp.route("/<int:order_id>/delete", methods=["POST"])
def delete(order_id):
    if orders_service.delete_order(order_id):
        flash("Order deleted.", "success")
    else:
        flash("This order could not be found -- it may have already been deleted.", "error")
    return redirect(url_for("orders.index"))
