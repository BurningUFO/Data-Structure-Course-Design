from __future__ import annotations

from src.ui.demo_service import DemoUIService


def test_thu_bootstrap_exposes_site_specific_interest_users():
    service = DemoUIService("THU")

    payload = service.get_bootstrap_payload()
    user_ids = {item["id"] for item in payload["users"]}
    interest_values = {item["value"] for item in payload["controls"]["interest_options"]}

    assert payload["stats"]["user_count"] >= 3
    assert payload["default_user_id"] == "user_thu_001"
    assert {"user_thu_001", "user_thu_002", "user_thu_003"} <= user_ids
    assert {"图书馆", "大礼堂", "校史", "桃李园", "食堂"} <= interest_values


def test_thu_interest_recommendation_prefers_thu_specific_landmarks_and_canteens():
    service = DemoUIService("THU")

    history_response = service.scenic_search(
        {
            "user_id": "user_thu_002",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    food_response = service.scenic_search(
        {
            "user_id": "user_thu_003",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )

    assert history_response["success"] is True
    assert food_response["success"] is True
    assert history_response["metadata"]["user_interest_context"]["user_id"] == "user_thu_002"
    assert food_response["metadata"]["user_interest_context"]["user_id"] == "user_thu_003"

    history_top = [item["route_target_node_id"] for item in history_response["results"][:4]]
    food_top = [item["route_target_node_id"] for item in food_response["results"][:5]]

    assert history_top[0] in {"auditorium", "second_gate", "qinghua_xuetang"}
    assert len({"auditorium", "second_gate", "qinghua_xuetang", "sundial"} & set(history_top)) >= 3
    assert food_top[0] == "canteen"
    assert "guanchouyuan_canteen" in food_top
    assert history_response["results"][0]["interest_match_score"] > 0
    assert food_response["results"][0]["interest_match_score"] > 0
