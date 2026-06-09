import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.ui.demo_service import DemoUIService
from src.ui.demo_server import build_handler


EXTENSION_SITE_IDS = [
    "THU",
    "WHU",
    "XMU",
    "ZJU",
    "NJU",
    "FDU",
    "SJTU",
    "TONGJI",
    "SEU",
    "SYSU",
    "SCU",
    "HNU",
    "SDU",
    "HUST",
    "SCUT",
    "OUC",
    "SUDA",
    "HIT",
    "YNU",
    "HZAU",
]
M32A_SITE_IDS = ["PKU", *EXTENSION_SITE_IDS]


def _global_site_ids() -> list[str]:
    payload = json.loads(Path("data/global_sites.json").read_text(encoding="utf-8"))
    return [item["id"] for item in payload["sites"]]


@contextmanager
def _demo_api_server():
    service = DemoUIService("PKU")
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _read_json(request: str | urllib.request.Request) -> tuple[int, dict[str, object]]:
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise AssertionError(f"API request failed with {error.code}: {body}") from error


def _get_json(base_url: str, path: str, query: dict[str, object]) -> tuple[int, dict[str, object]]:
    encoded_query = urllib.parse.urlencode(query)
    return _read_json(f"{base_url}{path}?{encoded_query}")


def _post_json(base_url: str, path: str, body: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    return _read_json(request)


def _assert_search_response(payload: dict[str, object], site_id: str) -> None:
    assert payload["success"] is True
    assert payload["results"]
    assert payload["total"] >= len(payload["results"])
    assert all(item["site_id"] == site_id for item in payload["results"])


def _indoor_library_target(bootstrap: dict[str, object]) -> str:
    for target in bootstrap["route_targets"]:
        if target.get("graph_type") == "indoor" and target.get("building_id") == "library":
            return target["id"]
    raise AssertionError(f"missing library indoor route target for {bootstrap['site']['id']}")


def test_m32a_http_api_matrix_covers_pku_and_twenty_extension_sites():
    assert len(EXTENSION_SITE_IDS) == 20
    global_site_ids = _global_site_ids()
    assert set(M32A_SITE_IDS) <= set(global_site_ids)
    assert len(global_site_ids) >= len(M32A_SITE_IDS)

    with _demo_api_server() as base_url:
        for site_id in M32A_SITE_IDS:
            status, bootstrap = _get_json(base_url, "/api/bootstrap", {"site_id": site_id})
            assert status == 200
            assert bootstrap["site"]["id"] == site_id
            assert bootstrap["site"]["is_available"] is True
            assert bootstrap["site"]["data_status"] == "available"
            assert set(M32A_SITE_IDS) <= {item["id"] for item in bootstrap["sites"]}
            assert bootstrap["map_renderer"] == "leaflet_geo"
            assert bootstrap["map_capabilities"]["geojson_endpoint"] == "/api/map/geojson"
            assert bootstrap["map_capabilities"]["indoor_map_endpoint"] == "/api/map/indoor"
            assert bootstrap["map_capabilities"]["indoor_navigation"] is True
            assert bootstrap["map_capabilities"]["indoor_supported_building_count"] >= 5
            assert [item["value"] for item in bootstrap["controls"]["transport_modes"]] == [
                "walk",
                "bike",
                "mixed",
            ]

            status, geojson = _get_json(base_url, "/api/map/geojson", {"site_id": site_id})
            assert status == 200
            assert geojson["success"] is True
            assert geojson["site_id"] == site_id
            assert geojson["geojson"]["type"] == "FeatureCollection"
            assert geojson["stats"]["node_feature_count"] > 0
            assert geojson["stats"]["edge_feature_count"] > 0
            assert geojson["stats"]["feature_count"] == len(geojson["geojson"]["features"])

            start_node_id = bootstrap["default_start_node"]
            default_user_id = bootstrap["default_user_id"]
            common_query = {"site_id": site_id, "start_node_id": start_node_id, "limit": 3}

            status, scenic = _post_json(
                base_url,
                "/api/search/scenic",
                {**common_query, "sort_field": "interest", "user_id": default_user_id},
            )
            assert status == 200
            _assert_search_response(scenic, site_id)
            assert scenic["metadata"]["user_interest_context"]["user_id"] == default_user_id

            status, places = _post_json(
                base_url,
                "/api/search/places",
                {**common_query, "category": "education", "sort_field": "distance_m"},
            )
            assert status == 200
            _assert_search_response(places, site_id)
            assert places["filters"]["site_id"] == site_id

            status, catering = _post_json(
                base_url,
                "/api/recommend/catering",
                {**common_query, "sort_field": "distance_m"},
            )
            assert status == 200
            _assert_search_response(catering, site_id)
            assert catering["filters"]["site_id"] == site_id

            outdoor_route_body = {
                "site_id": site_id,
                "start_node_id": start_node_id,
                "target_node_id": "library",
                "strategy": "shortest_time",
                "transport_mode": "mixed",
            }
            status, outdoor_route = _post_json(base_url, "/api/route", outdoor_route_body)
            assert status == 200
            assert outdoor_route["success"] is True
            assert outdoor_route["site_id"] == site_id
            assert outdoor_route["target_node_id"] == "library"
            assert outdoor_route["ui"]["route_geojson"]["type"] == "Feature"
            assert outdoor_route["ui"]["route_geojson"]["geometry"]["type"] == "LineString"
            assert outdoor_route["summary"]["transport_text"] == "步行 + 自行车最短时间"

            status, multi_route = _post_json(
                base_url,
                "/api/route/multi",
                {
                    "site_id": site_id,
                    "start_node_id": start_node_id,
                    "target_node_ids": ["library", "canteen"],
                    "strategy": "shortest_time",
                    "transport_mode": "mixed",
                    "return_to_start": False,
                },
            )
            assert status == 200
            assert multi_route["success"] is True
            assert multi_route["site_id"] == site_id
            assert multi_route["route_type"] == "multi_target"
            assert multi_route["target_node_ids"] == ["library", "canteen"]
            assert multi_route["summary"]["target_count"] == 2

            indoor_building = bootstrap["map_capabilities"]["indoor_supported_buildings"][0]
            status, indoor_map = _get_json(
                base_url,
                "/api/map/indoor",
                {
                    "site_id": site_id,
                    "building_id": indoor_building["building_id"],
                    "floor": indoor_building["default_floor_id"],
                },
            )
            assert status == 200
            assert indoor_map["success"] is True
            assert indoor_map["site_id"] == site_id
            assert indoor_map["building_id"] == indoor_building["building_id"]
            assert indoor_map["floorplan"]["renderer"] == "svg_floorplan"
            assert indoor_map["nodes"]
            assert indoor_map["edges"]

            indoor_target_id = _indoor_library_target(bootstrap)
            status, indoor_route = _post_json(
                base_url,
                "/api/route",
                {
                    "site_id": site_id,
                    "start_node_id": start_node_id,
                    "target_node_id": indoor_target_id,
                    "strategy": "shortest_time",
                    "transport_mode": "walk",
                },
            )
            assert status == 200
            assert indoor_route["success"] is True
            assert indoor_route["site_id"] == site_id
            assert indoor_route["target_node_id"] == indoor_target_id
            assert indoor_route["ui"]["indoor_route_views"]
            assert any(view["kind"] == "indoor" for view in indoor_route["ui"]["available_route_views"])

            status, indoor_multi_route = _post_json(
                base_url,
                "/api/route/multi",
                {
                    "site_id": site_id,
                    "start_node_id": start_node_id,
                    "target_node_ids": ["library", indoor_target_id],
                    "strategy": "shortest_time",
                    "transport_mode": "walk",
                    "return_to_start": False,
                },
            )
            assert status == 200
            assert indoor_multi_route["success"] is True
            assert indoor_multi_route["site_id"] == site_id
            assert indoor_multi_route["route_type"] == "multi_target"
            assert indoor_multi_route["ui"]["indoor_route_views"]

        status, pku_bootstrap = _get_json(base_url, "/api/bootstrap", {"site_id": "PKU"})
        assert status == 200
        assert pku_bootstrap["site"]["id"] == "PKU"
        assert pku_bootstrap["map"]["node_count"] > 1000
