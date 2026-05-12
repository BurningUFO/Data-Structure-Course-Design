import json
import os
import sys
import tempfile
import threading
import urllib.request
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


def test_demo_bootstrap_contains_map_and_controls():
    service = DemoUIService("PKU")
    payload = service.get_bootstrap_payload()

    assert payload["product"]["name"] == "智能校园导览系统"
    assert payload["product"]["stage"] == "正式产品演示版"
    assert payload["sites"][0]["id"] == "PKU"
    assert payload["sites"][0]["is_current"] is True
    assert payload["site"]["name"] == "北京大学"
    assert payload["default_start_node"] == "gate_north"
    assert payload["map"]["node_count"] >= 10
    assert payload["map"]["edge_count"] >= 10
    assert payload["map"]["geometry_edge_count"] > 8
    assert payload["map"]["osm_matched_edge_count"] > 0
    assert payload["map"]["manual_geometry_edge_count"] >= 0
    assert payload["map"]["fallback_edge_count"] > 0
    assert payload["map"]["geometry_coverage_ratio"] >= 0.17
    assert payload["map"]["osm_matched_coverage_ratio"] > 0
    assert payload["map_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["renderers"] == ["simple_svg", "leaflet_geo"]
    assert payload["map_capabilities"]["default_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["fallback_renderer"] == "simple_svg"
    assert payload["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
    assert payload["map_capabilities"]["osm_layers_endpoint"] == "/api/map/osm-layers"
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
    assert payload["stats"]["site_count"] >= 1
    assert payload["stats"]["aigc_sample_count"] == 3
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
    assert payload["help"]["stage"] == "正式产品演示版 · 地图方案 B M9"
    assert len(payload["help"]["demo_flow"]) >= 3
    assert any("Leaflet / SVG" in item for item in payload["help"]["demo_flow"])
    assert any("[lng, lat]" in item for item in payload["help"]["map_acceptance"])
    assert any("真实瓦片" in item for item in payload["help"]["map_acceptance"])
    assert any("M9 将关键课程图 edge 匹配到本地 OSM 道路线形" in item for item in payload["help"]["map_acceptance"])
    assert any(item["value"] == "education" for item in payload["controls"]["scenic_categories"])
    print("test_demo_bootstrap_contains_map_and_controls passed.")


def test_demo_osm_edge_matches_file_loads_for_m9():
    service = DemoUIService("PKU")
    match_path = Path("data/sites/PKU/geo/edge_osm_geometry_matches.json")
    loaded = json.loads(match_path.read_text(encoding="utf-8"))

    assert loaded["metadata"]["stage"] == "M9"
    assert loaded["metadata"]["source_file"] == "osm_roads_simplified.geojson"
    assert loaded["metadata"]["runtime_policy"]["routing_authority"] == "course_graph"
    assert service.osm_edge_match_warnings == []
    assert len(service.osm_edge_matches) == len(loaded["matches"])

    edge_keys = {item["edge_key"] for item in service.osm_edge_matches}
    assert {
        "gate_north->square_center",
        "square_center->library",
        "road_cross->gate_east",
        "road_cross->canteen",
        "gate_south->teaching_building_1",
    } <= edge_keys

    first_match = service.osm_edge_matches[0]
    assert first_match["geometry_source"] == "osm_matched"
    assert first_match["osm_way_ids"]
    assert len(first_match["geometry"]) >= 2
    print("test_demo_osm_edge_matches_file_loads_for_m9 passed.")


def test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order():
    service = DemoUIService("PKU")
    payload = service.get_map_geojson_payload()

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert payload["geojson"]["type"] == "FeatureCollection"
    assert payload["stats"]["node_feature_count"] > 0
    assert payload["stats"]["edge_feature_count"] > 0
    assert payload["stats"]["geometry_edge_count"] > 8
    assert payload["stats"]["osm_matched_edge_count"] > 0
    assert payload["stats"]["manual_geometry_edge_count"] >= 0
    assert payload["stats"]["fallback_edge_count"] > 0
    assert (
        payload["stats"]["geometry_edge_count"]
        + payload["stats"]["fallback_edge_count"]
        == payload["stats"]["edge_feature_count"]
    )
    assert payload["stats"]["geometry_coverage_ratio"] >= 0.17

    features = payload["geojson"]["features"]
    node_features = [item for item in features if item["properties"]["kind"] == "node"]
    edge_features = [item for item in features if item["properties"]["kind"] == "edge"]
    assert len(node_features) == payload["stats"]["node_feature_count"]
    assert len(edge_features) == payload["stats"]["edge_feature_count"]

    node_index = {node["id"]: node for node in service.map_nodes}
    first_node = node_features[0]
    first_node_id = first_node["properties"]["id"]
    assert first_node["geometry"]["type"] == "Point"
    assert first_node["geometry"]["coordinates"] == [
        node_index[first_node_id]["lng"],
        node_index[first_node_id]["lat"],
    ]
    assert {"kind", "id", "name", "category", "category_label"} <= set(first_node["properties"])

    first_edge = edge_features[0]
    assert first_edge["geometry"]["type"] == "LineString"
    assert len(first_edge["geometry"]["coordinates"]) >= 2
    assert {
        "kind",
        "from",
        "to",
        "name",
        "edge_type",
            "distance_m",
            "geometry_source",
            "geometry_confidence",
            "osm_way_ids",
            "is_fallback_geometry",
        } <= set(first_edge["properties"])
    source = node_index[first_edge["properties"]["from"]]
    target = node_index[first_edge["properties"]["to"]]
    assert first_edge["geometry"]["coordinates"][0] == [source["lng"], source["lat"]]
    assert first_edge["geometry"]["coordinates"][-1] == [target["lng"], target["lat"]]
    assert any(edge["properties"]["geometry_source"] == "osm_matched" for edge in edge_features)
    assert any(edge["properties"]["geometry_source"] == "manual" for edge in edge_features)
    assert any(edge["properties"]["geometry_source"] == "fallback_line" for edge in edge_features)
    gate_edge = next(
        edge
        for edge in edge_features
        if edge["properties"]["from"] == "gate_north"
        and edge["properties"]["to"] == "square_center"
    )
    assert gate_edge["properties"]["geometry_source"] == "osm_matched"
    assert gate_edge["properties"]["geometry_confidence"] > 0
    assert gate_edge["properties"]["osm_way_ids"] == ["1075644762"]
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
    assert stats["geometry_edge_count"] == geometry_edge_count
    assert stats["osm_matched_edge_count"] == osm_matched_edge_count
    assert stats["manual_geometry_edge_count"] == manual_geometry_edge_count
    assert stats["fallback_edge_count"] == fallback_edge_count
    assert stats["osm_matched_edge_count"] == 13
    assert stats["manual_geometry_edge_count"] == 1
    assert stats["geometry_edge_count"] > 8
    assert stats["geometry_coverage_ratio"] == round(
        geometry_edge_count / len(service.map_edges),
        4,
    )
    assert stats["osm_matched_coverage_ratio"] == round(
        osm_matched_edge_count / len(service.map_edges),
        4,
    )

    bootstrap_map = service.get_bootstrap_payload()["map"]
    assert bootstrap_map["geometry_edge_count"] == stats["geometry_edge_count"]
    assert bootstrap_map["osm_matched_edge_count"] == stats["osm_matched_edge_count"]
    assert bootstrap_map["manual_geometry_edge_count"] == stats["manual_geometry_edge_count"]
    assert bootstrap_map["fallback_edge_count"] == stats["fallback_edge_count"]
    assert bootstrap_map["geometry_coverage_ratio"] == stats["geometry_coverage_ratio"]
    assert bootstrap_map["osm_matched_coverage_ratio"] == stats["osm_matched_coverage_ratio"]
    print("test_demo_map_geojson_reports_geometry_coverage_stats passed.")


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


def test_demo_osm_layers_missing_file_keeps_core_map_and_route_available():
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
    print("test_demo_osm_layers_missing_file_keeps_core_map_and_route_available passed.")


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


def test_demo_outdoor_geometry_quality_and_geojson_coordinate_order():
    service = DemoUIService("PKU")
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    outdoor_path = os.path.join(repo_root, "data", "sites", "PKU", "outdoor.json")
    with open(outdoor_path, encoding="utf-8") as file:
        outdoor_data = json.load(file)

    node_index = {node["id"]: node for node in outdoor_data["nodes"]}
    bounds = service.get_bootstrap_payload()["map"]["bounds"]
    margin = 0.001
    geometry_edges = [
        edge
        for edge in outdoor_data["edges"]
        if isinstance(edge.get("geometry"), list)
    ]
    assert geometry_edges

    for edge in geometry_edges:
        geometry = edge["geometry"]
        assert len(geometry) >= 2
        source = node_index[edge["from"]]["location"]
        target = node_index[edge["to"]]["location"]
        assert_close_coordinate(geometry[0], source)
        assert_close_coordinate(geometry[-1], target)
        for point in geometry:
            assert is_number(point["lat"])
            assert is_number(point["lng"])
            assert bounds["lat_min"] - margin <= point["lat"] <= bounds["lat_max"] + margin
            assert bounds["lng_min"] - margin <= point["lng"] <= bounds["lng_max"] + margin

    payload = service.get_map_geojson_payload()
    map_edge_lookup = {
        (edge["from"], edge["to"]): edge
        for edge in service.map_edges
    }
    edge_features = [
        item
        for item in payload["geojson"]["features"]
        if item["properties"]["kind"] == "edge"
    ]
    for feature in edge_features:
        properties = feature["properties"]
        coordinates = feature["geometry"]["coordinates"]
        assert feature["geometry"]["type"] == "LineString"
        assert len(coordinates) >= 2
        for lng, lat in coordinates:
            assert is_number(lng)
            assert is_number(lat)
            assert bounds["lng_min"] - margin <= lng <= bounds["lng_max"] + margin
            assert bounds["lat_min"] - margin <= lat <= bounds["lat_max"] + margin

        edge = map_edge_lookup[(properties["from"], properties["to"])]
        if edge.get("geometry"):
            assert coordinates == [
                [point["lng"], point["lat"]]
                for point in edge["geometry"]
            ]
    print("test_demo_outdoor_geometry_quality_and_geojson_coordinate_order passed.")


def test_demo_route_overlay_returns_geojson_with_reversed_edge_geometry():
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
    assert response["ui"]["mappable_path_node_ids"] == ["gate_north", "square_center", "library"]
    geojson = response["ui"]["route_geojson"]
    assert geojson["type"] == "Feature"
    assert geojson["geometry"]["type"] == "LineString"

    coordinates = geojson["geometry"]["coordinates"]
    assert coordinates[0] == [116.3055, 39.9929]
    assert coordinates[-1] == [116.307, 39.9915]
    lng, lat = coordinates[0]
    assert 116 < lng < 117
    assert 39 < lat < 40

    square_index = coordinates.index([116.3065, 39.9917])
    assert coordinates[square_index + 1] == [116.3063419, 39.9917316]

    stats = response["ui"]["route_geometry_stats"]
    assert stats["route_segment_count"] == 2
    assert stats["geometry_segment_count"] == 2
    assert stats["osm_matched_segment_count"] == 2
    assert stats["manual_geometry_segment_count"] == 0
    assert stats["fallback_segment_count"] < stats["route_segment_count"]
    assert stats["reverse_edge_reuse_count"] == 1
    assert geojson["properties"]["osm_matched_segment_count"] == 2
    assert geojson["properties"]["manual_geometry_segment_count"] == 0
    assert response["ui"]["stats"]["route_geometry"] == stats
    print("test_demo_route_overlay_returns_geojson_with_reversed_edge_geometry passed.")


def test_demo_reverse_route_reuses_osm_matched_geometry_in_reverse():
    service = DemoUIService("PKU")
    forward = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "library",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    reverse = service.plan_route(
        {
            "start_node_id": "library",
            "target_node_id": "gate_north",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert forward["success"] is True
    assert reverse["success"] is True
    forward_coordinates = forward["ui"]["route_geojson"]["geometry"]["coordinates"]
    reverse_coordinates = reverse["ui"]["route_geojson"]["geometry"]["coordinates"]
    assert reverse_coordinates == list(reversed(forward_coordinates))

    stats = reverse["ui"]["route_geometry_stats"]
    assert stats["route_segment_count"] == 2
    assert stats["osm_matched_segment_count"] == 2
    assert stats["manual_geometry_segment_count"] == 0
    assert stats["fallback_segment_count"] == 0
    assert stats["reverse_edge_reuse_count"] >= 1
    print("test_demo_reverse_route_reuses_osm_matched_geometry_in_reverse passed.")


def test_demo_route_overlay_falls_back_when_edge_has_no_geometry():
    service = DemoUIService("PKU")
    response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "campus_service_01",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )

    assert response["success"] is True
    assert response["path"] == ["gate_north", "campus_service_01"]
    geojson = response["ui"]["route_geojson"]
    assert geojson["type"] == "Feature"
    assert geojson["geometry"]["type"] == "LineString"
    assert geojson["geometry"]["coordinates"] == [
        [116.3055, 39.9929],
        [116.305, 39.9898],
    ]

    stats = response["ui"]["route_geometry_stats"]
    assert stats["route_segment_count"] == 1
    assert stats["fallback_segment_count"] == 1
    assert stats["geometry_segment_count"] == 0
    assert stats["osm_matched_segment_count"] == 0
    assert stats["manual_geometry_segment_count"] == 0
    assert stats["reverse_edge_reuse_count"] == 0
    assert stats["missing_edge_count"] == 0
    print("test_demo_route_overlay_falls_back_when_edge_has_no_geometry passed.")


def test_demo_missing_osm_match_file_uses_manual_and_fallback_geometry():
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
    assert stats["manual_geometry_edge_count"] == 14
    assert stats["fallback_edge_count"] == 67

    response = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": "library",
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert response["success"] is True
    route_stats = response["ui"]["route_geometry_stats"]
    assert route_stats["osm_matched_segment_count"] == 0
    assert route_stats["manual_geometry_segment_count"] == 2
    assert route_stats["fallback_segment_count"] == 0
    print("test_demo_missing_osm_match_file_uses_manual_and_fallback_geometry passed.")


def test_demo_priority_gate_routes_use_expanded_geometry():
    service = DemoUIService("PKU")

    for start_node_id, target_node_id in (
        ("gate_east", "road_cross"),
        ("road_cross", "gate_east"),
        ("gate_south", "teaching_building_1"),
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
        stats = response["ui"]["route_geometry_stats"]
        assert stats["route_segment_count"] == 1
        assert stats["geometry_segment_count"] == 1
        assert stats["osm_matched_segment_count"] == 1
        assert stats["fallback_segment_count"] == 0
        assert stats["coordinate_count"] > 2
    print("test_demo_priority_gate_routes_use_expanded_geometry passed.")


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
    assert scenic_target == "library"
    assert scenic_route["success"] is True
    assert scenic_route["summary"]["distance_text"] == "110.0 m"
    assert scenic_route["ui"]["mappable_path_node_ids"] == ["gate_north", "square_center", "library"]

    place = service.place_search(
        {
            "keyword": "洗手间",
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
    assert place_distances == sorted(place_distances)
    assert place["results"][0]["route_target_node_id"] == "toilet_sports_area"
    place_route = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": place["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert place_route["success"] is True
    assert place_route["ui"]["mappable_path_node_ids"]

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
    assert catering_distances == sorted(catering_distances)
    assert catering["results"][0]["route_target_node_id"] == "lib_cafe"
    catering_route = service.plan_route(
        {
            "start_node_id": "gate_north",
            "target_node_id": catering["results"][0]["route_target_node_id"],
            "strategy": "shortest_distance",
            "transport_mode": "any",
        }
    )
    assert catering_route["success"] is True
    assert "lib_cafe" in catering_route["path"]

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
    assert multi_route["summary"]["target_count"] == 2
    assert multi_route["summary"]["leg_count"] == len(multi_route["leg_results"])
    assert multi_route["ui"]["mappable_path_node_ids"]
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
    assert 'id="diary-destination-node"' in html
    assert 'id="diary-images"' in html
    assert 'id="diary-videos"' in html
    assert 'data-diary-edit-id' in script
    assert 'data-diary-delete-id' in script
    assert '"/api/diaries/create"' in script
    assert '"/api/diaries/update"' in script
    assert '"/api/diaries/rate"' in script
    assert '"/api/diaries/delete"' in script
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
    assert 'data-map-renderer="leaflet_geo"' in html
    assert 'data-map-renderer="simple_svg"' in html
    assert 'data-map-basemap="real_map"' in html
    assert 'data-map-basemap="none"' in html
    assert 'data-osm-layer="roads"' in html
    assert 'data-osm-layer="buildings"' in html
    assert 'data-osm-layer="water_landuse"' in html
    assert 'data-demo-action="single-route"' in html
    assert 'data-demo-action="multi-route"' in html
    assert 'id="help-map-acceptance"' in html
    assert 'class="map-legend"' in html
    assert "fallback 直线段" in html
    assert "OSM 匹配课程边" in html
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
    assert "syncLeafletRouteLayer" in script
    assert "switchMapRenderer" in script
    assert "runMapDemoAction" in script
    assert "syncMapDemoPanel" in script
    assert "routeGeometrySummaryText" in script
    assert "appendRouteGeometryCaption" in script
    assert "OSM匹配" in script
    assert "osm_matched" in script
    assert "manual_geometry_segment_count" in script
    assert "is_fallback_geometry" in script
    assert "edgeGeometrySourceLabel" in script
    assert "isRenderableRouteGeoJson" in script
    assert "route_geojson" in script
    assert "fallbackToSvgMap" in script
    assert '"/api/map/geojson"' in script
    assert '"/api/map/osm-layers"' in script
    print("test_demo_static_leaflet_renderer_contains_local_assets_and_fallback passed.")


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
    assert set(response["target_node_ids"]) == {"library", "canteen"}
    assert response["total_distance_m"] > 0
    assert response["estimated_time_s"] > 0
    assert len(response["leg_results"]) >= 2
    assert response["summary"]["visit_order_text"]
    assert response["summary"]["leg_count"] == len(response["leg_results"])
    assert response["ui"]["leg_summaries"]
    assert response["ui"]["display_steps"]
    assert "多目标访问顺序" in response["ui"]["caption"]

    route_geojson = response["ui"]["route_geojson"]
    assert route_geojson["type"] == "FeatureCollection"
    assert len(route_geojson["features"]) == len(response["leg_results"])
    for feature in route_geojson["features"]:
        assert feature["geometry"]["type"] == "LineString"
        assert len(feature["geometry"]["coordinates"]) >= 2
        lng, lat = feature["geometry"]["coordinates"][0]
        assert 116 < lng < 117
        assert 39 < lat < 40
        assert feature["properties"]["kind"] == "route"
        assert feature["properties"]["route_type"] == "multi_target_leg"

    stats = response["ui"]["route_geometry_stats"]
    assert stats["feature_count"] == len(route_geojson["features"])
    assert stats["route_segment_count"] >= len(response["leg_results"])
    assert stats["osm_matched_segment_count"] > 0
    assert stats["manual_geometry_segment_count"] >= 0
    assert stats["fallback_segment_count"] < stats["route_segment_count"]
    print("test_demo_multi_route_contains_visit_order_and_legs passed.")


def run_all_tests():
    print("Running UI demo service tests...")
    test_demo_bootstrap_contains_map_and_controls()
    test_demo_osm_edge_matches_file_loads_for_m9()
    test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order()
    test_demo_map_geojson_reports_geometry_coverage_stats()
    test_demo_osm_layers_payload_contains_local_feature_collections_and_stats()
    test_demo_osm_layers_geojson_uses_lng_lat_coordinate_order()
    test_demo_osm_layers_missing_file_keeps_core_map_and_route_available()
    test_demo_server_osm_layers_endpoint_returns_payload()
    test_demo_outdoor_geometry_quality_and_geojson_coordinate_order()
    test_demo_route_overlay_returns_geojson_with_reversed_edge_geometry()
    test_demo_reverse_route_reuses_osm_matched_geometry_in_reverse()
    test_demo_route_overlay_falls_back_when_edge_has_no_geometry()
    test_demo_missing_osm_match_file_uses_manual_and_fallback_geometry()
    test_demo_priority_gate_routes_use_expanded_geometry()
    test_demo_scenic_search_is_routeable()
    test_demo_place_search_distance_order()
    test_demo_main_query_recommend_route_chains_remain_available()
    test_demo_diary_fulltext_search_links_to_route()
    test_demo_diary_management_flow_links_to_route()
    test_demo_static_diary_center_contains_management_controls()
    test_demo_static_leaflet_renderer_contains_local_assets_and_fallback()
    test_demo_aigc_preview_returns_template_storyboard()
    test_demo_aigc_preview_validation_error()
    test_demo_static_aigc_entry_contains_controls()
    test_demo_route_overlay_contains_indoor_note()
    test_demo_multi_route_contains_visit_order_and_legs()
    print("All UI demo service tests passed.")


if __name__ == "__main__":
    run_all_tests()

