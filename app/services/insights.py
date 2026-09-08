from __future__ import annotations

from app.services import analytics


def generate_insights(currency="₹") -> list[dict]:
    """Build a list of natural-language insight strings computed live from
    the current data. Returns [] when there isn't enough data yet."""
    kpis = analytics.kpi_summary()
    if kpis["total_orders"] == 0:
        return []

    insights = []

    growth = analytics.monthly_growth()
    if growth is not None:
        direction = "increased" if growth >= 0 else "decreased"
        insights.append(
            {
                "icon": "💰" if growth >= 0 else "📉",
                "text": f"Your food spending {direction} by {abs(growth)}% compared with last month.",
            }
        )

    platforms = analytics.platform_stats()
    leader = max(platforms, key=lambda p: p["order_count"])
    if leader["order_count"] > 0:
        insights.append(
            {
                "icon": "📱",
                "text": f"{leader['platform'].capitalize()} accounts for {leader['order_percentage']}% of your food orders.",
            }
        )

    top = analytics.top_restaurants(limit=1)
    if top:
        insights.append(
            {
                "icon": "🏆",
                "text": f"{top[0]['name']} is your most frequently ordered restaurant with {top[0]['order_count']} orders.",
            }
        )

    cuisines = analytics.cuisine_distribution()
    if cuisines:
        top_cuisine = cuisines[0]
        insights.append(
            {
                "icon": "🍛",
                "text": f"{top_cuisine['name']} cuisine is your most ordered cuisine, at {top_cuisine['order_percentage']}% of orders.",
            }
        )

    time_dist = analytics.ordering_time_distribution()
    peak = max(time_dist, key=lambda t: t["order_count"])
    if peak["order_count"] > 0:
        insights.append({"icon": "🌙", "text": f"You order most frequently during the {peak['period'].lower()}."})

    repeat_stats = analytics.repeat_restaurant_stats()
    if repeat_stats["total_restaurants"] > 0:
        insights.append(
            {
                "icon": "🔁",
                "text": f"{repeat_stats['repeat_restaurant_rate']}% of your restaurants are repeat restaurants.",
            }
        )

    insights.append(
        {
            "icon": "🧾",
            "text": f"Your average food order is {currency}{kpis['avg_order_value']:.0f}.",
        }
    )

    weekday_weekend = analytics.weekday_vs_weekend()
    wd, we = weekday_weekend["weekday"], weekday_weekend["weekend"]
    if wd["orders"] and we["orders"]:
        if we["avg_order_value"] > wd["avg_order_value"]:
            insights.append(
                {
                    "icon": "🎉",
                    "text": "You tend to spend more per order on weekends than on weekdays.",
                }
            )
        else:
            insights.append(
                {
                    "icon": "📆",
                    "text": "You tend to spend more per order on weekdays than on weekends.",
                }
            )

    return insights
