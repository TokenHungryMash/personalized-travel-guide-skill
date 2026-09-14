"""Fast regression checks for incoming source legs and outgoing Trip Mode legs."""
import json
import re
import unittest
from pathlib import Path
from build_render_bindings import adapt_runtimes, hero


class TransferBindingsTest(unittest.TestCase):
    def test_incoming_legs_are_displayed_after_previous_stop(self):
        profile = {"display_name": "测试", "destination": "test", "itinerary": [{"stops": [
            {"place_id": "a", "transfer_minutes": 0, "distance_km": 0, "transport_mode": "抵达"},
            {"place_id": "b", "transfer_minutes": 20, "distance_km": 4, "transport_mode": "地铁"},
            {"place_id": "c", "transfer_minutes": 15, "distance_km": 1.1, "transport_mode": "步行"},
        ]}]}
        canonical = Path(__file__).resolve().parent.parent / "assets" / "canonical" / "product"
        runtime = next(r["content"] for r in adapt_runtimes(profile, canonical) if r["path"] == "trip-mode.js")
        stops = json.loads(re.search(r"var TRIP_MODE_DATA=(.*?);", runtime).group(1))[0]["stops"]
        self.assertEqual([(s["transport_mode"], s["transfer_minutes"], s["distance_km"]) for s in stops],
                         [("地铁", 20, 4), ("步行", 15, 1.1), ("", None, None)])
        self.assertEqual(profile["itinerary"][0]["stops"][0]["transfer_minutes"], 0)

    def test_pending_cover_date(self):
        rendered = hero({"display_name": "测试", "cover": {"kicker": "TEST", "summary": "测试摘要"}, "trip": {"start_date": "pending", "end_date": "pending", "days": 4}})
        self.assertIn("日期待定", rendered)
        self.assertNotIn("pending", rendered)


if __name__ == "__main__":
    unittest.main()
