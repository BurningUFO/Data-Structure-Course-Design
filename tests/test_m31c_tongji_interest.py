from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_tongji_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("TONGJI")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/TONGJI/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_TONGJI"
    assert highlights["study"]["highlight_node_ids"] == ["library", "architecture_college", "lab_building"]
    assert highlights["landmark"]["highlight_node_ids"] == ["sakura_avenue", "auditorium", "architecture_college"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_north",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_tongji_001"
    assert {"user_tongji_001", "user_tongji_002", "user_tongji_003"} <= user_ids
    assert {"图书馆", "自习", "建筑学院", "樱花大道", "大礼堂", "学苑食堂", "北苑食堂", "校园生活"} <= interest_values


def test_tongji_interest_recommendation_prefers_local_landmarks_and_canteens():
    service = DemoUIService("TONGJI")

    study_response = service.scenic_search(
        {
            "user_id": "user_tongji_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    landmark_response = service.scenic_search(
        {
            "user_id": "user_tongji_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_tongji_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "dormitory_1",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert landmark_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_tongji_001"
    assert landmark_response["metadata"]["user_interest_context"]["user_id"] == "user_tongji_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_tongji_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    landmark_top = [item["route_target_node_id"] for item in landmark_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert "architecture_college" in study_top[:3]
    assert set(landmark_top[:2]) == {"sakura_avenue", "auditorium"}
    assert campus_life_top[0] == "canteen"
    assert "canteen_north" in campus_life_top[:5]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert landmark_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert any(token in study_response["results"][0]["interest_reason"] for token in ("图书馆", "自习", "建筑"))
    assert any(token in landmark_response["results"][0]["interest_reason"] for token in ("樱花大道", "大礼堂", "摄影"))
    assert any(token in campus_life_response["results"][0]["interest_reason"] for token in ("学苑食堂", "北苑食堂", "校园生活"))
