import json
import os
import sys
import tempfile
import threading
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.ui.demo_service import DemoUIService
from src.ui.demo_server import build_handler


def assert_close_coordinate(left, right, tolerance=0.00035):
    assert abs(left["lat"] - right["lat"]) <= tolerance
    assert abs(left["lng"] - right["lng"]) <= tolerance


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_orthogonal_polyline(points):
    return all(
        len(start) >= 2
        and len(end) >= 2
        and (
            abs(float(start[0]) - float(end[0])) < 0.001
            or abs(float(start[1]) - float(end[1])) < 0.001
        )
        for start, end in zip(points, points[1:])
    )


def iter_geojson_positions(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Point":
        yield coordinates
    elif geometry_type in {"LineString", "MultiPoint"}:
        yield from coordinates
    elif geometry_type in {"Polygon", "MultiLineString"}:
        for part in coordinates:
            yield from part
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield from ring


CORE_PKU_POI_COUNT = 14
ENRICHED_NEW_POI_MIN = 80
ENRICHED_NEW_POI_MAX = 120


def test_demo_bootstrap_contains_map_and_controls():
    service = DemoUIService("PKU")
    payload = service.get_bootstrap_payload()

    assert payload["product"]["name"] == "智能校园导览系统"
    assert payload["product"]["stage"] == "正式产品演示版"
    assert payload["sites"][0]["id"] == "PKU"
    assert payload["sites"][0]["is_current"] is True
    site_options = {item["id"]: item for item in payload["sites"]}
    assert site_options["PKU"]["is_available"] is True
    assert site_options["PKU"]["data_status"] == "available"
    assert site_options["THU"]["is_available"] is True
    assert site_options["THU"]["data_status"] == "available"
    assert site_options["WHU"]["is_available"] is True
    assert site_options["WHU"]["data_status"] == "available"
    assert site_options["XMU"]["is_available"] is True
    assert site_options["XMU"]["data_status"] == "available"
    assert site_options["ZJU"]["is_available"] is True
    assert site_options["ZJU"]["data_status"] == "available"
    assert site_options["FDU"]["is_available"] is True
    assert site_options["FDU"]["data_status"] == "available"
    assert site_options["SJTU"]["is_available"] is True
    assert site_options["SJTU"]["data_status"] == "available"
    assert site_options["TONGJI"]["is_available"] is True
    assert site_options["TONGJI"]["data_status"] == "available"
    assert site_options["SEU"]["is_available"] is True
    assert site_options["SEU"]["data_status"] == "available"
    assert site_options["SYSU"]["is_available"] is True
    assert site_options["SYSU"]["data_status"] == "available"
    assert payload["site"]["name"] == "北京大学"
    assert payload["default_start_node"] == "gate_north"
    assert payload["map"]["node_count"] >= 1000
    assert payload["map"]["poi_node_count"] >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    assert payload["map"]["edge_count"] > 0
    assert payload["map"]["geometry_edge_count"] == payload["map"]["edge_count"]
    assert payload["map"]["osm_matched_edge_count"] > 0
    assert payload["map"]["manual_geometry_edge_count"] == payload["map"]["poi_node_count"]
    assert payload["map"]["fallback_edge_count"] == 0
    assert payload["map"]["geometry_coverage_ratio"] == 1.0
    assert payload["map"]["osm_matched_coverage_ratio"] > 0.9
    assert payload["map_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["renderers"] == ["simple_svg", "leaflet_geo"]
    assert payload["map_capabilities"]["default_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["fallback_renderer"] == "simple_svg"
    assert payload["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert payload["map_capabilities"]["osm_layers_endpoint"] == "/api/map/osm-layers"
    assert payload["map_capabilities"]["indoor_map_endpoint"] == "/api/map/indoor"
    assert payload["map_capabilities"]["indoor_navigation"] is True

    assert payload["map_capabilities"]["indoor_supported_building_count"] >= 20
    assert payload["map_capabilities"]["indoor_buildings"] == payload["indoor_buildings"]
    assert payload["map_capabilities"]["indoor_supported_buildings"] == payload["indoor_buildings"]
    assert any(item["building_id"] == "library" for item in payload["indoor_buildings"])
    assert any(item["building_id"] == "teaching_building_1" for item in payload["indoor_buildings"])
    assert any(item["building_id"] == "dormitory_1" for item in payload["indoor_buildings"])
    osm_layers = payload["map_capabilities"]["osm_layers"]
    assert [item["id"] for item in osm_layers["layers"]] == ["roads", "buildings", "water_landuse"]
    assert osm_layers["default_visible"]["roads"] is True
    assert osm_layers["default_visible"]["buildings"] is True
    assert osm_layers["default_visible"]["water_landuse"] is True
    basemaps = payload["map_capabilities"]["basemaps"]
    assert basemaps["default"] == "real_map"
    assert basemaps["fallback"] == "none"
    assert [item["id"] for item in basemaps["modes"]] == ["real_map", "none"]
    assert basemaps["modes"][0]["tile_url"] == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    assert "OpenStreetMap" in basemaps["modes"][0]["attribution"]
    assert basemaps["modes"][0]["network_required"] is True
    assert basemaps["modes"][1]["network_required"] is False
    assert payload["stats"]["route_target_count"] >= 10
    assert payload["stats"]["indoor_building_count"] >= 20
    assert payload["stats"]["site_count"] >= 1
    assert payload["stats"]["user_count"] >= 10
    assert payload["stats"]["aigc_sample_count"] == 3
    assert payload["default_user_id"] == "user_001"
    assert len(payload["users"]) >= 10
    assert payload["users"][0]["interests"]
    assert len(payload["aigc_samples"]) == 3
    assert payload["aigc_samples"][0]["sample_id"] == "aigc_sample_001"
    assert any(item["id"] == "aigc" for item in payload["navigation"])
    assert any(item["value"] == "warm_storyboard" for item in payload["controls"]["aigc_styles"])
    assert payload["state_policy"]["site_switch_supported"] is True
    assert "current_route" in payload["state_policy"]["reset_on_site_change"]
    assert payload["feedback_messages"]["site_switched"]
    assert payload["feedback_messages"]["route_unreachable"]
    assert any(item["id"] == "help" for item in payload["navigation"])
    assert any(item["id"] == "route" for item in payload["navigation"])
    assert next(item for item in payload["navigation"] if item["id"] == "diary")["status"] == "ready"
    assert payload["help"]["launch_command"] == "py -B -m src.ui.demo_server"
    assert payload["help"]["fallback_launch_command"] == "python -B -m src.ui.demo_server"
    assert payload["help"]["browser_url"] == "http://127.0.0.1:8765"
    assert payload["help"]["stage"] == "正式产品演示版 · 地图方案 B M14"
    assert len(payload["help"]["demo_flow"]) >= 3
    assert any("Leaflet / SVG" in item for item in payload["help"]["demo_flow"])
    assert any("[lng, lat]" in item for item in payload["help"]["map_acceptance"])
    assert any("真实瓦片" in item for item in payload["help"]["map_acceptance"])
    assert any("M14 只沿本地 OSM 白线道路相邻节点" in item for item in payload["help"]["map_acceptance"])
    assert any(item["value"] == "education" for item in payload["controls"]["scenic_categories"])
    assert any(item["value"] == "building" for item in payload["controls"]["scenic_categories"])
    assert any(item["value"] == "building_entrance" for item in payload["controls"]["scenic_categories"])
    assert any(item["value"] == "building_entrance" for item in payload["controls"]["place_categories"])
    assert any(item["value"] == "interest" for item in payload["controls"]["scenic_sort_options"])
    assert any(item["value"] == "interest" for item in payload["controls"]["diary_sort_options"])
    assert any(item["value"] == "图书馆" for item in payload["controls"]["interest_options"])
    assert [item["value"] for item in payload["controls"]["nearby_radius_options"]] == [200, 500, 800, 1200]
    assert [item["value"] for item in payload["controls"]["transport_modes"]] == ["walk", "bike", "mixed"]
    assert [item["label"] for item in payload["controls"]["transport_modes"]] == [
        "步行",
        "自行车",
        "步行 + 自行车最短时间",
    ]
    library_target = next(item for item in payload["route_targets"] if item["id"] == "library")
    room_target = next(item for item in payload["route_targets"] if item["id"] == "lib_reading_room_1")
    dorm_target = next(item for item in payload["route_targets"] if item["id"] == "dorm1_room_101")
    assert library_target["indoor_supported"] is True
    assert library_target["indoor_graph_id"] == "indoor_LIB"
    assert library_target["indoor_entry_node_id"] == "library"
    assert library_target["building_id"] == "library"
    assert library_target["building_name"] == "图书馆"
    assert room_target["building_id"] == "library"
    assert room_target["building_name"] == "图书馆"
    assert room_target["floor_id"] == "F1"
    assert room_target["floor_label"] == "1F"
    assert room_target["source_sub_graph_id"] == "indoor_LIB"
    assert room_target["layout"]["x"] == 132
    assert room_target["layout"]["y"] == 320
    assert dorm_target["building_id"] == "dormitory_1"
    assert dorm_target["floor_id"] == "F1"
    print("test_demo_bootstrap_contains_map_and_controls passed.")


def test_m27x_thu_outdoor_main_chain_is_available_in_first_batch():
    service = DemoUIService("THU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/THU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "THU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M27X"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "first_5_outdoor"
    assert outdoor["metadata"]["ready_for_first_batch_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "THU"
    assert payload["site"]["name"] == "清华大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["THU"]["is_available"] is True
    assert site_options["THU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 10
    assert payload["stats"]["route_target_count"] >= 10
    assert payload["map"]["node_count"] >= 20
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] == "restroom_main"
    assert place["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "THU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "THU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m27x_thu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("THU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "THU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["THU"]["is_available"] is True
    assert site_options["THU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "THU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 116.2 < lng < 116.5
    assert 39.9 < lat < 40.1

    repo_root = os.path.join(os.path.dirname(__file__), "..")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert "isSiteFrontendSelectable" in script
    assert 'site.data_status === "backend_ready"' in script
    assert "试点可演示" in script
    assert "filterRoutePresetsForCurrentSite" in script
    assert "filterMultiRoutePresetsForCurrentSite" in script
    assert "defaultRouteTargetId" in script
    assert "resolveDemoRouteScenario" in script
    assert "currentSiteId() === siteId" in script
    assert "state.mapGeoJsonLoading === loading" in script
    assert "state.osmLayersLoading === loading" in script


def test_m27x_whu_outdoor_main_chain_is_available_in_first_batch():
    service = DemoUIService("WHU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/WHU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "WHU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M27X"
    assert outdoor["metadata"]["site_id"] == "WHU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "first_5_outdoor"
    assert outdoor["metadata"]["ready_for_first_batch_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "WHU"
    assert payload["site"]["name"] == "武汉大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["WHU"]["is_available"] is True
    assert site_options["WHU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 15
    assert payload["stats"]["route_target_count"] >= 15
    assert payload["map"]["node_count"] >= 25
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] == "restroom_main"
    assert place["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "桂园食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "WHU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "WHU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m27x_whu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("WHU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "WHU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["WHU"]["is_available"] is True
    assert site_options["WHU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "WHU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 114.34 < lng < 114.38
    assert 30.52 < lat < 30.56


def test_m27x_xmu_outdoor_main_chain_is_available_in_first_batch():
    service = DemoUIService("XMU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/XMU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "XMU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M27X"
    assert outdoor["metadata"]["site_id"] == "XMU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "first_5_outdoor"
    assert outdoor["metadata"]["ready_for_first_batch_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "XMU"
    assert payload["site"]["name"] == "厦门大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["XMU"]["is_available"] is True
    assert site_options["XMU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] == "restroom_main"
    assert place["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "XMU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "XMU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m27x_xmu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("XMU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "XMU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["XMU"]["is_available"] is True
    assert site_options["XMU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "XMU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 118.08 < lng < 118.11
    assert 24.43 < lat < 24.45


def test_m27x_zju_outdoor_main_chain_is_available_in_first_batch():
    service = DemoUIService("ZJU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/ZJU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "ZJU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M27X"
    assert outdoor["metadata"]["site_id"] == "ZJU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "first_5_outdoor"
    assert outdoor["metadata"]["ready_for_first_batch_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "ZJU"
    assert payload["site"]["name"] == "浙江大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["ZJU"]["is_available"] is True
    assert site_options["ZJU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_south",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] == "restroom_main"
    assert place["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "临湖餐厅",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "ZJU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "ZJU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m27x_zju_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("ZJU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "ZJU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["ZJU"]["is_available"] is True
    assert site_options["ZJU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "ZJU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 120.07 < lng < 120.10
    assert 30.30 < lat < 30.32


def test_m27x_nju_outdoor_main_chain_is_available_in_first_batch():
    service = DemoUIService("NJU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/NJU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "NJU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M27X"
    assert outdoor["metadata"]["site_id"] == "NJU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "first_5_outdoor"
    assert outdoor["metadata"]["ready_for_first_batch_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "NJU"
    assert payload["site"]["name"] == "南京大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["NJU"]["is_available"] is True
    assert site_options["NJU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] == "restroom_main"
    assert place["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "九食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "NJU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "NJU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m27x_nju_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("NJU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "NJU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["NJU"]["is_available"] is True
    assert site_options["NJU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "NJU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 118.94 < lng < 118.98
    assert 32.10 < lat < 32.14


def test_m28x_fdu_outdoor_main_chain_is_available_in_remaining_batch():
    service = DemoUIService("FDU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/FDU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "FDU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M28X"
    assert outdoor["metadata"]["site_id"] == "FDU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "remaining_15_outdoor"
    assert outdoor["metadata"]["ready_for_m28_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "FDU"
    assert payload["site"]["name"] == "复旦大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["FDU"]["is_available"] is True
    assert site_options["FDU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] in {"restroom_main", "restroom_library"}
    assert place["results"][0]["distance_status"] == "available"

    shopping = service.place_search(
        {
            "keyword": "便利",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert shopping["success"] is True
    assert shopping["results"][0]["route_target_node_id"] == "convenience_store"
    assert shopping["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "FDU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "FDU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m28x_fdu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("FDU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "FDU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["FDU"]["is_available"] is True
    assert site_options["FDU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "FDU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0
    assert geojson_payload["stats"]["geometry_edge_count"] == 0
    assert geojson_payload["stats"]["fallback_edge_count"] == geojson_payload["stats"]["edge_feature_count"]

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 121.49 < lng < 121.51
    assert 31.29 < lat < 31.31


def test_m28x_sjtu_outdoor_main_chain_is_available_in_remaining_batch():
    service = DemoUIService("SJTU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/SJTU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "SJTU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M28X"
    assert outdoor["metadata"]["site_id"] == "SJTU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "remaining_15_outdoor"
    assert outdoor["metadata"]["ready_for_m28_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "SJTU"
    assert payload["site"]["name"] == "上海交通大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["SJTU"]["is_available"] is True
    assert site_options["SJTU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] in {"restroom_main", "restroom_teaching"}
    assert place["results"][0]["distance_status"] == "available"

    shopping = service.place_search(
        {
            "keyword": "便利",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert shopping["success"] is True
    assert shopping["results"][0]["route_target_node_id"] == "convenience_store"
    assert shopping["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "SJTU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "SJTU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m28x_sjtu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("SJTU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "SJTU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["SJTU"]["is_available"] is True
    assert site_options["SJTU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "SJTU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0
    assert geojson_payload["stats"]["geometry_edge_count"] == 0
    assert geojson_payload["stats"]["fallback_edge_count"] == geojson_payload["stats"]["edge_feature_count"]

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 121.42 < lng < 121.45
    assert 31.01 < lat < 31.04


def test_m28x_tongji_outdoor_main_chain_is_available_in_remaining_batch():
    service = DemoUIService("TONGJI")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/TONGJI/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "TONGJI"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M28X"
    assert outdoor["metadata"]["site_id"] == "TONGJI"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "remaining_15_outdoor"
    assert outdoor["metadata"]["ready_for_m28_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "TONGJI"
    assert payload["site"]["name"] == "同济大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["TONGJI"]["is_available"] is True
    assert site_options["TONGJI"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] in {"restroom_main", "restroom_teaching"}
    assert place["results"][0]["distance_status"] == "available"

    shopping = service.place_search(
        {
            "keyword": "便利",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert shopping["success"] is True
    assert shopping["results"][0]["route_target_node_id"] == "convenience_store"
    assert shopping["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "TONGJI"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "TONGJI"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m28x_tongji_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("TONGJI")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "TONGJI"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["TONGJI"]["is_available"] is True
    assert site_options["TONGJI"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "TONGJI"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0
    assert geojson_payload["stats"]["geometry_edge_count"] == 0
    assert geojson_payload["stats"]["fallback_edge_count"] == geojson_payload["stats"]["edge_feature_count"]

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 121.49 < lng < 121.51
    assert 31.27 < lat < 31.29


def test_m28x_seu_outdoor_main_chain_is_available_in_remaining_batch():
    service = DemoUIService("SEU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/SEU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "SEU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M28X"
    assert outdoor["metadata"]["site_id"] == "SEU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "remaining_15_outdoor"
    assert outdoor["metadata"]["ready_for_m28_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "SEU"
    assert payload["site"]["name"] == "东南大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["SEU"]["is_available"] is True
    assert site_options["SEU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] in {"restroom_main", "restroom_teaching"}
    assert place["results"][0]["distance_status"] == "available"

    shopping = service.place_search(
        {
            "keyword": "便利",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert shopping["success"] is True
    assert shopping["results"][0]["route_target_node_id"] == "convenience_store"
    assert shopping["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "SEU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "SEU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m28x_seu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("SEU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "SEU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["SEU"]["is_available"] is True
    assert site_options["SEU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "SEU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0
    assert geojson_payload["stats"]["geometry_edge_count"] == 0
    assert geojson_payload["stats"]["fallback_edge_count"] == geojson_payload["stats"]["edge_feature_count"]

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 118.81 < lng < 118.83
    assert 31.88 < lat < 31.90


def test_m28x_sysu_outdoor_main_chain_is_available_in_remaining_batch():
    service = DemoUIService("SYSU")
    payload = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in payload["sites"]}
    outdoor = json.loads(Path("data/sites/SYSU/outdoor.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    categories = {node["category"] for node in outdoor["nodes"]}

    assert getattr(service.graph, "site_id", "") == "SYSU"
    assert {"gate_west", "library", "canteen"} <= set(service.graph.nodes)
    assert outdoor["metadata"]["stage"] == "M28X"
    assert outdoor["metadata"]["site_id"] == "SYSU"
    assert outdoor["metadata"]["scaffold"] is False
    assert outdoor["metadata"]["batch"] == "remaining_15_outdoor"
    assert outdoor["metadata"]["ready_for_m28_regression"] is True
    assert {
        "gate_west",
        "gate_south",
        "gate_east",
        "gate_north",
        "library",
        "teaching_building",
        "dormitory_1",
        "canteen",
        "service_center",
        "restroom_main",
    } <= node_ids
    assert {
        "entrance",
        "education",
        "dormitory",
        "catering",
        "service",
        "shopping",
        "restroom",
    } <= categories
    assert payload["site"]["id"] == "SYSU"
    assert payload["site"]["name"] == "中山大学"
    assert payload["site"]["is_available"] is True
    assert payload["site"]["data_status"] == "available"
    assert site_options["SYSU"]["is_available"] is True
    assert site_options["SYSU"]["data_status"] == "available"
    assert payload["default_start_node"] == "gate_north"
    assert payload["stats"]["record_count"] >= 20
    assert payload["stats"]["route_target_count"] >= 20
    assert payload["map"]["node_count"] >= 30
    assert payload["map"]["edge_count"] > 0
    assert "library" in {item["id"] for item in payload["route_targets"]}
    assert "canteen" in {item["id"] for item in payload["route_targets"]}

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert scenic["success"] is True
    assert scenic["results"][0]["route_target_node_id"] == "library"
    assert scenic["results"][0]["distance_status"] == "available"

    place = service.place_search(
        {
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert place["success"] is True
    assert place["results"][0]["route_target_node_id"] in {"restroom_main", "restroom_teaching"}
    assert place["results"][0]["distance_status"] == "available"

    shopping = service.place_search(
        {
            "keyword": "便利",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert shopping["success"] is True
    assert shopping["results"][0]["route_target_node_id"] == "convenience_store"
    assert shopping["results"][0]["distance_status"] == "available"

    catering = service.catering_search(
        {
            "keyword": "食堂",
            "sort_field": "distance_m",
            "start_node_id": "gate_west",
            "limit": 3,
        }
    )
    assert catering["success"] is True
    assert catering["results"][0]["route_target_node_id"] == "canteen"
    assert catering["results"][0]["distance_status"] == "available"

    route = service.plan_route(
        {
            "start_node_id": "gate_west",
            "target_node_id": scenic["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )
    assert route["success"] is True
    assert route["site_id"] == "SYSU"
    assert route["target_node_id"] == "library"
    assert route["total_distance_m"] > 0

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_west",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )
    assert multi_route["success"] is True
    assert multi_route["site_id"] == "SYSU"
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["target_node_ids"] == ["library", "canteen"]


def test_m28x_sysu_frontend_switch_contract_and_leaflet_data():
    service = DemoUIService("SYSU")
    bootstrap = service.get_bootstrap_payload()
    site_options = {item["id"]: item for item in bootstrap["sites"]}
    geojson_payload = service.get_map_geojson_payload()

    assert bootstrap["site"]["id"] == "SYSU"
    assert bootstrap["site"]["is_available"] is True
    assert bootstrap["site"]["data_status"] == "available"
    assert site_options["SYSU"]["is_available"] is True
    assert site_options["SYSU"]["data_status"] == "available"
    assert bootstrap["map_renderer"] == "leaflet_geo"
    assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert geojson_payload["success"] is True
    assert geojson_payload["site_id"] == "SYSU"
    assert geojson_payload["stats"]["node_feature_count"] == bootstrap["map"]["node_count"]
    assert geojson_payload["stats"]["edge_feature_count"] == bootstrap["map"]["edge_count"]
    assert geojson_payload["stats"]["feature_count"] > 0
    assert geojson_payload["stats"]["geometry_edge_count"] == 0
    assert geojson_payload["stats"]["fallback_edge_count"] == geojson_payload["stats"]["edge_feature_count"]

    node_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node"
    ]
    edge_features = [
        feature
        for feature in geojson_payload["geojson"]["features"]
        if feature["properties"]["kind"] == "edge"
    ]
    assert {feature["properties"]["id"] for feature in node_features} >= {"gate_north", "library", "canteen"}
    assert edge_features
    lng, lat = node_features[0]["geometry"]["coordinates"]
    assert 113.28 < lng < 113.31
    assert 23.09 < lat < 23.11


def test_demo_osm_edge_matches_file_records_m14_white_road_edges():
    service = DemoUIService("PKU")
    match_path = Path("data/sites/PKU/geo/edge_osm_geometry_matches.json")
    loaded = json.loads(match_path.read_text(encoding="utf-8"))

    assert loaded["metadata"]["stage"] == "M14_white_road_adjacent_edges"
    assert loaded["metadata"]["source_file"] == "osm_roads_simplified.geojson"
    assert loaded["metadata"]["runtime_policy"]["routing_authority"] == "course_graph"
    coverage = loaded["metadata"]["coverage_statistics"]
    assert coverage["white_road_edge_count"] > 0
    assert coverage["poi_access_edge_count"] >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    assert coverage["fallback_edge_count"] == 0
    assert coverage["geometry_coverage_ratio"] == 1.0
    assert service.osm_edge_match_warnings == []
    assert len(service.osm_edge_matches) == len(loaded["matches"])
    assert loaded["matches"]
    assert service.map_edges
    white_match = next(
        item for item in loaded["matches"]
        if item["geometry_source"] == "osm_matched"
    )
    assert white_match["white_road_source"] == "adjacent_osm_linestring_slice"
    assert white_match["source_osm_id"]
    assert len(white_match["geometry"]) >= 2
    access_match = next(
        item for item in loaded["matches"]
        if item["geometry_source"] == "manual"
    )
    assert access_match["white_road_source"] == "poi_access_projection"
    print("test_demo_osm_edge_matches_file_records_m14_white_road_edges passed.")


def test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order():
    service = DemoUIService("PKU")
    payload = service.get_map_geojson_payload()

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert payload["geojson"]["type"] == "FeatureCollection"
    assert payload["stats"]["node_feature_count"] > 0
    assert payload["stats"]["edge_feature_count"] > 0
    assert payload["stats"]["geometry_edge_count"] == payload["stats"]["edge_feature_count"]
    assert payload["stats"]["osm_matched_edge_count"] > 0
    assert payload["stats"]["manual_geometry_edge_count"] == payload["stats"]["poi_node_count"]
    assert payload["stats"]["fallback_edge_count"] == 0
    assert (
        payload["stats"]["geometry_edge_count"]
        + payload["stats"]["fallback_edge_count"]
        == payload["stats"]["edge_feature_count"]
    )
    assert payload["stats"]["geometry_coverage_ratio"] == 1.0

    features = payload["geojson"]["features"]
    node_features = [item for item in features if item["properties"]["kind"] == "node"]
    edge_features = [item for item in features if item["properties"]["kind"] == "edge"]
    assert len(node_features) == payload["stats"]["node_feature_count"]
    assert len(edge_features) == payload["stats"]["edge_feature_count"]
    assert edge_features
    first_edge = edge_features[0]
    assert first_edge["geometry"]["type"] == "LineString"
    assert len(first_edge["geometry"]["coordinates"]) >= 2
    assert first_edge["properties"]["kind"] == "edge"
    assert first_edge["properties"]["geometry_source"] in {"osm_matched", "manual"}
    assert first_edge["properties"]["is_fallback_geometry"] is False
    assert "source_osm_id" in first_edge["properties"]
    assert "source_highway" in first_edge["properties"]
    assert all(edge["properties"].get("source_osm_id") for edge in edge_features)
    assert all(edge["properties"].get("source_highway") for edge in edge_features)
    for lng, lat in first_edge["geometry"]["coordinates"]:
        assert is_number(lng)
        assert is_number(lat)
        assert 115.0 < lng < 117.5
        assert 39.0 < lat < 41.0

    node_index = {node["id"]: node for node in service.map_nodes}
    first_node = node_features[0]
    first_node_id = first_node["properties"]["id"]
    assert first_node["geometry"]["type"] == "Point"
    assert first_node["geometry"]["coordinates"] == [
        node_index[first_node_id]["lng"],
        node_index[first_node_id]["lat"],
    ]
    assert {
        "kind",
        "id",
        "name",
        "category",
        "category_label",
        "display_role",
        "is_waypoint",
        "label_priority",
        "show_label",
        "is_searchable",
    } <= set(first_node["properties"])

    waypoint_nodes = [node for node in node_features if node["properties"]["is_waypoint"]]
    poi_nodes = [node for node in node_features if not node["properties"]["is_waypoint"]]
    assert waypoint_nodes
    assert poi_nodes
    assert all(node["properties"]["display_role"] == "waypoint" for node in waypoint_nodes)
    assert all(node["properties"]["show_label"] is False for node in waypoint_nodes)
    assert all(node["properties"]["is_searchable"] is False for node in waypoint_nodes)
    assert all(node["properties"]["label_priority"] <= 10 for node in waypoint_nodes)
    assert all(node["properties"]["display_role"] == "poi" for node in poi_nodes)
    assert all(node["properties"]["show_label"] is True for node in poi_nodes)
    assert not any("campus_service" in node["properties"]["id"] for node in node_features)
    assert not any("?" in node["properties"]["name"] for node in node_features)
    access_nodes = [
        node for node in node_features
        if node["properties"].get("network_role") == "poi_access"
    ]
    assert len(access_nodes) == len(poi_nodes)
    gate_access = next(
        node for node in access_nodes
        if node["properties"]["id"] == "road_access_gate_north"
    )
    assert gate_access["properties"]["anchor_for"] == "gate_north"
    assert gate_access["properties"]["projection_distance_m"] <= 80
    gate_poi = next(node for node in poi_nodes if node["properties"]["id"] == "gate_north")
    assert gate_poi["properties"]["route_anchor_node_id"] == "road_access_gate_north"
    print("test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order passed.")


def test_demo_map_geojson_reports_geometry_coverage_stats():
    service = DemoUIService("PKU")
    payload = service.get_map_geojson_payload()
    stats = payload["stats"]

    osm_matched_edge_count = sum(1 for edge in service.map_edges if edge.get("geometry_source") == "osm_matched")
    manual_geometry_edge_count = sum(1 for edge in service.map_edges if edge.get("geometry_source") == "manual")
    geometry_edge_count = osm_matched_edge_count + manual_geometry_edge_count
    fallback_edge_count = len(service.map_edges) - geometry_edge_count

    assert stats["edge_feature_count"] == len(service.map_edges)
    assert stats["poi_node_count"] == sum(1 for node in service.map_nodes if not node["is_waypoint"])
    assert stats["waypoint_node_count"] == sum(1 for node in service.map_nodes if node["is_waypoint"])
    assert stats["poi_node_count"] >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    assert stats["waypoint_node_count"] >= 600
    assert stats["node_feature_count"] == len(service.map_nodes)
    assert stats["edge_feature_count"] == len(service.map_edges) > 0
    assert stats["geometry_edge_count"] == geometry_edge_count
    assert stats["osm_matched_edge_count"] == osm_matched_edge_count
    assert stats["manual_geometry_edge_count"] == manual_geometry_edge_count
    assert stats["fallback_edge_count"] == fallback_edge_count
    assert stats["osm_matched_edge_count"] > 0
    assert stats["manual_geometry_edge_count"] == stats["poi_node_count"]
    assert stats["geometry_edge_count"] == stats["edge_feature_count"]
    assert stats["fallback_edge_count"] == 0
    assert stats["geometry_coverage_ratio"] == 1.0
    assert stats["osm_matched_coverage_ratio"] > 0.9

    bootstrap_map = service.get_bootstrap_payload()["map"]
    assert bootstrap_map["poi_node_count"] == stats["poi_node_count"]
    assert bootstrap_map["waypoint_node_count"] == stats["waypoint_node_count"]
    assert bootstrap_map["geometry_edge_count"] == stats["geometry_edge_count"]
    assert bootstrap_map["osm_matched_edge_count"] == stats["osm_matched_edge_count"]
    assert bootstrap_map["manual_geometry_edge_count"] == stats["manual_geometry_edge_count"]
    assert bootstrap_map["fallback_edge_count"] == stats["fallback_edge_count"]
    assert bootstrap_map["geometry_coverage_ratio"] == stats["geometry_coverage_ratio"]
    assert bootstrap_map["osm_matched_coverage_ratio"] == stats["osm_matched_coverage_ratio"]
    print("test_demo_map_geojson_reports_geometry_coverage_stats passed.")


def test_demo_white_road_skeleton_audit_matches_m14_edges():
    audit_path = Path("data/sites/PKU/geo/white_road_skeleton_audit.json")
    outdoor_path = Path("data/sites/PKU/outdoor.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    outdoor = json.loads(outdoor_path.read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in outdoor["nodes"]}
    access_node_ids = {
        node["id"]
        for node in outdoor["nodes"]
        if node.get("network_role") == "poi_access"
    }
    poi_nodes = [node for node in outdoor["nodes"] if node.get("category") != "road"]

    assert audit["metadata"]["stage"] == "M14_white_road_adjacent_edges"
    assert audit["metadata"]["stage_boundary"] == "white_road_adjacent_edges_only"
    assert audit["summary"]["input_outdoor_node_count"] >= audit["summary"]["poi_node_count"]
    assert audit["summary"]["old_road_node_count_removed"] >= 0
    assert audit["summary"]["poi_node_count"] >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    assert audit["summary"]["generated_node_count_total"] == len(outdoor["nodes"])
    m14_edges = [
        edge for edge in outdoor["edges"]
        if edge.get("source") != "m21_transport_demo"
    ]
    m21_edges = [
        edge for edge in outdoor["edges"]
        if edge.get("source") == "m21_transport_demo"
    ]
    assert audit["summary"]["outdoor_edge_count"] == len(m14_edges) > 0
    assert len(m21_edges) == 8
    assert audit["summary"]["white_road_edge_count"] > 0
    assert audit["summary"]["poi_access_edge_count"] == len(access_node_ids) * 2
    assert audit["summary"]["geometry_edge_count"] == audit["summary"]["outdoor_edge_count"]
    assert audit["summary"]["fallback_edge_count"] == 0
    assert audit["summary"]["geometry_coverage_ratio"] == 1.0
    assert audit["summary"]["match_count"] > 0
    assert audit["summary"]["poi_projection_needs_review_count"] == 0
    assert audit["summary"]["generated_white_road_node_count"] == sum(
        audit["generated_role_counts"][role]
        for role in ("junction", "bend", "endpoint")
    )
    assert audit["summary"]["generated_access_node_count"] == len(access_node_ids)
    assert audit["generated_role_counts"]["junction"] >= 200
    assert audit["generated_role_counts"]["bend"] >= 100
    assert audit["generated_role_counts"]["endpoint"] >= 250
    assert audit["generated_role_counts"]["poi_access"] == len(access_node_ids)
    assert audit["checks"]["old_road_nodes_removed"] is True
    assert audit["checks"]["outdoor_edges_have_geometry"] is True
    assert audit["checks"]["matches_record_edges"] is True
    assert audit["checks"]["all_pois_have_route_anchor"] is True
    assert audit["review"]["checks"]["all_poi_projection_distances_within_review_threshold"] is True
    assert audit["review"]["checks"]["access_node_count_is_expected"] is True
    assert audit["checks"]["m13b_review_passed"] is True
    assert audit["checks"]["white_road_edges_exist"] is True
    assert audit["checks"]["poi_access_edges_exist"] is True
    assert audit["edge_construction"]["undirected_white_road_edge_count"] > 0
    assert audit["edge_construction"]["excluded_candidate_count"] == 0
    assert audit["review"]["status"] == "reviewed_pass"
    assert audit["review"]["density"]["bbox_area_km2"] > 0
    assert audit["review"]["density"]["nodes_per_km2"] > 0
    assert (
        audit["review"]["near_duplicate_review"]["threshold_m"]
        == audit["rules"]["dedup_tolerance_m"]
    )
    assert audit["review"]["near_duplicate_review"]["pair_count"] == 0
    assert (
        audit["review"]["poi_projection_review"]["max_distance_m"]
        <= audit["rules"]["access_review_distance_m"]
    )
    assert audit["review"]["poi_projection_review"]["needs_review_count"] == 0
    assert all(audit["review"]["checks"].values())
    assert len(poi_nodes) == audit["summary"]["poi_node_count"]
    for poi in poi_nodes:
        assert poi["route_anchor_node_id"] in access_node_ids
    assert len(audit["poi_projections"]) == len(poi_nodes)
    for projection in audit["poi_projections"]:
        assert projection["anchor_node_id"] in node_ids
        assert projection["anchor_node_id"] in access_node_ids
        assert projection["needs_review"] is False
        assert projection["projection_distance_m"] <= audit["rules"]["access_review_distance_m"]
    for edge in outdoor["edges"]:
        if edge.get("source") == "m21_transport_demo":
            assert edge["type"] == "bike_lane"
            assert edge.get("allowed_transports") == ["bike"]
            continue
        assert edge["type"] in {"white_road", "poi_access"}
        assert edge["geometry"]
        for point in edge["geometry"]:
            assert set(point) == {"lat", "lng"}
    print("test_demo_white_road_skeleton_audit_matches_m14_edges passed.")


def test_demo_osm_layers_payload_contains_local_feature_collections_and_stats():
    service = DemoUIService("PKU")
    payload = service.get_osm_layers_payload()

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert set(payload["layers"]) == {"roads", "buildings", "water_landuse"}
    assert payload["metadata"]["data_status"] == "formal_osm_overpass_extract"
    assert payload["metadata"]["runtime_policy"]["web_ui_calls_overpass"] is False
    assert payload["metadata"]["runtime_policy"]["web_ui_calls_osmnx"] is False
    assert "OpenStreetMap" in payload["metadata"]["source"]["name"]
    assert "ODbL" in payload["metadata"]["license"]["name"]

    for layer_id, geojson in payload["layers"].items():
        assert geojson["type"] == "FeatureCollection"
        assert isinstance(geojson["features"], list)
        assert payload["stats"]["layers"][layer_id]["feature_count"] == len(geojson["features"])
        assert len(geojson["features"]) > 0

    assert payload["stats"]["roads_feature_count"] == len(payload["layers"]["roads"]["features"])
    assert payload["stats"]["buildings_feature_count"] == len(payload["layers"]["buildings"]["features"])
    assert payload["stats"]["water_landuse_feature_count"] == len(payload["layers"]["water_landuse"]["features"])
    assert payload["stats"]["feature_count"] == (
        payload["stats"]["roads_feature_count"]
        + payload["stats"]["buildings_feature_count"]
        + payload["stats"]["water_landuse_feature_count"]
    )
    assert payload["stats"]["missing_file_count"] == 0
    print("test_demo_osm_layers_payload_contains_local_feature_collections_and_stats passed.")


def test_demo_osm_layers_geojson_uses_lng_lat_coordinate_order():
    service = DemoUIService("PKU")
    payload = service.get_osm_layers_payload()

    for layer in payload["layers"].values():
        for feature in layer["features"]:
            positions = list(iter_geojson_positions(feature["geometry"]))
            assert positions
            for lng, lat in positions:
                assert is_number(lng)
                assert is_number(lat)
                assert 115.0 < lng < 117.5
                assert 39.0 < lat < 41.0
    print("test_demo_osm_layers_geojson_uses_lng_lat_coordinate_order passed.")


def test_demo_osm_layers_missing_file_keeps_core_map_available():
    service = DemoUIService("PKU")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roads_path = temp_path / "osm_roads_simplified.geojson"
        roads_path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[116.3055, 39.9929], [116.307, 39.9915]],
                            },
                            "properties": {"kind": "osm", "layer": "roads"},
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (temp_path / "osm_extract_metadata.json").write_text(
            json.dumps({"site_id": "PKU", "data_status": "test_partial"}, ensure_ascii=False),
            encoding="utf-8",
        )
        service._osm_geo_dir = lambda: temp_path

        payload = service.get_osm_layers_payload()

    assert payload["success"] is True
    assert payload["layers"]["roads"]["type"] == "FeatureCollection"
    assert payload["stats"]["roads_feature_count"] == 1
    assert payload["stats"]["buildings_feature_count"] == 0
    assert payload["stats"]["water_landuse_feature_count"] == 0
    assert payload["stats"]["missing_file_count"] == 2
    assert "osm_buildings.geojson" in payload["stats"]["missing_files"]
    assert "osm_water_landuse.geojson" in payload["stats"]["missing_files"]

    map_payload = service.get_map_geojson_payload()
    route_payload = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "library",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert map_payload["success"] is True
    assert route_payload["success"] is True
    assert route_payload["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    print("test_demo_osm_layers_missing_file_keeps_core_map_available passed.")


def test_demo_server_osm_layers_endpoint_returns_payload():
    service = DemoUIService("PKU")
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/map/osm-layers?site_id=PKU",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert payload["layers"]["roads"]["type"] == "FeatureCollection"
    assert payload["stats"]["roads_feature_count"] > 0
    print("test_demo_server_osm_layers_endpoint_returns_payload passed.")


def test_demo_indoor_map_payload_contains_floor_nodes_and_zone_metadata():
    service = DemoUIService("PKU")
    payload = service.get_indoor_map_payload("library", "F1")

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert payload["building_id"] == "library"
    assert payload["building_name"] == "图书馆"
    assert payload["entry_node_id"] == "library"
    assert payload["indoor_graph_id"] == "indoor_LIB"
    assert payload["template_id"] == "library_service_v1"
    assert payload["template_name"]
    assert payload["current_floor"]["id"] == "F1"
    assert payload["current_floor"]["label"] == "1F"
    assert payload["current_floor_id"] == "F1"
    assert payload["stats"]["floor_count"] == 3
    assert payload["stats"]["node_count"] == len(payload["nodes"])
    assert payload["stats"]["edge_count"] == len(payload["edges"])
    assert payload["stats"]["zone_count"] == len(payload["zones"])
    assert all("id" in item and "label" in item for item in payload["available_floors"])
    assert payload["floorplan"]["renderer"] == "svg_floorplan"
    assert payload["floorplan"]["version"] == "m20_realistic_floorplan_v1"
    assert payload["floorplan"]["stats"]["room_count"] >= 6
    assert payload["floorplan"]["stats"]["corridor_count"] >= 6
    assert payload["floorplan"]["stats"]["wall_count"] > payload["floorplan"]["stats"]["room_count"]
    assert payload["floorplan"]["stats"]["door_count"] >= 6
    assert payload["floorplan"]["stats"]["icon_count"] >= 4
    assert payload["floorplan"]["route_overlay"]["aligns_to"] == "corridors.path"

    entrance = next(item for item in payload["nodes"] if item["id"] == "lib_entrance")
    reading_room = next(item for item in payload["nodes"] if item["id"] == "lib_reading_room_1")
    route_edge = next(
        item
        for item in payload["edges"]
        if item["from"] == "lib_entrance" and item["to"] == "lib_reading_room_1"
    )

    assert entrance["is_gate"] is True
    assert is_number(entrance["layout"]["x"])
    assert is_number(entrance["layout"]["y"])
    assert entrance["zone_type"] == "lobby"
    assert entrance["zone_shape"] == "polygon"
    assert entrance["icon_type"] == "lobby"
    assert len(entrance["polygon"]) >= 4
    assert reading_room["floor_id"] == "F1"
    assert reading_room["floor_label"] == "1F"
    assert reading_room["description"]
    assert reading_room["facilities"]
    assert reading_room["zone_type"] == "reading_room"
    assert reading_room["zone_shape"] == "polygon"
    assert len(reading_room["door_positions"]) >= 1
    assert route_edge["from_floor_id"] == "F1"
    assert route_edge["to_floor_id"] == "F1"
    assert route_edge["is_cross_floor_transition"] is False
    icon_types = {item["type"] for item in payload["floorplan"]["icons"]}
    assert {"restroom", "elevator", "stairs", "lobby"} <= icon_types
    zone_ids = {item["id"] for item in payload["zones"]}
    assert "lib_reading_room_1" in zone_ids
    assert "lib_staircase" not in zone_ids

    second_floor = service.get_indoor_map_payload("library", "F2")
    assert second_floor["success"] is True
    second_floor_node_ids = {item["id"] for item in second_floor["nodes"]}
    assert "lib_reading_room_2" in second_floor_node_ids
    assert "lib_reading_room_1" not in second_floor_node_ids

    invalid_floor = service.get_indoor_map_payload("library", "B9")
    assert invalid_floor["success"] is False
    print("test_demo_indoor_map_payload_contains_floor_nodes_and_zone_metadata passed.")


def test_demo_m20_indoor_floorplan_covers_realistic_scene_types():
    service = DemoUIService("PKU")
    scenarios = [
        ("library", "F1", {"lobby", "reading_room", "restroom", "elevator", "stairs"}),
        ("teaching_building_1", "F1", {"lobby", "education", "restroom", "elevator", "stairs"}),
        ("dormitory_1", "F1", {"lobby", "dormitory", "restroom", "elevator", "stairs"}),
        ("poi_osm_catering_way_444894329", "F1", {"lobby", "catering", "restroom", "elevator", "stairs"}),
    ]

    for building_id, floor_id, required_zone_types in scenarios:
        payload = service.get_indoor_map_payload(building_id, floor_id)
        floorplan = payload["floorplan"]
        zone_types = {room["zone_type"] for room in floorplan["rooms"]}
        corridor_segments = floorplan["corridors"]

        assert payload["success"] is True
        assert floorplan["renderer"] == "svg_floorplan"
        assert required_zone_types <= zone_types
        assert floorplan["stats"]["room_count"] == len(floorplan["rooms"])
        assert floorplan["stats"]["corridor_count"] == len(corridor_segments)
        assert floorplan["stats"]["door_count"] == len(floorplan["doors"])
        assert floorplan["stats"]["icon_count"] == len(floorplan["icons"])
        assert all(len(room["polygon"]) >= 4 for room in floorplan["rooms"])
        assert all(len(corridor["polygon"]) == 4 for corridor in corridor_segments)
        assert all(len(corridor["segment"]) == 2 for corridor in corridor_segments)
        assert all(len(corridor["path"]) >= 2 for corridor in corridor_segments)
        assert all(corridor["is_orthogonal"] is True for corridor in corridor_segments)
        assert all(is_orthogonal_polyline(corridor["path"]) for corridor in corridor_segments)
        assert any(corridor["turn_count"] >= 1 for corridor in corridor_segments)
        assert any(door["segment"] for door in floorplan["doors"])

    print("test_demo_m20_indoor_floorplan_covers_realistic_scene_types passed.")


def test_demo_server_indoor_map_endpoint_returns_payload():
    service = DemoUIService("PKU")
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/map/indoor?site_id=PKU&building_id=library&floor=F1",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert payload["success"] is True
    assert payload["building_id"] == "library"
    assert payload["current_floor"]["id"] == "F1"
    assert any(item["id"] == "lib_reading_room_1" for item in payload["nodes"])
    print("test_demo_server_indoor_map_endpoint_returns_payload passed.")


def test_demo_white_road_skeleton_quality_and_geojson_coordinate_order():
    service = DemoUIService("PKU")
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    outdoor_path = os.path.join(repo_root, "data", "sites", "PKU", "outdoor.json")
    with open(outdoor_path, encoding="utf-8") as file:
        outdoor_data = json.load(file)

    node_index = {node["id"]: node for node in outdoor_data["nodes"]}
    bounds = service.get_bootstrap_payload()["map"]["bounds"]
    margin = 0.001
    role_counts = {}

    assert outdoor_data["edges"]
    assert len(node_index) == len(outdoor_data["nodes"])
    for node in outdoor_data["nodes"]:
        location = node["location"]
        assert is_number(location["lat"])
        assert is_number(location["lng"])
        assert bounds["lat_min"] - margin <= location["lat"] <= bounds["lat_max"] + margin
        assert bounds["lng_min"] - margin <= location["lng"] <= bounds["lng_max"] + margin
        role = node.get("network_role")
        if role:
            role_counts[role] = role_counts.get(role, 0) + 1

    assert role_counts["junction"] >= 200
    assert role_counts["bend"] >= 100
    assert role_counts["endpoint"] >= 250
    assert role_counts["poi_access"] >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    poi_nodes = [
        node
        for node in outdoor_data["nodes"]
        if node.get("category") != "road"
    ]
    assert len(poi_nodes) >= CORE_PKU_POI_COUNT + ENRICHED_NEW_POI_MIN
    for poi in poi_nodes:
        anchor_id = poi.get("route_anchor_node_id")
        assert anchor_id in node_index
        assert poi.get("route_anchor_source") == "white_road_projection"
        assert poi.get("route_anchor_needs_review") is False
    for edge in outdoor_data["edges"]:
        assert edge["from"] in node_index
        assert edge["to"] in node_index
        assert edge["type"] in {"white_road", "poi_access", "bike_lane"}
        if edge["type"] == "bike_lane":
            assert edge.get("source") == "m21_transport_demo"
            assert edge.get("allowed_transports") == ["bike"]
            continue
        assert len(edge["geometry"]) >= 2

    payload = service.get_map_geojson_payload()
    assert payload["stats"]["edge_feature_count"] > 0
    assert payload["stats"]["fallback_edge_count"] == 0
    edge_features = [
        item
        for item in payload["geojson"]["features"]
        if item["properties"]["kind"] == "edge"
    ]
    assert edge_features
    assert all(not item["properties"]["is_fallback_geometry"] for item in edge_features)
    node_features = [
        item
        for item in payload["geojson"]["features"]
        if item["properties"]["kind"] == "node"
    ]
    for feature in node_features:
        lng, lat = feature["geometry"]["coordinates"]
        assert is_number(lng)
        assert is_number(lat)
        assert bounds["lng_min"] - margin <= lng <= bounds["lng_max"] + margin
        assert bounds["lat_min"] - margin <= lat <= bounds["lat_max"] + margin
    print("test_demo_white_road_skeleton_quality_and_geojson_coordinate_order passed.")


def test_demo_m14_core_outdoor_route_is_reachable_without_fallback():
    service = DemoUIService("PKU")
    response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "library",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert response["success"] is True
    assert response["path"][0] == "gate_north"
    assert response["path"][-1] == "library"
    assert response["path"][1] == "road_access_gate_north"
    assert response["path"][-2] == "road_access_library"
    assert any(node_id.startswith("road_white_") for node_id in response["path"])
    stats = response["ui"]["route_geometry_stats"]
    assert stats["fallback_segment_count"] == 0
    assert stats["fallback_edge_count"] == 0
    assert stats["missing_edge_count"] == 0
    assert stats["geometry_segment_count"] == stats["route_segment_count"]
    print("test_demo_m14_core_outdoor_route_is_reachable_without_fallback passed.")


def test_demo_indoor_route_still_links_from_poi_gate():
    service = DemoUIService("PKU")
    response = service.plan_route(
        {
            "start_node_id": "library",
            "target_node_id": "lib_reading_room_1",
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )

    assert response["success"] is True
    assert response["path"] == ["library", "lib_entrance", "lib_reading_room_1"]
    assert response["ui"]["mappable_path_node_ids"] == ["library"]
    assert response["ui"]["route_geojson"] is None
    assert response["ui"]["route_geometry_stats"]["skipped_unmapped_segment_count"] == 2
    print("test_demo_indoor_route_still_links_from_poi_gate passed.")


def test_demo_poi_access_anchors_are_exposed():
    service = DemoUIService("PKU")
    access_ids = {node["id"] for node in service.map_nodes if node.get("network_role") == "poi_access"}
    poi_nodes = [node for node in service.map_nodes if not node["is_waypoint"]]

    assert len(access_ids) == len(poi_nodes)
    for poi in poi_nodes:
        anchor_id = poi.get("route_anchor_node_id")
        assert anchor_id in access_ids
        assert poi.get("route_anchor_distance_m") <= 80
    print("test_demo_poi_access_anchors_are_exposed passed.")


def test_demo_pku_poi_enrichment_audit_and_virtual_doors():
    audit_path = Path("data/sites/PKU/geo/pku_poi_enrichment_audit.json")
    outdoor_path = Path("data/sites/PKU/outdoor.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    outdoor = json.loads(outdoor_path.read_text(encoding="utf-8"))
    nodes = outdoor["nodes"]
    node_ids = {node["id"] for node in nodes}
    access_ids = {
        node["id"]
        for node in nodes
        if node.get("network_role") == "poi_access"
    }
    poi_nodes = [node for node in nodes if node.get("category") != "road"]
    enriched_nodes = [
        node
        for node in poi_nodes
        if node.get("poi_enrichment_source")
    ]
    source_counts = Counter(node["poi_enrichment_source"] for node in enriched_nodes)
    category_counts = Counter(node["category"] for node in enriched_nodes)
    door_nodes = [
        node
        for node in enriched_nodes
        if node.get("poi_enrichment_source") == "generated_building_directional_entrance"
    ]

    assert audit["metadata"]["stage"] == "M17_pku_poi_enrichment"
    assert audit["metadata"]["runtime_ui_calls_overpass"] is False
    assert audit["metadata"]["runtime_ui_calls_osmnx"] is False
    assert ENRICHED_NEW_POI_MIN <= audit["summary"]["new_poi_count"] <= ENRICHED_NEW_POI_MAX
    assert audit["summary"]["final_poi_count"] == len(poi_nodes)
    assert audit["summary"]["generated_access_node_count"] == len(access_ids)
    assert audit["summary"]["fallback_edge_count"] == 0
    assert audit["summary"]["poi_projection_needs_review_count"] == 0
    assert len(enriched_nodes) == audit["summary"]["new_poi_count"]
    assert source_counts["overpass_poi"] >= 40
    assert source_counts["overpass_named_building"] >= 15
    assert source_counts["generated_building_directional_entrance"] >= 30
    for category in ("shopping", "building", "building_entrance", "sports"):
        assert category_counts[category] > 0
    for poi in poi_nodes:
        anchor_id = poi.get("route_anchor_node_id")
        assert anchor_id in access_ids
        assert anchor_id in node_ids
    assert door_nodes
    for door in door_nodes:
        assert door["category"] == "building_entrance"
        assert door["virtual_entrance"] is True
        assert door["direction"] in {"north", "east", "south", "west"}
        assert door["parent_building_id"]
        assert door["parent_building_name"]
    print("test_demo_pku_poi_enrichment_audit_and_virtual_doors passed.")


def test_demo_pku_enriched_poi_search_targets_are_routeable():
    service = DemoUIService("PKU")
    search_cases = (
        {"keyword": "楼门", "category": "building_entrance", "limit": 3},
        {"keyword": "操场", "category": "sports", "limit": 3},
        {"keyword": "店", "category": "shopping", "limit": 3},
    )

    for case in search_cases:
        response = service.place_search(
            {
                **case,
                "sort_field": "distance_m",
                "start_node_id": "gate_north",
            }
        )
        available = [
            item
            for item in response["results"]
            if item.get("distance_status") == "available" and item.get("route_target_node_id")
        ]

        assert response["success"] is True
        assert response["total"] >= 1
        assert response["metadata"]["distance"]["available_count"] >= 1
        assert available
        assert available[0]["category"] == case["category"]

        route = service.plan_route(
            {
                "start_node_id": "gate_north",
                "target_node_id": available[0]["route_target_node_id"],
                "strategy": "shortest_distance",
                "transport_mode": "any",
            }
        )
        assert route["success"] is True
        stats = route["ui"]["route_geometry_stats"]
        assert stats["fallback_edge_count"] == 0
        assert stats["missing_edge_count"] == 0
    print("test_demo_pku_enriched_poi_search_targets_are_routeable passed.")


def test_demo_missing_osm_match_file_keeps_outdoor_geometry_routeable():
    original_osm_geo_dir = DemoUIService._osm_geo_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        DemoUIService._osm_geo_dir = lambda self: temp_path
        try:
            service = DemoUIService("PKU")
        finally:
            DemoUIService._osm_geo_dir = original_osm_geo_dir

    assert service.osm_edge_matches == []
    assert service.osm_edge_match_warnings == ["missing edge_osm_geometry_matches.json"]
    stats = service.get_map_geojson_payload()["stats"]
    assert stats["osm_matched_edge_count"] == 0
    assert stats["manual_geometry_edge_count"] == len(service.map_edges) > 0
    assert stats["fallback_edge_count"] == 0

    response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "library",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert response["success"] is True
    assert response["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    print("test_demo_missing_osm_match_file_keeps_outdoor_geometry_routeable passed.")


def test_demo_priority_outdoor_routes_are_reachable_without_fallback():
    service = DemoUIService("PKU")

    for start_node_id, target_node_id in (
        ("gate_north", "library"),
        ("gate_north", "canteen"),
        ("gate_east", "canteen"),
        ("gate_south", "teaching_building_1"),
        ("library", "sports_ground"),
        ("library", "canteen"),
        ("gate_north", "sports_ground"),
        ("gate_east", "parking_lot"),
        ("library", "toilet_lib_area"),
        ("sports_ground", "toilet_sports_area"),
        ("gate_south", "dormitory_1"),
        ("convenience_store", "teaching_building_2"),
    ):
        response = service.plan_route(
            {
                "start_node_id": start_node_id,
                "target_node_id": target_node_id,
                "strategy": "shortest_distance",
                "transport_mode": "any",
            }
        )

        assert response["success"] is True
        assert response["path"][0] == start_node_id
        assert response["path"][-1] == target_node_id
        stats = response["ui"]["route_geometry_stats"]
        assert stats["fallback_segment_count"] == 0
        assert stats["fallback_edge_count"] == 0
        assert stats["missing_edge_count"] == 0
    print("test_demo_priority_outdoor_routes_are_reachable_without_fallback passed.")


def test_demo_m15_core_white_road_routes_have_auditable_geometry_stats():
    service = DemoUIService("PKU")
    route_cases = (
        ("gate_north", "library", 200, 550),
        ("gate_east", "canteen", 700, 1200),
        ("gate_south", "teaching_building_1", 500, 950),
        ("library", "sports_ground", 120, 350),
        ("gate_north", "toilet_lib_area", 160, 450),
        ("gate_east", "parking_lot", 20, 120),
    )

    for start_node_id, target_node_id, min_distance_m, max_distance_m in route_cases:
        response = service.plan_route(
            {
                "start_node_id": start_node_id,
                "target_node_id": target_node_id,
                "strategy": "shortest_distance",
                "transport_mode": "any",
            }
        )

        assert response["success"] is True
        assert response["path"][0] == start_node_id
        assert response["path"][-1] == target_node_id
        assert min_distance_m <= response["total_distance_m"] <= max_distance_m

        route_geojson = response["ui"]["route_geojson"]
        assert route_geojson["geometry"]["type"] == "LineString"
        assert len(route_geojson["geometry"]["coordinates"]) >= 2

        stats = response["ui"]["route_geometry_stats"]
        assert stats["fallback_segment_count"] == 0
        assert stats["fallback_edge_count"] == 0
        assert stats["missing_edge_count"] == 0
        assert stats["skipped_unmapped_segment_count"] == 0
        assert stats["geometry_segment_count"] == stats["route_segment_count"]
        assert stats["osm_matched_segment_count"] > 0
        assert stats["manual_geometry_segment_count"] >= 2

        properties = route_geojson["properties"]
        for key in (
            "route_segment_count",
            "fallback_segment_count",
            "fallback_edge_count",
            "geometry_segment_count",
            "osm_matched_segment_count",
            "manual_geometry_segment_count",
            "missing_edge_count",
            "skipped_unmapped_segment_count",
        ):
            assert properties[key] == stats[key]
    print("test_demo_m15_core_white_road_routes_have_auditable_geometry_stats passed.")


def test_demo_m15_indoor_and_multi_target_routes_keep_expected_geometry_boundaries():
    service = DemoUIService("PKU")
    indoor_response = service.plan_route(
        {
            "start_node_id": "library",
            "target_node_id": "lib_reading_room_1",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert indoor_response["success"] is True
    assert indoor_response["path"] == ["library", "lib_entrance", "lib_reading_room_1"]
    assert indoor_response["total_distance_m"] <= 100
    assert indoor_response["ui"]["route_geojson"] is None
    indoor_stats = indoor_response["ui"]["route_geometry_stats"]
    assert indoor_stats["route_segment_count"] == 0
    assert indoor_stats["fallback_segment_count"] == 0
    assert indoor_stats["missing_edge_count"] == 0
    assert indoor_stats["skipped_unmapped_segment_count"] == 2

    multi_response = service.plan_multi_route(
        {
            "start_node_id": "gate_north",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
            "return_to_start": False,
        }
    )

    assert multi_response["success"] is True
    assert multi_response["visit_order"] == ["gate_north", "library", "canteen"]
    assert 800 <= multi_response["total_distance_m"] <= 1300
    assert multi_response["ui"]["route_geojson"]["type"] == "FeatureCollection"
    assert len(multi_response["ui"]["route_geojson"]["features"]) == 2
    stats = multi_response["ui"]["route_geometry_stats"]
    assert stats["fallback_segment_count"] == 0
    assert stats["fallback_edge_count"] == 0
    assert stats["missing_edge_count"] == 0
    assert stats["skipped_unmapped_segment_count"] == 0
    assert stats["geometry_segment_count"] == stats["route_segment_count"]
    assert stats["osm_matched_segment_count"] > 0
    assert stats["manual_geometry_segment_count"] >= 4
    print("test_demo_m15_indoor_and_multi_target_routes_keep_expected_geometry_boundaries passed.")


def test_demo_indoor_route_ui_views_cover_single_outdoor_to_indoor_and_multi_cases():
    service = DemoUIService("PKU")
    indoor_response = service.plan_route(
        {
            "start_node_id": "library",
            "target_node_id": "lib_reading_room_1",
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )

    assert indoor_response["success"] is True
    assert indoor_response["ui"]["default_route_view"] == "indoor:library:F1"
    assert any(view["id"] == "outdoor" for view in indoor_response["ui"]["available_route_views"])
    assert any(view["id"] == "indoor:library:F1" for view in indoor_response["ui"]["available_route_views"])
    assert indoor_response["ui"]["indoor_route_views"][0]["building_id"] == "library"
    floor_view = indoor_response["ui"]["indoor_route_views"][0]["floors"][0]
    assert floor_view["floor_id"] == "F1"
    assert floor_view["route_node_ids"] == ["lib_entrance", "lib_reading_room_1"]
    assert floor_view["path_step_indices"] == [1, 2]
    assert floor_view["route_step_indices"] == [1, 2]
    assert floor_view["contains_target"] is True

    mixed_response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "lib_reading_room_2",
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )

    assert mixed_response["success"] is True
    assert mixed_response["ui"]["default_route_view"] == "outdoor"
    assert mixed_response["ui"]["route_geojson"] is not None
    assert mixed_response["ui"]["indoor_route_views"]
    mixed_floors = {
        floor["floor_id"]
        for building in mixed_response["ui"]["indoor_route_views"]
        for floor in building["floors"]
    }
    assert "F2" in mixed_floors
    assert any(view["kind"] == "indoor" for view in mixed_response["ui"]["available_route_views"])

    multi_response = service.plan_multi_route(
        {
            "start_node_id": "gate_north",
            "target_node_ids": ["dorm1_room_101"],
            "strategy": "shortest_distance",
            "transport_mode": "walk",
            "return_to_start": False,
        }
    )

    assert multi_response["success"] is True
    assert multi_response["route_type"] == "multi_target"
    assert multi_response["ui"]["indoor_route_views"]
    assert multi_response["ui"]["indoor_route_views"][0]["building_id"] == "dormitory_1"
    assert any(view["kind"] == "indoor" for view in multi_response["ui"]["available_route_views"])
    print("test_demo_indoor_route_ui_views_cover_single_outdoor_to_indoor_and_multi_cases passed.")


def test_demo_waypoints_are_not_regular_route_targets_or_search_results():
    service = DemoUIService("PKU")
    bootstrap = service.get_bootstrap_payload()
    payload = service.get_map_geojson_payload()
    waypoint_ids = {
        feature["properties"]["id"]
        for feature in payload["geojson"]["features"]
        if feature["properties"]["kind"] == "node" and feature["properties"]["is_waypoint"]
    }

    assert waypoint_ids
    assert all(target["display_role"] == "poi" for target in bootstrap["route_targets"])
    assert not any(target["id"] in waypoint_ids for target in bootstrap["route_targets"])

    scenic = service.scenic_search({"keyword": "路口", "category": "", "limit": 20})
    places = service.place_search({"keyword": "路口", "category": "", "limit": 20})
    for response in (scenic, places):
        assert response["success"] is True
        offending = [
            item
            for item in response["results"]
            if item.get("route_target_node_id") and item.get("route_target_node_id") in waypoint_ids
        ]
        assert not offending, offending
    print("test_demo_waypoints_are_not_regular_route_targets_or_search_results passed.")


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
    assert response["total"] >= 1
    assert response["results"][0]["route_target_node_id"] == "library"
    assert response["results"][0]["has_map_location"] is True
    print("test_demo_scenic_search_is_routeable passed.")


def test_demo_place_search_distance_order():
    service = DemoUIService("PKU")
    response = service.place_search(
        {
            "keyword": "",
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


def assert_nearby_place_response(response, *, center_node_id, radius_m, category):
    assert response["success"] is True
    assert response["query_type"] == "place_search"
    assert response["filters"]["nearby_search"] is True
    assert response["filters"]["center_node_id"] == center_node_id
    assert response["filters"]["radius_m"] == float(radius_m)
    assert response["metadata"]["nearby"]["center_node_id"] == center_node_id
    assert response["metadata"]["nearby"]["radius_m"] == float(radius_m)
    assert response["metadata"]["nearby"]["distance_basis"] == "graph_shortest_path"
    assert response["results"]
    distances = [item["distance_m"] for item in response["results"]]
    assert distances == sorted(distances)
    assert all(item["distance_status"] == "available" for item in response["results"])
    assert all(item["distance_m"] <= radius_m for item in response["results"])
    assert all(item["category"] == category for item in response["results"])
    assert all(item["nearby_center_node_id"] == center_node_id for item in response["results"])
    assert all(item["nearby_reason"] for item in response["results"])


def test_demo_m22_fixed_nearby_facility_scenarios():
    service = DemoUIService("PKU")

    library_restrooms = service.place_search(
        {
            "keyword": "",
            "category": "restroom",
            "center_node_id": "library",
            "radius_m": 220,
            "limit": 10,
        }
    )
    assert_nearby_place_response(
        library_restrooms,
        center_node_id="library",
        radius_m=220,
        category="restroom",
    )
    assert library_restrooms["results"][0]["route_target_node_id"] == "lib_toilet_1f"

    teaching_shopping = service.place_search(
        {
            "keyword": "",
            "category": "shopping",
            "center_node_id": "teaching_building_1",
            "radius_m": 500,
            "limit": 10,
        }
    )
    assert_nearby_place_response(
        teaching_shopping,
        center_node_id="teaching_building_1",
        radius_m=500,
        category="shopping",
    )
    assert teaching_shopping["results"][0]["route_target_node_id"] == "poi_osm_shopping_node_13006577029"

    canteen_services = service.place_search(
        {
            "keyword": "",
            "category": "service",
            "center_node_id": "canteen",
            "radius_m": 300,
            "limit": 10,
        }
    )
    assert_nearby_place_response(
        canteen_services,
        center_node_id="canteen",
        radius_m=300,
        category="service",
    )
    assert canteen_services["results"][0]["route_target_node_id"] == "tb2_service_desk"

    small_radius = service.place_search(
        {
            "keyword": "",
            "category": "shopping",
            "center_node_id": "teaching_building_1",
            "radius_m": 500,
            "limit": 20,
        }
    )
    large_radius = service.place_search(
        {
            "keyword": "",
            "category": "shopping",
            "center_node_id": "teaching_building_1",
            "radius_m": 700,
            "limit": 20,
        }
    )
    small_ids = [item["route_target_node_id"] for item in small_radius["results"]]
    large_ids = [item["route_target_node_id"] for item in large_radius["results"]]
    assert len(small_ids) < len(large_ids)
    assert large_ids[: len(small_ids)] == small_ids

    legacy = service.place_search(
        {
            "keyword": "便利店",
            "category": "shopping",
            "sort_field": "distance_m",
            "start_node_id": "gate_north",
            "limit": 3,
        }
    )
    assert legacy["success"] is True
    assert legacy["filters"]["nearby_search"] is False
    assert legacy["results"][0]["route_target_node_id"] == "convenience_store"
    assert "nearby_reason" not in legacy["results"][0]
    print("test_demo_m22_fixed_nearby_facility_scenarios passed.")


def test_demo_main_query_recommend_route_chains_remain_available():
    service = DemoUIService("PKU")

    scenic = service.scenic_search(
        {
            "keyword": "图书馆",
            "category": "education",
            "sort_field": "heat",
            "start_node_id": "gate_north",
            "limit": 3,
        }
    )
    scenic_target = scenic["results"][0]["route_target_node_id"]
    scenic_route = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": scenic_target,
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert scenic["success"] is True
    assert scenic["ui"]["routeable_result_count"] >= 1
    assert scenic["metadata"]["distance"]["status_counts"]["available"] >= 1
    assert scenic_target == "library"
    assert scenic["results"][0]["distance_status"] == "available"
    assert scenic["results"][0]["distance_m"] > 0
    assert scenic_route["success"] is True

    place = service.place_search(
        {
            "keyword": "",
            "category": "restroom",
            "sort_field": "distance_m",
            "start_node_id": "gate_north",
            "limit": 4,
        }
    )
    place_distances = [
        item["distance_m"]
        for item in place["results"]
        if item.get("distance_status") == "available"
    ]

    assert place["success"] is True
    assert place["metadata"]["distance"]["available_count"] == place["total"]
    assert place["metadata"]["distance"]["status_counts"]["available"] == place["total"]
    assert place_distances == sorted(place_distances)
    assert place["results"][0]["route_target_node_id"]
    assert all(item["distance_status"] == "available" for item in place["results"])
    place_route = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": place["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert place_route["success"] is True

    catering = service.catering_search(
        {
            "keyword": "",
            "cuisine": "",
            "sort_field": "distance_m",
            "start_node_id": "gate_north",
            "limit": 2,
        }
    )
    catering_distances = [
        item["distance_m"]
        for item in catering["results"]
        if item.get("distance_status") == "available"
    ]

    assert catering["success"] is True
    assert catering["total"] == 2
    assert catering["metadata"]["distance"]["available_count"] == 2
    assert catering["metadata"]["distance"]["status_counts"]["available"] == 2
    assert catering_distances == sorted(catering_distances)
    assert catering["results"][0]["distance_status"] == "available"
    assert catering["results"][0]["route_target_node_id"]
    catering_route = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": catering["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert catering_route["success"] is True

    multi_route = service.plan_multi_route(
        {
            "start_node_id": "gate_north",
            "target_node_ids": [
                scenic["results"][0]["route_target_node_id"],
                catering["results"][0]["route_target_node_id"],
            ],
            "strategy": "shortest_distance",
            "transport_mode": "any",
            "return_to_start": False,
        }
    )

    assert multi_route["success"] is True
    assert multi_route["route_type"] == "multi_target"
    assert multi_route["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    print("test_demo_main_query_recommend_route_chains_remain_available passed.")


def test_demo_diary_fulltext_search_links_to_route():
    service = DemoUIService("PKU")
    response = service.diary_fulltext_search({"query": "图书馆 自习", "limit": 3})

    assert response["success"] is True
    assert response["total"] >= 1
    assert response["results"][0]["route_target_node_id"]
    assert response["results"][0]["content"]
    assert response["results"][0]["images"]
    print("test_demo_diary_fulltext_search_links_to_route passed.")


def test_demo_m23_interest_user_switch_changes_scenic_recommendations():
    service = DemoUIService("PKU")

    study_response = service.scenic_search(
        {
            "user_id": "user_001",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )
    food_response = service.scenic_search(
        {
            "user_id": "user_002",
            "sort_field": "interest",
            "start_node_id": "gate_north",
            "limit": 5,
        }
    )

    assert study_response["success"] is True
    assert food_response["success"] is True
    assert study_response["metadata"]["interest"]["active_for_ranking"] is True
    assert food_response["metadata"]["interest"]["active_for_ranking"] is True
    assert study_response["metadata"]["user_interest_context"]["user_id"] == "user_001"
    assert food_response["metadata"]["user_interest_context"]["user_id"] == "user_002"
    assert study_response["results"][0]["route_target_node_id"] == "library"
    assert food_response["results"][0]["route_target_node_id"] == "canteen"
    assert study_response["results"][0]["interest_match_score"] > 0
    assert food_response["results"][0]["interest_match_score"] > 0
    assert "兴趣命中" in study_response["results"][0]["interest_reason"]
    assert study_response["results"][0]["id"] != food_response["results"][0]["id"]
    print("test_demo_m23_interest_user_switch_changes_scenic_recommendations passed.")


def test_demo_m23_interest_user_switch_changes_diary_recommendations():
    service = DemoUIService("PKU")

    study_response = service.diary_list(
        {
            "user_id": "user_001",
            "sort_field": "interest",
            "limit": 5,
        }
    )
    food_response = service.diary_list(
        {
            "user_id": "user_002",
            "sort_field": "interest",
            "limit": 5,
        }
    )
    fulltext_response = service.diary_fulltext_search({"query": "图书馆 自习", "limit": 3})

    assert study_response["success"] is True
    assert food_response["success"] is True
    assert fulltext_response["success"] is True
    assert study_response["query_type"] == "diary_list"
    assert food_response["query_type"] == "diary_list"
    assert study_response["metadata"]["interest"]["active_for_ranking"] is True
    assert food_response["metadata"]["interest"]["active_for_ranking"] is True
    assert study_response["results"][0]["id"] in {"diary_001", "diary_003"}
    assert food_response["results"][0]["id"] == "diary_002"
    assert study_response["results"][0]["id"] != food_response["results"][0]["id"]
    assert study_response["results"][0]["interest_reason"]
    assert fulltext_response["query_type"] == "diary_fulltext_search"
    print("test_demo_m23_interest_user_switch_changes_diary_recommendations passed.")


def test_demo_diary_management_flow_links_to_route():
    service = DemoUIService("PKU")
    created = service.create_diary(
        {
            "title": "第十一周日记管理接口联调",
            "content": "这是一条用于 Web 服务层联调的日记管理记录。",
            "destination": "北京大学图书馆",
            "destination_node_id": "library",
            "rating": 4.4,
            "tags": ["第十一周", "日记管理"],
            "images": ["media/placeholders/ui_diary.jpg"],
            "videos": ["media/placeholders/ui_diary.mp4"],
        }
    )

    assert created["success"] is True
    assert created["query_type"] == "diary_create"
    assert created["metadata"]["site_id"] == "PKU"
    assert created["metadata"]["ui_contract"]["media_fields"] == ["images", "videos"]
    assert created["ui"]["source"] == "diary_create"
    assert created["ui"]["storage_mode"] == "memory_only"
    diary = created["results"][0]
    assert diary["route_target_node_id"] == "library"
    assert diary["route_target_name"] == "图书馆"
    assert diary["has_map_location"] is True

    found = service.diary_fulltext_search({"query": "服务层联调", "limit": 5})
    assert any(item["id"] == diary["id"] for item in found["results"])

    updated = service.update_diary(
        {
            "id": diary["id"],
            "updates": {
                "title": "第十一周日记管理接口复盘",
                "rating": 4.9,
                "videos": ["media/placeholders/ui_diary_updated.mp4"],
            },
        }
    )
    assert updated["success"] is True
    assert updated["results"][0]["title"] == "第十一周日记管理接口复盘"
    assert updated["results"][0]["videos"] == ["media/placeholders/ui_diary_updated.mp4"]

    rated = service.rate_diary({"id": diary["id"], "rating": 5})
    assert rated["success"] is True
    assert rated["results"][0]["rating"] == 5.0

    deleted = service.delete_diary({"id": diary["id"]})
    assert deleted["success"] is True
    assert deleted["ui"]["record_count"] == len(service.diary_service.records)
    print("test_demo_diary_management_flow_links_to_route passed.")


def test_demo_static_diary_center_contains_management_controls():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'id="diary-create-form"' in html
    assert 'id="diary-list-form"' in html
    assert 'id="diary-list-sort"' in html
    assert 'id="diary-destination-node"' in html
    assert 'id="diary-images"' in html
    assert 'id="diary-videos"' in html
    assert 'data-diary-edit-id' in script
    assert 'data-diary-delete-id' in script
    assert '"/api/diaries/create"' in script
    assert '"/api/diaries/update"' in script
    assert '"/api/diaries/rate"' in script
    assert '"/api/diaries/delete"' in script
    assert '"/api/diaries/list"' in script
    assert "buildInterestPayload" in script
    assert 'id="user-selector"' in html
    assert 'id="interest-tags"' in html
    print("test_demo_static_diary_center_contains_management_controls passed.")


def test_demo_static_leaflet_renderer_contains_local_assets_and_fallback():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'href="/vendor/leaflet/leaflet.css"' in html
    assert 'src="/vendor/leaflet/leaflet.js"' in html
    assert 'id="leaflet-map"' in html
    assert 'id="map-renderer-controls"' in html
    assert 'id="map-basemap-controls"' in html
    assert 'id="map-osm-layer-controls"' in html
    assert 'id="map-osm-status"' in html
    assert 'id="map-basemap-status"' in html
    assert 'id="white-road-role-controls"' in html
    assert 'id="white-road-edge-toggle"' in html
    assert 'id="path-node-toggle"' in html
    assert 'data-map-renderer="leaflet_geo"' in html
    assert 'data-map-renderer="simple_svg"' in html
    assert 'data-map-basemap="real_map"' in html
    assert 'data-map-basemap="none"' in html
    assert 'data-osm-layer="roads"' in html
    assert 'data-osm-layer="buildings"' in html
    assert 'data-osm-layer="water_landuse"' in html
    assert 'data-white-road-role="junction"' in html
    assert 'data-white-road-role="bend"' in html
    assert 'data-white-road-role="endpoint"' in html
    assert 'data-white-road-role="poi_access"' in html
    assert 'data-demo-action="single-route"' in html
    assert 'data-demo-action="multi-route"' in html
    assert 'id="help-map-acceptance"' in html
    assert 'class="map-legend"' in html
    assert "校园真实地图" in html
    assert "fallback 直线段" in html
    assert "OSM 匹配课程边" in html
    assert "POI 标记" in html
    assert "弱化路网点" in html
    assert "白线骨架点" in html
    assert "POI 接驳点" in html
    assert "OSM 道路" in html
    assert "水域 / 绿地" in html
    assert "renderSvgMap" in script
    assert "renderLeafletMap" in script
    assert "ensureLeafletMap" in script
    assert "L.tileLayer" in script
    assert "loadOsmLayers" in script
    assert "syncLeafletOsmLayers" in script
    assert "toggleOsmLayer" in script
    assert "leafletOsmLayerStyle" in script
    assert "syncLeafletLayerOrder" in script
    assert "syncLeafletBasemapLayer" in script
    assert "switchBasemapMode" in script
    assert "toggleWhiteRoadRole" in script
    assert "togglePathNodeVisibility" in script
    assert "refreshLeafletInspectionLayers" in script
    assert "shouldRenderWhiteRoadNode" in script
    assert "isPathNodeData" in script
    assert "isPathNodeFeature" in script
    assert "pathNodesVisible: false" in script
    assert "shouldRenderWhiteRoadEdge" in script
    assert 'edgeType === "white_road" || edgeType === "poi_access"' in script
    assert "syncLeafletRouteLayer" in script
    assert "switchMapRenderer" in script
    assert "runMapDemoAction" in script
    assert "syncMapDemoPanel" in script
    assert "routeGeometrySummaryText" in script
    assert "appendRouteGeometryCaption" in script
    assert "display_role" in script
    assert "is_waypoint" in script
    assert "network_role" in script
    assert "source_osm_id(s)" in script
    assert "source_highway(s)" in script
    assert "anchor_for" in script
    assert "projection_distance_m" in script
    assert "whiteRoadRoleLabel" in script
    assert "OSM匹配" in script
    assert "osm_matched" in script
    assert "manual_geometry_segment_count" in script
    assert "missing_edge_count" in script
    assert "is_fallback_geometry" in script
    assert "edgeGeometrySourceLabel" in script
    assert "source_osm_id" in script
    assert "source_highway" in script
    assert "isRenderableRouteGeoJson" in script
    assert "route_geojson" in script
    assert "fallbackToSvgMap" in script
    assert '"/api/map/geojson"' in script
    assert '"/api/map/osm-layers"' in script
    print("test_demo_static_leaflet_renderer_contains_local_assets_and_fallback passed.")


def test_demo_static_indoor_navigation_ui_contains_panel_and_entry_hooks():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'id="indoor-panel"' in html
    assert 'id="indoor-panel-meta"' in html
    assert 'id="indoor-panel-body"' in html
    assert "室内导航" in html
    assert "/api/map/indoor?" in script
    assert "进入室内导航" in script
    assert "createDefaultIndoorState" in script
    assert "renderIndoorPanel" in script
    assert "renderIndoorFloorplan" in script
    assert "renderIndoorSvgFloorplan" in script
    assert "renderIndoorNetworkFloorplan" in script
    assert "floorplan.corridors" in script
    assert "indoorCorridorPath" in script
    assert "indoor-floor-room" in script
    assert "indoor-floor-corridor" in script
    assert "indoor-floor-door" in script
    assert "indoor-route-overlay" in script
    assert "hydrateIndoorBootstrap" in script
    assert "syncIndoorStateFromRoute" in script
    assert "data-enter-indoor" in script
    assert "data-route-view" in script
    assert "data-indoor-floor" in script
    assert "data-indoor-zone" in script
    print("test_demo_static_indoor_navigation_ui_contains_panel_and_entry_hooks passed.")


def test_demo_static_m19_quickstart_and_advanced_controls_are_user_friendly():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'id="indoor-quickstart"' in html
    assert 'id="indoor-quick-actions"' in html
    assert 'id="indoor-supported-buildings-details"' in html
    assert 'id="indoor-supported-buildings"' in html
    assert "室内导航最快入口" in html
    assert "高级路线选项" in html
    assert "多目标路线（高级）" in html
    assert "高级地图调试选项" in html
    assert "补充图例" in html
    assert "renderIndoorQuickStart" in script
    assert 'data-show-supported-indoor' in script
    assert 'switchTab("route")' in script
    assert 'activeTab: "route"' in script
    assert "routeTargetLabel" in script
    print("test_demo_static_m19_quickstart_and_advanced_controls_are_user_friendly passed.")


def test_demo_static_m22_nearby_place_search_controls():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'id="place-center-node"' in html
    assert 'id="place-radius"' in html
    assert "附近中心" in html
    assert "范围" in html
    assert "buildPlaceSearchPayload" in script
    assert "runNearbySearch" in script
    assert "data-nearby-center" in script
    assert "center_node_id" in script
    assert "radius_m" in script
    assert "nearby_reason" in script
    assert "查附近设施" in script
    print("test_demo_static_m22_nearby_place_search_controls passed.")


def test_demo_aigc_preview_returns_template_storyboard():
    service = DemoUIService("PKU")
    response = service.aigc_preview(
        {
            "sample_id": "aigc_sample_001",
            "prompt": "银杏、未名湖和图书馆串成校园导览短片。",
            "style": "warm_storyboard",
            "duration_s": 9,
        }
    )

    assert response["success"] is True
    assert response["query_type"] == "aigc_preview"
    assert response["metadata"]["prototype_mode"] == "template_preview"
    assert response["metadata"]["real_model_called"] is False
    preview = response["results"][0]
    assert preview["sample_id"] == "aigc_sample_001"
    assert preview["image_placeholder"].endswith("pku_autumn_yanyuan.jpg")
    assert preview["preview_placeholder"].endswith("aigc_sample_001_storyboard.gif")
    assert preview["style_label"] == "暖色故事板"
    assert preview["duration_s"] == 9
    assert len(preview["storyboard_frames"]) == 4
    assert preview["source"]["real_model_called"] is False
    print("test_demo_aigc_preview_returns_template_storyboard passed.")


def test_demo_aigc_preview_validation_error():
    service = DemoUIService("PKU")
    response = service.aigc_preview({"sample_id": "missing_sample", "prompt": "测试"})

    assert response["success"] is False
    assert response["query_type"] == "aigc_preview"
    assert response["results"] == []
    print("test_demo_aigc_preview_validation_error passed.")


def test_demo_static_aigc_entry_contains_controls():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.join(repo_root, "src", "ui", "static", "index.html")
    js_path = os.path.join(repo_root, "src", "ui", "static", "app.js")

    with open(html_path, encoding="utf-8") as file:
        html = file.read()
    with open(js_path, encoding="utf-8") as file:
        script = file.read()

    assert 'data-tab="aigc"' in html
    assert 'data-panel="aigc"' in html
    assert 'id="aigc-form"' in html
    assert 'id="aigc-sample"' in html
    assert 'id="aigc-prompt"' in html
    assert 'id="aigc-style"' in html
    assert '"/api/aigc/preview"' in script
    assert "renderAigcPreview" in script
    print("test_demo_static_aigc_entry_contains_controls passed.")


def test_demo_route_overlay_contains_indoor_note():
    service = DemoUIService("PKU")
    response = service.plan_route(
        {
            "start_node_id": "library",
            "target_node_id": "lib_reading_room_1",
            "strategy": "shortest_distance",
            "transport_mode": "walk",
        }
    )

    assert response["success"] is True
    assert "lib_entrance" in response["path"]
    assert response["ui"]["mappable_path_node_ids"][-1] == "library"
    assert "室内段" in response["ui"]["caption"]
    print("test_demo_route_overlay_contains_indoor_note passed.")


def test_demo_m21_mixed_transport_single_and_multi_routes():
    service = DemoUIService("PKU")

    walk_response = service.plan_route(
        {
            "start_node_id": "gate_south",
            "target_node_id": "sports_ground",
            "strategy": "shortest_time",
            "transport_mode": "walk",
        }
    )
    bike_response = service.plan_route(
        {
            "start_node_id": "gate_south",
            "target_node_id": "sports_ground",
            "strategy": "shortest_time",
            "transport_mode": "bike",
        }
    )
    mixed_response = service.plan_route(
        {
            "start_node_id": "gate_south",
            "target_node_id": "sports_ground",
            "strategy": "shortest_time",
            "transport_mode": "mixed",
        }
    )

    assert walk_response["success"] is True
    assert bike_response["success"] is True
    assert mixed_response["success"] is True
    assert bike_response["total_weight"] < walk_response["total_weight"]
    assert mixed_response["total_weight"] < bike_response["total_weight"]
    assert mixed_response["summary"]["transport_text"] == "步行 + 自行车最短时间"
    assert mixed_response["summary"]["strategy_text"] == "最短时间"
    assert mixed_response["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    mixed_modes = {step["transport_mode_used"] for step in mixed_response["path_steps"]}
    assert {"walk", "bike"}.issubset(mixed_modes)

    multi_response = service.plan_multi_route(
        {
            "start_node_id": "gate_south",
            "target_node_ids": ["sports_ground", "library"],
            "strategy": "shortest_time",
            "transport_mode": "mixed",
            "return_to_start": False,
        }
    )

    assert multi_response["success"] is True
    assert multi_response["route_type"] == "multi_target"
    assert multi_response["summary"]["transport_text"] == "步行 + 自行车最短时间"
    assert multi_response["summary"]["strategy_text"] == "最短时间"
    assert multi_response["visit_order"][0] == "gate_south"
    assert multi_response["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    print("test_demo_m21_mixed_transport_single_and_multi_routes passed.")


def test_demo_multi_route_contains_visit_order_and_legs():
    service = DemoUIService("PKU")
    response = service.plan_multi_route(
        {
            "start_node_id": "gate_north",
            "target_node_ids": ["library", "canteen"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
            "return_to_start": True,
        }
    )

    assert response["success"] is True
    assert response["route_type"] == "multi_target"
    assert response["visit_order"][0] == "gate_north"
    assert response["visit_order"][-1] == "gate_north"
    assert response["ui"]["route_geometry_stats"]["fallback_edge_count"] == 0
    print("test_demo_multi_route_contains_visit_order_and_legs passed.")


def run_all_tests():
    print("Running UI demo service tests...")
    test_demo_bootstrap_contains_map_and_controls()
    test_m27x_thu_outdoor_main_chain_is_available_in_first_batch()
    test_m27x_thu_frontend_switch_contract_and_leaflet_data()
    test_m27x_zju_outdoor_main_chain_is_available_in_first_batch()
    test_m27x_zju_frontend_switch_contract_and_leaflet_data()
    test_m28x_fdu_outdoor_main_chain_is_available_in_remaining_batch()
    test_m28x_fdu_frontend_switch_contract_and_leaflet_data()
    test_m28x_sjtu_outdoor_main_chain_is_available_in_remaining_batch()
    test_m28x_sjtu_frontend_switch_contract_and_leaflet_data()
    test_m28x_tongji_outdoor_main_chain_is_available_in_remaining_batch()
    test_m28x_tongji_frontend_switch_contract_and_leaflet_data()
    test_m28x_seu_outdoor_main_chain_is_available_in_remaining_batch()
    test_m28x_seu_frontend_switch_contract_and_leaflet_data()
    test_m28x_sysu_outdoor_main_chain_is_available_in_remaining_batch()
    test_m28x_sysu_frontend_switch_contract_and_leaflet_data()
    test_demo_osm_edge_matches_file_records_m14_white_road_edges()
    test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order()
    test_demo_map_geojson_reports_geometry_coverage_stats()
    test_demo_white_road_skeleton_audit_matches_m14_edges()
    test_demo_osm_layers_payload_contains_local_feature_collections_and_stats()
    test_demo_osm_layers_geojson_uses_lng_lat_coordinate_order()
    test_demo_osm_layers_missing_file_keeps_core_map_available()
    test_demo_server_osm_layers_endpoint_returns_payload()
    test_demo_indoor_map_payload_contains_floor_nodes_and_zone_metadata()
    test_demo_m20_indoor_floorplan_covers_realistic_scene_types()
    test_demo_server_indoor_map_endpoint_returns_payload()
    test_demo_white_road_skeleton_quality_and_geojson_coordinate_order()
    test_demo_m14_core_outdoor_route_is_reachable_without_fallback()
    test_demo_indoor_route_still_links_from_poi_gate()
    test_demo_poi_access_anchors_are_exposed()
    test_demo_pku_poi_enrichment_audit_and_virtual_doors()
    test_demo_pku_enriched_poi_search_targets_are_routeable()
    test_demo_missing_osm_match_file_keeps_outdoor_geometry_routeable()
    test_demo_priority_outdoor_routes_are_reachable_without_fallback()
    test_demo_m15_core_white_road_routes_have_auditable_geometry_stats()
    test_demo_m15_indoor_and_multi_target_routes_keep_expected_geometry_boundaries()
    test_demo_indoor_route_ui_views_cover_single_outdoor_to_indoor_and_multi_cases()
    test_demo_waypoints_are_not_regular_route_targets_or_search_results()
    test_demo_scenic_search_is_routeable()
    test_demo_place_search_distance_order()
    test_demo_m22_fixed_nearby_facility_scenarios()
    test_demo_main_query_recommend_route_chains_remain_available()
    test_demo_diary_fulltext_search_links_to_route()
    test_demo_m23_interest_user_switch_changes_scenic_recommendations()
    test_demo_m23_interest_user_switch_changes_diary_recommendations()
    test_demo_diary_management_flow_links_to_route()
    test_demo_static_diary_center_contains_management_controls()
    test_demo_static_leaflet_renderer_contains_local_assets_and_fallback()
    test_demo_static_indoor_navigation_ui_contains_panel_and_entry_hooks()
    test_demo_static_m19_quickstart_and_advanced_controls_are_user_friendly()
    test_demo_static_m22_nearby_place_search_controls()
    test_demo_aigc_preview_returns_template_storyboard()
    test_demo_aigc_preview_validation_error()
    test_demo_static_aigc_entry_contains_controls()
    test_demo_route_overlay_contains_indoor_note()
    test_demo_m21_mixed_transport_single_and_multi_routes()
    test_demo_multi_route_contains_visit_order_and_legs()
    print("All UI demo service tests passed.")


if __name__ == "__main__":
    run_all_tests()

