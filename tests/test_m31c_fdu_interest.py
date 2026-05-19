from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_fdu_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("FDU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/FDU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_FDU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "lab_building"]
    assert highlights["history"]["highlight_node_ids"] == ["guanghua_tower", "xianghui_hall", "history_museum"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_north",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_fdu_001"
    assert {"user_fdu_001", "user_fdu_002", "user_fdu_003"} <= user_ids
    assert {"图书馆", "文科图书馆", "第三教学楼", "光华楼", "相辉堂", "南区食堂"} <= interest_values


def test_fdu_interest_recommendation_prefers_fdu_specific_landmarks_and_canteens():
    service = DemoUIService("FDU")

    study_response = service.scenic_search(
        {
            "user_id": "user_fdu_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    history_response = service.scenic_search(
        {
            "user_id": "user_fdu_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_fdu_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "dormitory_1",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert history_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_fdu_001"
    assert history_response["metadata"]["user_interest_context"]["user_id"] == "user_fdu_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_fdu_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    history_top = [item["route_target_node_id"] for item in history_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert "teaching_building" in study_top[:3]
    assert history_top[0] in {"guanghua_tower", "xianghui_hall"}
    assert {"guanghua_tower", "xianghui_hall"} <= set(history_top[:3])
    assert "history_museum" in history_top[:5]
    assert campus_life_top[0] == "canteen"
    assert "canteen_north" in campus_life_top[:3]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert history_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert "图书馆" in study_response["results"][0]["interest_reason"]
    assert any(token in history_response["results"][0]["interest_reason"] for token in ("光华楼", "相辉堂", "校史"))
    assert any(token in campus_life_response["results"][0]["interest_reason"] for token in ("南区食堂", "食堂"))
