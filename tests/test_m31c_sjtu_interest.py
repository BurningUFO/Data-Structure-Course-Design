from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_sjtu_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("SJTU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/SJTU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_SJTU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "lab_building"]
    assert highlights["landmark"]["highlight_node_ids"] == ["siyuan_lake", "culture_square", "gymnasium"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_north",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_sjtu_001"
    assert {"user_sjtu_001", "user_sjtu_002", "user_sjtu_003"} <= user_ids
    assert {"图书馆", "东中院", "思源湖", "文化广场", "霍英东", "第一餐饮大楼", "校园生活"} <= interest_values


def test_sjtu_interest_recommendation_prefers_local_landmarks_and_canteens():
    service = DemoUIService("SJTU")

    study_response = service.scenic_search(
        {
            "user_id": "user_sjtu_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    landmark_response = service.scenic_search(
        {
            "user_id": "user_sjtu_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_sjtu_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert landmark_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_sjtu_001"
    assert landmark_response["metadata"]["user_interest_context"]["user_id"] == "user_sjtu_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_sjtu_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    landmark_top = [item["route_target_node_id"] for item in landmark_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert "teaching_building" in study_top[:3]
    assert "lab_building" in study_top[:5]
    assert landmark_top[0] in {"culture_square", "siyuan_lake"}
    assert {"culture_square", "siyuan_lake"} <= set(landmark_top[:3])
    assert campus_life_top[0] == "canteen"
    assert "canteen_north" in campus_life_top[:5]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert landmark_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert "图书馆" in study_response["results"][0]["interest_reason"]
    assert any(token in landmark_response["results"][0]["interest_reason"] for token in ("思源湖", "文化广场", "霍英东"))
    assert any(token in campus_life_response["results"][0]["interest_reason"] for token in ("第一餐饮大楼", "食堂", "校园生活"))
