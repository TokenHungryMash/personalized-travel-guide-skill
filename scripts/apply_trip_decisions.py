#!/usr/bin/env python3
"""Merge structured pre-handbook choices into a destination profile without prose parsing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply(root: Path, profile: dict) -> dict:
    path = root / "trip-decisions.json"
    if not path.is_file():
        return profile
    decisions = json.loads(path.read_text(encoding="utf-8"))
    flight = decisions.get("flight", {})
    selected_flight = flight.get("selected_record") if flight.get("status") == "selected" else None
    if flight.get("status") == "selected" and not isinstance(selected_flight, dict):
        raise ValueError("flight status selected requires a complete selected_record")
    if isinstance(selected_flight, dict):
        legs = []
        for direction, key in (("去程", "outbound"), ("回程", "return")):
            route = selected_flight.get(key, {})
            segments = route.get("segments") if isinstance(route, dict) else None
            if not isinstance(segments, list) or not segments:
                segments = [route]
            for segment in segments:
                legs.append({
                    "direction": direction,
                    "date": segment.get("date", route.get("date", "")),
                    "service_number": segment.get("flight_number", segment.get("flight", "")),
                    "origin": segment.get("origin", segment.get("depart_airport", "")),
                    "destination": segment.get("destination", segment.get("arrival_airport", "")),
                    "departure_time": segment.get("departure_time", segment.get("depart", "")),
                    "arrival_time": segment.get("arrival_time", segment.get("arrival", "")),
                    "verification_status": segment.get("verification_status", selected_flight.get("schedule_verification_status", "verified" if selected_flight.get("source_url") and selected_flight.get("snapshot_at") else None)),
                    "source_url": segment.get("source_url", selected_flight.get("source_url")),
                    "checked_at": segment.get("checked_at", selected_flight.get("snapshot_at")),
                })
        profile["transport"] = {
            "status": "confirmed",
            "headline": selected_flight.get("name") or "已选往返航班",
            "legs": legs,
            "decision_summary": {
                "selection_id": selected_flight.get("id"),
                "base_price_cny": selected_flight.get("base_price_cny"),
                "effective_price_cny": selected_flight.get("effective_price_cny"),
                "baggage": selected_flight.get("baggage"),
                "baggage_status": selected_flight.get("baggage_status", selected_flight.get("price_status")),
                "snapshot_at": selected_flight.get("snapshot_at"),
                "source_url": selected_flight.get("source_url"),
                "price_status": selected_flight.get("price_status"),
            },
            "fineprint": "已同步机酒决策页的完整选择记录；付款与出发前仍需复核时刻、航站楼、行李及最终金额。",
        }

    stay = decisions.get("stay", {})
    selected_stay = stay.get("selected_record") if stay.get("status") == "selected" else None
    if stay.get("status") == "selected" and not isinstance(selected_stay, dict):
        raise ValueError("stay status selected requires a complete selected_record")
    if isinstance(selected_stay, dict):
        place_id = str(selected_stay.get("place_id") or selected_stay.get("id"))
        places = profile.setdefault("places", [])
        place = next((item for item in places if str(item.get("id")) == place_id), None)
        if place is None:
            place = {"id": place_id, "type": "hotel", "images": selected_stay.get("images", [])}
            places.append(place)
        place.update({
            "display_name": selected_stay.get("chinese_name") or selected_stay.get("name"),
            "english_name": selected_stay.get("official_name") or selected_stay.get("english_name") or selected_stay.get("name"),
            "area": selected_stay.get("area", ""),
            "address": selected_stay.get("address", ""),
            "transport_note": selected_stay.get("transport_note") or selected_stay.get("nearest_transport", ""),
            "description": selected_stay.get("why_recommended") or selected_stay.get("route_fit", ""),
            "source_url": selected_stay.get("source_url") or selected_stay.get("room_rate_source_url") or (selected_stay.get("inventory_evidence") or {}).get("room_rate_source_url", ""),
            "selection_price": {
                "nightly_price_cny": selected_stay.get("nightly_price_cny"),
                "total_price_cny": selected_stay.get("total_price_cny"),
                "room": selected_stay.get("room"),
                "snapshot_at": selected_stay.get("snapshot_at"),
                "availability_status": selected_stay.get("availability_status"),
                "price_status": selected_stay.get("price_status", "specified_date_verified" if selected_stay.get("availability_status") == "available" else "reference_only"),
                "occupancy": selected_stay.get("occupancy"),
            },
        })
        profile["stays"] = [{
            "status": "confirmed", "place_id": place_id,
            "check_in": selected_stay.get("check_in") or profile.get("trip", {}).get("start_date"),
            "check_out": selected_stay.get("check_out") or profile.get("trip", {}).get("end_date"),
            "notes": selected_stay.get("booking_caution", ""),
        }]
    return profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbench", type=Path)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    root = args.workbench.resolve()
    path = args.profile.resolve()
    profile = apply(root, json.loads(path.read_text(encoding="utf-8")))
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS applied structured trip decisions: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
