#!/usr/bin/env python3
"""Verify that selected commercial records merge without replacing handbook data."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from apply_trip_decisions import apply


def main() -> int:
    profile = {
        "trip": {"start_date": "2026-11-10", "end_date": "2026-11-14"},
        "transport": {"status": "pending", "legs": []},
        "stays": [{"status": "pending", "place_id": None}],
        "places": [{"id": "sight-1", "type": "sight", "display_name": "保留的景点"}],
    }
    decisions = {
        "schema_version": 1,
        "flight": {
            "status": "selected",
            "selected_record": {
                "id": "flight-1",
                "name": "完整往返组合",
                "effective_price_cny": 3200,
                "baggage": "每人 1 件托运行李",
                "baggage_status": "verified",
                "snapshot_at": "2026-09-08T10:00:00Z",
                "source_url": "https://example.com/flight",
                "outbound": {"date": "2026-11-10", "flight_number": "XY100", "origin": "AAA", "destination": "BBB", "departure_time": "09:00", "arrival_time": "12:00"},
                "return": {"date": "2026-11-14", "flight_number": "XY101", "origin": "BBB", "destination": "AAA", "departure_time": "18:00", "arrival_time": "21:00"},
            },
        },
        "stay": {
            "status": "selected",
            "selected_record": {
                "id": "hotel-1",
                "name": "结构测试酒店",
                "area": "Central",
                "address": "Test Address",
                "why_recommended": "与每日路线衔接稳定。",
                "source_url": "https://example.com/hotel",
                "images": [{"file": "assets/hotel-1.jpg"}, {"file": "assets/hotel-2.jpg"}],
                "nightly_price_cny": 900,
                "total_price_cny": 3600,
                "room": "标准双人房",
                "snapshot_at": "2026-09-08T10:00:00Z",
                "availability_status": "available",
                "occupancy": "2 adults",
            },
        },
    }
    with tempfile.TemporaryDirectory(prefix="travel-decision-import-") as raw:
        root = Path(raw)
        (root / "trip-decisions.json").write_text(json.dumps(decisions), encoding="utf-8")
        merged = apply(root, profile)

    assert merged["transport"]["status"] == "confirmed"
    assert [leg["service_number"] for leg in merged["transport"]["legs"]] == ["XY100", "XY101"]
    assert merged["stays"][0]["place_id"] == "hotel-1"
    assert merged["places"][0]["id"] == "sight-1", "handbook places must survive decision import"
    assert any(place.get("id") == "hotel-1" for place in merged["places"])
    print("PASS selected flight/stay records merge before profile validation and signing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
