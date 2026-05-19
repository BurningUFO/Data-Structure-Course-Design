from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_zju_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("ZJU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/ZJU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_ZJU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "teaching_building_2"]
    assert highlights["landmark"]["highlight_node_ids"] == ["qiushi_square", "qiushi_great_hall", "anzhong_building"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen_yinquan",
        "canteen",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] >= 3
    assert payload["default_user_id"] == "user_zju_001"
    assert {"user_zju_001", "user_zju_002", "user_zju_003"} <= user_ids
    assert {"图书馆", "求是", "大讲堂", "食堂", "银泉", "丹青"} <= interest_values


def test_zju_interest_recommendation_prefers_zju_specific_landmarks_and_canteens():
    service = DemoUIService("ZJU")

    study_response = service.scenic_search(
        {
            "user_id": "user_zju_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    landmark_response = service.scenic_search(
        {
            "user_id": "user_zju_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_zju_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert landmark_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_zju_001"
    assert landmark_response["metadata"]["user_interest_context"]["user_id"] == "user_zju_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_zju_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    landmark_top = [item["route_target_node_id"] for item in landmark_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert landmark_top[0] == "qiushi_square"
    assert "qiushi_great_hall" in landmark_top[:3]
    assert campus_life_top[0] == "canteen_yinquan"
    assert "canteen" in campus_life_top[:3]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert landmark_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert "图书馆" in study_response["results"][0]["interest_reason"]
    assert "求是" in landmark_response["results"][0]["interest_reason"]
    assert "银泉" in campus_life_response["results"][0]["interest_reason"]
