from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


def test_sysu_bootstrap_exposes_site_specific_interest_profiles():
    service = DemoUIService("SYSU")

    payload = service.get_bootstrap_payload()
    outdoor = json.loads(Path("data/sites/SYSU/outdoor.json").read_text(encoding="utf-8"))
    highlights = {
        item["profile_id"]: item
        for item in outdoor["metadata"]["interest_highlights"]
    }
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert outdoor["metadata"]["interest_calibration_stage"] == "M31C_SYSU"
    assert highlights["study"]["highlight_node_ids"] == ["library", "teaching_building", "lab_building"]
    assert highlights["history"]["highlight_node_ids"] == [
        "sun_yat_sen_statue",
        "huaishi_hall",
        "yixian_lake",
    ]
    assert highlights["campus_life"]["highlight_node_ids"] == [
        "canteen",
        "canteen_east",
        "dormitory_1",
        "convenience_store",
    ]
    assert payload["stats"]["user_count"] == 3
    assert payload["default_user_id"] == "user_sysu_001"
    assert {"user_sysu_001", "user_sysu_002", "user_sysu_003"} <= user_ids
    assert {"图书馆", "第一教学楼", "怀士堂", "孙中山", "东区食堂", "校园生活"} <= interest_values


def test_sysu_interest_recommendation_prefers_local_landmarks_and_canteens():
    service = DemoUIService("SYSU")

    study_response = service.scenic_search(
        {
            "user_id": "user_sysu_001",
            "category": "education",
            "sort_field": "interest",
            "start_node_id": "gate_west",
            "limit": 5,
        }
    )
    history_response = service.scenic_search(
        {
            "user_id": "user_sysu_002",
            "category": "landmark",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 5,
        }
    )
    campus_life_response = service.scenic_search(
        {
            "user_id": "user_sysu_003",
            "category": "catering",
            "sort_field": "interest",
            "start_node_id": "gate_south",
            "limit": 10,
        }
    )

    assert study_response["success"] is True
    assert history_response["success"] is True
    assert campus_life_response["success"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_sysu_001"
    assert history_response["metadata"]["user_interest_context"]["user_id"] == "user_sysu_002"
    assert campus_life_response["metadata"]["user_interest_context"]["user_id"] == "user_sysu_003"

    study_top = [item["route_target_node_id"] for item in study_response["results"][:5]]
    history_top = [item["route_target_node_id"] for item in history_response["results"][:5]]
    campus_life_top = [item["route_target_node_id"] for item in campus_life_response["results"][:10]]

    assert study_top[:2] == ["library", "teaching_building"]
    assert history_top[0] == "sun_yat_sen_statue"
    assert "huaishi_hall" in history_top[:3]
    assert campus_life_top[0] == "canteen_east"
    assert "canteen" in campus_life_top[:3]
    assert study_response["results"][0]["interest_match_score"] > 0
    assert history_response["results"][0]["interest_match_score"] > 0
    assert campus_life_response["results"][0]["interest_match_score"] > 0
    assert any(token in study_response["results"][0]["interest_reason"] for token in ("图书馆", "自习"))
    assert any(token in history_response["results"][0]["interest_reason"] for token in ("孙中山", "校史"))
    assert any(token in campus_life_response["results"][0]["interest_reason"] for token in ("东区食堂", "食堂", "校园生活"))
