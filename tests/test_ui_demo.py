import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.ui.demo_service import DemoUIService


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
    assert payload["map_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["renderers"] == ["simple_svg", "leaflet_geo"]
    assert payload["map_capabilities"]["default_renderer"] == "leaflet_geo"
    assert payload["map_capabilities"]["fallback_renderer"] == "simple_svg"
    assert payload["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
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
    assert payload["help"]["browser_url"] == "http://127.0.0.1:8765"
    assert len(payload["help"]["demo_flow"]) >= 3
    assert any(item["value"] == "education" for item in payload["controls"]["scenic_categories"])
    print("test_demo_bootstrap_contains_map_and_controls passed.")


def test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order():
    service = DemoUIService("PKU")
    payload = service.get_map_geojson_payload()

    assert payload["success"] is True
    assert payload["site_id"] == "PKU"
    assert payload["geojson"]["type"] == "FeatureCollection"
    assert payload["stats"]["node_feature_count"] > 0
    assert payload["stats"]["edge_feature_count"] > 0
    assert payload["stats"]["fallback_edge_count"] > 0

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
    assert {"kind", "from", "to", "name", "edge_type", "distance_m"} <= set(first_edge["properties"])
    source = node_index[first_edge["properties"]["from"]]
    target = node_index[first_edge["properties"]["to"]]
    assert first_edge["geometry"]["coordinates"][0] == [source["lng"], source["lat"]]
    assert first_edge["geometry"]["coordinates"][-1] == [target["lng"], target["lat"]]
    print("test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order passed.")


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
    assert "renderSvgMap" in script
    assert "renderLeafletMap" in script
    assert "ensureLeafletMap" in script
    assert "syncLeafletRouteLayer" in script
    assert "fallbackToSvgMap" in script
    assert '"/api/map/geojson"' in script
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
    print("test_demo_multi_route_contains_visit_order_and_legs passed.")


def run_all_tests():
    print("Running UI demo service tests...")
    test_demo_bootstrap_contains_map_and_controls()
    test_demo_map_geojson_contains_nodes_edges_and_lng_lat_order()
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

