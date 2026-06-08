from __future__ import annotations

import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


THU_OUTDOOR_PATH = Path("data/sites/THU/outdoor.json")
THU_REGISTRY_PATH = Path("data/sites/THU/geo/indoor_building_registry.json")

NEW_THU_BUILDINGS = {
    "science_hall": ("road_xuetang_south", 140.01),
    "engineering_hall": ("road_second_gate", 212.09),
    "tongfang_building": ("road_second_gate", 120.42),
    "humanities_building": ("road_second_gate", 251.71),
    "architecture_building": ("road_central_axis", 345.79),
    "mechanical_engineering_building": ("road_central_axis", 187.97),
    "electrical_engineering_building": ("road_central_axis", 138.30),
    "information_science_building": ("road_central_axis", 147.97),
    "automation_building": ("road_central_axis", 174.53),
    "meng_minwei_science_building": ("road_south_gate", 374.04),
    "law_school_building": ("road_south_gate", 242.61),
    "economics_management_building": ("road_south_gate", 161.67),
    "student_activity_center": ("road_xuetang_south", 275.43),
    "zijing_apartment_2": ("road_zijing_axis", 126.48),
    "sports_center_building": ("road_zijing_axis", 286.73),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_m32d_thu_outdoor_building_nodes_reach_course_minimum():
    outdoor = load_json(THU_OUTDOOR_PATH)
    registry = load_json(THU_REGISTRY_PATH)["buildings"]
    nodes_by_id = {node["id"]: node for node in outdoor["nodes"]}
    indoor_supported = set(outdoor["metadata"]["indoor_supported_buildings"])
    registry_buildings = {item["building_id"] for item in registry}

    building_nodes = [node for node in outdoor["nodes"] if node.get("type") == "building"]

    assert len(building_nodes) >= 20
    assert set(NEW_THU_BUILDINGS) <= set(nodes_by_id)
    assert indoor_supported == registry_buildings
    assert not (set(NEW_THU_BUILDINGS) & indoor_supported)

    for building_id in NEW_THU_BUILDINGS:
        node = nodes_by_id[building_id]
        location = node["location"]

        assert node["type"] == "building"
        assert node["category"] == "building"
        assert node["source"] == "m32d_thu_building_minimum"
        assert node["needs_review"] is True
        assert node["sub_graph_id"] is None
        assert node.get("indoor_supported") is None
        assert node["tags"]
        assert node["keywords"]
        assert 39.996 < float(location["lat"]) < 40.011
        assert 116.315 < float(location["lng"]) < 116.329


def test_m32d_thu_coordinates_are_wgs84_aligned_for_leaflet_basemap():
    outdoor = load_json(THU_OUTDOOR_PATH)
    nodes_by_id = {node["id"]: node for node in outdoor["nodes"]}
    lats = [float(node["location"]["lat"]) for node in outdoor["nodes"]]
    lngs = [float(node["location"]["lng"]) for node in outdoor["nodes"]]

    assert nodes_by_id["gate_west"]["location"] == {
        "lat": 39.9967499,
        "lng": 116.3088897,
    }
    assert nodes_by_id["second_gate"]["location"] == {
        "lat": 39.9996335,
        "lng": 116.3182427,
    }
    assert nodes_by_id["library"]["location"] == {
        "lat": 40.0035771,
        "lng": 116.3182659,
    }
    assert nodes_by_id["main_building"]["location"] == {
        "lat": 40.0004203,
        "lng": 116.3263191,
    }
    assert min(lats) > 39.996
    assert max(lats) < 40.012
    assert min(lngs) > 116.308
    assert max(lngs) < 116.33


def test_m32d_thu_new_buildings_have_bidirectional_poi_access_edges():
    outdoor = load_json(THU_OUTDOOR_PATH)
    edge_by_pair = {
        (edge["from"], edge["to"]): edge
        for edge in outdoor["edges"]
    }

    for building_id, (anchor_id, expected_distance) in NEW_THU_BUILDINGS.items():
        outbound = edge_by_pair[(anchor_id, building_id)]
        inbound = edge_by_pair[(building_id, anchor_id)]

        for edge in (outbound, inbound):
            assert edge["type"] == "poi_access"
            assert edge["source"] == "m32d_thu_building_minimum"
            assert edge["vehicle_access"] == "all"
            assert edge["allowed_transports"] == ["walk", "bike"]
            assert edge["transport_semantics"] == "shared_walk_bike"
            assert edge["distance"] == expected_distance


def test_m32d_thu_buildings_are_route_targets_and_geojson_features():
    service = DemoUIService("THU")
    bootstrap = service.get_bootstrap_payload()
    geojson_payload = service.get_map_geojson_payload()
    route_target_ids = {item["id"] for item in bootstrap["route_targets"]}
    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    feature_ids = {feature["properties"]["id"] for feature in node_features}

    assert set(NEW_THU_BUILDINGS) <= route_target_ids
    assert set(NEW_THU_BUILDINGS) <= feature_ids
    assert bootstrap["map"]["node_count"] == geojson_payload["stats"]["node_feature_count"]
    assert bootstrap["map"]["edge_count"] == geojson_payload["stats"]["edge_feature_count"]
    assert bootstrap["map_capabilities"]["indoor_supported_building_count"] == 5
    assert bootstrap["stats"]["indoor_building_count"] == 5

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": "science_hall",
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )

    assert route["success"] is True
    assert route["target_node_id"] == "science_hall"
    assert route["total_distance_m"] > 0
