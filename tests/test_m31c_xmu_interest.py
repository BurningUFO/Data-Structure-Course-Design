from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_xmu_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("XMU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/XMU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_XMU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "jiageng_complex"]
    assert highlights["landmark"]["highlight_node_ids"] == ["furong_tunnel", "jiageng_complex", "furong_lake"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_nanguang",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] >= 3
    assert payload["default_user_id"] == "user_xmu_001"
    assert {"user_xmu_001", "user_xmu_002", "user_xmu_003"} <= user_ids
    assert {"图书馆", "南强", "芙蓉隧道", "文化墙", "食堂", "芙蓉"} <= interest_values


def test_xmu_interest_recommendation_prefers_xmu_specific_landmarks_and_canteens():
    service = DemoUIService("XMU")

    study_response = service.scenic_search(
        {
            "user_id": "user_xmu_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    landmark_response = service.scenic_search(
        {
            "user_id": "user_xmu_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_xmu_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert landmark_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_xmu_001"
    assert landmark_response["metadata"]["user_interest_context"]["user_id"] == "user_xmu_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_xmu_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    landmark_top = [item["route_target_node_id"] for item in landmark_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:5]]

    assert study_top[0] == "library"
    assert landmark_top[0] == "furong_tunnel"
    assert campus_life_top[0] == "canteen"
    assert "canteen_nanguang" in campus_life_top
    assert study_response["results"][0]["interest_match_score"] > 0
    assert landmark_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert "图书馆" in study_response["results"][0]["interest_reason"]
    assert "芙蓉隧道" in landmark_response["results"][0]["interest_reason"]
    assert "芙蓉" in campus_life_response["results"][0]["interest_reason"]
