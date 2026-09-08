from __future__ import annotations

from app.utils.dates import parse_date, parse_time

VALID_PLATFORMS = {"zomato", "swiggy"}

NUMERIC_FIELDS = ["subtotal", "discount", "delivery_fee", "platform_fee", "tax", "total_amount"]


def to_float(value):
    """Parse a currency-ish string ("₹1,234.50") into a float, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("₹", "").replace(",", "").replace("Rs.", "").replace("Rs", "").strip()
    return round(float(text), 2)


def validate_order_fields(data: dict) -> tuple[dict, list[str]]:
    """Validate + normalize a raw order dict (from a form or an import row).
    Returns (cleaned_data, errors). cleaned_data is always returned so the
    caller can show what parsed, even when errors are present.
    """
    errors: list[str] = []
    cleaned: dict = {}

    order_date = parse_date(data.get("order_date"))
    if not order_date:
        errors.append("Invalid or missing order date")
    cleaned["order_date"] = order_date

    raw_time = data.get("order_time")
    cleaned["order_time"] = parse_time(raw_time) if raw_time else None

    platform = str(data.get("platform") or "").strip().lower()
    if platform not in VALID_PLATFORMS:
        errors.append("Platform must be Zomato or Swiggy")
    cleaned["platform"] = platform if platform in VALID_PLATFORMS else None

    restaurant = str(data.get("restaurant") or "").strip()
    if not restaurant:
        errors.append("Restaurant name is missing")
    cleaned["restaurant"] = restaurant

    cuisine = str(data.get("cuisine") or "").strip()
    cleaned["cuisine"] = cuisine or None

    for field in ["subtotal", "discount", "delivery_fee", "platform_fee", "tax"]:
        raw = data.get(field)
        if raw in (None, ""):
            cleaned[field] = None
            continue
        try:
            cleaned[field] = to_float(raw)
        except ValueError:
            errors.append(f"{field.replace('_', ' ').title()} is not numeric")
            cleaned[field] = None

    total_raw = data.get("total_amount")
    total = None
    if total_raw not in (None, ""):
        try:
            total = to_float(total_raw)
        except ValueError:
            errors.append("Amount is not numeric")
    if total is None:
        components = [cleaned.get(k) for k in ("subtotal", "delivery_fee", "platform_fee", "tax")]
        if any(c is not None for c in components):
            total = round(sum(c or 0 for c in components) - (cleaned.get("discount") or 0), 2)
    if total is None:
        errors.append("Total amount is missing or not numeric")
    cleaned["total_amount"] = total

    notes = str(data.get("notes") or "").strip()
    cleaned["notes"] = notes or None

    cleaned["food_items"] = data.get("food_items")

    return cleaned, errors
