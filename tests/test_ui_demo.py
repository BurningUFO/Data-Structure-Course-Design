import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.ui.demo_service import DemoUIService


def test_demo_bootstrap_contains_map_and_controls():
    service = DemoUIService("PKU")
    payload = service.get_bootstrap_payload()

    assert payload["site"]["name"] == "北京大学"
    assert payload["default_start_node"] == "gate_north"
    assert payload["map"]["node_count"] >= 10
    assert payload["map"]["edge_count"] >= 10
    assert payload["stats"]["route_target_count"] >= 10
    assert any(item["value"] == "education" for item in payload["controls"]["scenic_categories"])
    print("test_demo_bootstrap_contains_map_and_controls passed.")


def test_demo_scenic_search_is_routeable():
    service = DemoUIService("PKU")
    response = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_north",
        }
    )

    assert response["success"] is True
    assert response["total"] == 1
    assert response["results"][0]["route_target_node_id"] == "library"
    assert response["results"][0]["has_map_location"] is True
    print("test_demo_scenic_search_is_routeable passed.")


def test_demo_place_search_distance_order():
    service = DemoUIService("PKU")
    response = service.place_search(
        {
            "keyword": "洗手间",
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_north",
        }
    )

    assert response["success"] is True
    distances = [
        item["distance_m"]
        for item in response["results"]
        if item.get("distance_status") == "available"
    ]
    assert distances == sorted(distances)
    print("test_demo_place_search_distance_order passed.")


def test_demo_diary_fulltext_search_links_to_route():
    service = DemoUIService("PKU")
    response = service.diary_fulltext_search({"query": "图书馆 自习", "limit": 3})

    assert response["success"] is True
    assert response["total"] >= 1
    assert response["results"][0]["route_target_node_id"]
    print("test_demo_diary_fulltext_search_links_to_route passed.")


def test_demo_route_overlay_contains_indoor_note():
    service = DemoUIService("PKU")
    response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "lib_reading_room_1",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert response["success"] is True
    assert "lib_entrance" in response["path"]
    assert response["ui"]["mappable_path_node_ids"][-1] == "library"
    assert "室内段" in response["ui"]["caption"]
    print("test_demo_route_overlay_contains_indoor_note passed.")


def run_all_tests():
    print("Running UI demo service tests...")
    test_demo_bootstrap_contains_map_and_controls()
    test_demo_scenic_search_is_routeable()
    test_demo_place_search_distance_order()
    test_demo_diary_fulltext_search_links_to_route()
    test_demo_route_overlay_contains_indoor_note()
    print("All UI demo service tests passed.")


if __name__ == "__main__":
    run_all_tests()

