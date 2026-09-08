import shutil
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.config import Config
from app.services import analytics
from app.services import orders as orders_service
from app.services.importer import auto_detect_mapping
from app.services.validation import validate_order_fields
from app.utils.normalize import normalize_name


class TestConfig(Config):
    pass


class AnalyticsTestCase(unittest.TestCase):
    """Exercises the aggregation math in app/services/analytics.py against a
    real (temp file) SQLite database -- these are the numbers the dashboard
    and analytics pages are built on, so they're worth pinning down."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        TestConfig.DATABASE_PATH = str(Path(self.tmp_dir) / "test.db")
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _add_order(self, **overrides):
        data = {
            "order_date": "2026-09-01",
            "platform": "zomato",
            "restaurant": "Test Restaurant",
            "total_amount": "300",
        }
        data.update(overrides)
        cleaned, errors = validate_order_fields(data)
        self.assertEqual(errors, [])
        return orders_service.create_order(cleaned)

    def test_kpi_summary_totals(self):
        self._add_order(total_amount="100")
        self._add_order(total_amount="200", restaurant="Other Place")
        kpis = analytics.kpi_summary()
        self.assertEqual(kpis["total_orders"], 2)
        self.assertEqual(kpis["total_spent"], 300)
        self.assertEqual(kpis["avg_order_value"], 150)
        self.assertEqual(kpis["unique_restaurants"], 2)

    def test_platform_stats_percentage(self):
        self._add_order(platform="zomato")
        self._add_order(platform="swiggy")
        self._add_order(platform="swiggy")
        stats = {p["platform"]: p for p in analytics.platform_stats()}
        self.assertEqual(stats["zomato"]["order_count"], 1)
        self.assertEqual(stats["swiggy"]["order_count"], 2)
        self.assertAlmostEqual(stats["swiggy"]["order_percentage"], 66.7, places=1)

    def test_repeat_restaurant_rate(self):
        self._add_order(restaurant="Repeat Place")
        self._add_order(restaurant="Repeat Place")
        self._add_order(restaurant="One-time Place")
        stats = analytics.repeat_restaurant_stats()
        self.assertEqual(stats["total_restaurants"], 2)
        self.assertEqual(stats["repeat_restaurants"], 1)
        self.assertEqual(stats["repeat_restaurant_rate"], 50.0)

    def test_weekday_vs_weekend_split(self):
        # 2026-09-05 is a Saturday, 2026-09-07 is a Monday.
        self._add_order(order_date="2026-09-05", total_amount="400")
        self._add_order(order_date="2026-09-07", total_amount="200")
        result = analytics.weekday_vs_weekend()
        self.assertEqual(result["weekend"]["orders"], 1)
        self.assertEqual(result["weekend"]["total_spent"], 400)
        self.assertEqual(result["weekday"]["orders"], 1)
        self.assertEqual(result["weekday"]["total_spent"], 200)

    def test_ordering_time_bucket(self):
        self._add_order(order_time="21:30")
        dist = {row["period"]: row for row in analytics.ordering_time_distribution()}
        self.assertEqual(dist["Night"]["order_count"], 1)
        self.assertEqual(dist["Morning"]["order_count"], 0)

    def test_duplicate_detection(self):
        self._add_order(restaurant="Dup Place", total_amount="250", order_date="2026-09-05")
        self.assertTrue(
            orders_service.check_possible_duplicate("2026-09-05", "Dup Place", 250.0, "zomato")
        )
        self.assertFalse(
            orders_service.check_possible_duplicate("2026-09-06", "Dup Place", 250.0, "zomato")
        )

    def test_restaurant_normalization_prevents_duplicate_rows(self):
        self._add_order(restaurant="Domino's")
        self._add_order(restaurant="Dominos", total_amount="150")
        kpis = analytics.kpi_summary()
        self.assertEqual(kpis["unique_restaurants"], 1)
        self.assertEqual(kpis["total_orders"], 2)


class NormalizeTestCase(unittest.TestCase):
    def test_normalize_apostrophe_variants(self):
        self.assertEqual(normalize_name("Domino's"), normalize_name("Dominos"))
        self.assertEqual(normalize_name("Domino’s"), normalize_name("Dominos"))

    def test_normalize_case_and_whitespace(self):
        self.assertEqual(normalize_name("  Pizza   Hut  "), "pizza hut")


class ValidationTestCase(unittest.TestCase):
    def test_missing_required_fields(self):
        cleaned, errors = validate_order_fields({})
        self.assertIn("Invalid or missing order date", errors)
        self.assertIn("Restaurant name is missing", errors)

    def test_total_computed_from_components(self):
        cleaned, errors = validate_order_fields(
            {
                "order_date": "2026-09-01",
                "platform": "swiggy",
                "restaurant": "Test",
                "subtotal": "200",
                "delivery_fee": "30",
                "discount": "20",
            }
        )
        self.assertEqual(errors, [])
        self.assertEqual(cleaned["total_amount"], 210.0)

    def test_invalid_amount_flagged(self):
        cleaned, errors = validate_order_fields(
            {
                "order_date": "2026-09-01",
                "platform": "zomato",
                "restaurant": "Test",
                "total_amount": "not-a-number",
            }
        )
        self.assertTrue(any("not numeric" in e for e in errors))

    def test_currency_symbol_and_commas_stripped(self):
        cleaned, errors = validate_order_fields(
            {
                "order_date": "08/09/2026",
                "platform": "zomato",
                "restaurant": "Test",
                "total_amount": "₹1,240.50",
            }
        )
        self.assertEqual(errors, [])
        self.assertEqual(cleaned["total_amount"], 1240.50)
        self.assertEqual(cleaned["order_date"], "2026-09-08")


class ImporterMappingTestCase(unittest.TestCase):
    def test_auto_detect_common_headers(self):
        headers = ["Order Date", "Restaurant Name", "Total Amount", "Platform"]
        mapping = auto_detect_mapping(headers)
        self.assertEqual(mapping["order_date"], "Order Date")
        self.assertEqual(mapping["restaurant"], "Restaurant Name")
        self.assertEqual(mapping["total_amount"], "Total Amount")
        self.assertEqual(mapping["platform"], "Platform")


if __name__ == "__main__":
    unittest.main()
