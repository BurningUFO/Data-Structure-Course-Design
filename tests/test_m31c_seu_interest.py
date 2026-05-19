from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_seu_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("SEU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/SEU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_SEU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "lab_building"]
    assert highlights["landmark"]["highlight_node_ids"] == ["jiulong_lake", "culture_center", "library"]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_south",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_seu_001"
    assert {"user_seu_001", "user_seu_002", "user_seu_003"} <= user_ids
    assert {"图书馆", "李文正图书馆", "九龙湖", "活动中心", "桃园", "校园生活"} <= interest_values


def test_seu_interest_recommendation_prefers_local_landmarks_and_canteens():
    service = DemoUIService("SEU")

    study_response = service.scenic_search(
        {
            "user_id": "user_seu_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    landmark_response = service.scenic_search(
        {
            "user_id": "user_seu_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_seu_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "dormitory_1",
            "limit": 10,
        }
    )

    assert study_response["success"] is True
    assert landmark_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_seu_001"
    assert landmark_response["metadata"]["user_interest_context"]["user_id"] == "user_seu_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_seu_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    landmark_top = [item["route_target_node_id"] for item in landmark_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:10]]

    assert study_top[0] == "library"
    assert "teaching_building" in study_top[:3]
    assert set(landmark_top[:2]) == {"jiulong_lake", "culture_center"}
    assert campus_life_top[0] == "canteen"
    assert "canteen_south" in campus_life_top[:10]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert landmark_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert any(token in study_response["results"][0]["interest_reason"] for token in ("李文正", "图书馆", "自习"))
    assert any(token in landmark_response["results"][0]["interest_reason"] for token in ("九龙湖", "活动中心", "摄影"))
    assert any(token in campus_life_response["results"][0]["interest_reason"] for token in ("桃园", "食堂", "校园生活"))
