from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_nju_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("NJU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/NJU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_NJU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "basic_lab"]
    assert highlights["history"]["highlight_node_ids"] == [
        "er_yuan_square",
        "nju_ding",
        "museum",
        "observatory",
    ]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_east",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_nju_001"
    assert {"user_nju_001", "user_nju_002", "user_nju_003"} <= user_ids
    assert {"图书馆", "杜厦", "二源", "南大鼎", "九食堂", "校园生活"} <= interest_values


def test_nju_interest_recommendation_prefers_nju_specific_landmarks_and_canteens():
    service = DemoUIService("NJU")

    study_response = service.scenic_search(
        {
            "user_id": "user_nju_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )
    history_response = service.scenic_search(
        {
            "user_id": "user_nju_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_nju_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert history_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_nju_001"
    assert history_response["metadata"]["user_interest_context"]["user_id"] == "user_nju_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_nju_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    history_top = [item["route_target_node_id"] for item in history_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert "teaching_building" in study_top[:3]
    assert history_top[0] in {"er_yuan_square", "nju_ding"}
    assert {"er_yuan_square", "nju_ding"} <= set(history_top[:3])
    assert "museum" in history_top[:5]
    assert campus_life_top[0] == "canteen"
    assert "canteen_east" in campus_life_top[:5]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert history_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert "杜厦" in study_response["results"][0]["interest_reason"]
    assert any(token in history_response["results"][0]["interest_reason"] for token in ("二源", "南大鼎", "校史"))
    assert "九食堂" in campus_life_response["results"][0]["interest_reason"]
