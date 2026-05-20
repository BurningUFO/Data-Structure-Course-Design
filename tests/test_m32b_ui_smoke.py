import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from html.parser import HTMLParser
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
ALL_SITE_IDS = ["PKU", *EXTENSION_SITE_IDS]
STATIC_DIR = Path("src/ui/static")


class StaticUiContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.data_tabs: set[str] = set()
        self.data_pages: set[str] = set()
        self.map_renderers: set[str] = set()
        self.map_basemaps: set[str] = set()
        self.demo_actions: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if element_id := attr_map.get("id"):
            self.ids.add(element_id)
        if tab := attr_map.get("data-tab"):
            self.data_tabs.add(tab)
        if page := attr_map.get("data-page"):
            self.data_pages.add(page)
        if renderer := attr_map.get("data-map-renderer"):
            self.map_renderers.add(renderer)
        if basemap := attr_map.get("data-map-basemap"):
            self.map_basemaps.add(basemap)
        if action := attr_map.get("data-demo-action"):
            self.demo_actions.add(action)


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


def _option_values(options: list[dict[str, object]]) -> set[str]:
    return {str(item["value"]) for item in options}


def test_m32b_static_shell_exposes_multicampus_ui_contract():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    parser = StaticUiContractParser()
    parser.feed(html)

    required_ids = {
        "site-selector",
        "global-start-node",
        "user-selector",
        "interest-tags",
        "scenic-form",
        "place-form",
        "catering-form",
        "diary-list-form",
        "diary-form",
        "route-form",
        "route-target",
        "route-strategy",
        "route-transport",
        "multi-route-form",
        "multi-route-targets",
        "map-renderer-controls",
        "map-data-status",
        "map-route-status",
        "map-renderer-status",
        "map-basemap-status",
        "map-osm-status",
        "campus-map",
        "leaflet-map",
        "map-caption",
        "route-summary",
        "route-steps",
        "indoor-panel",
        "results-list",
    }
    assert required_ids <= parser.ids
    assert {"home", "app"} <= parser.data_pages
    assert {"scenic", "place", "catering", "route", "diary", "aigc", "help"} <= parser.data_tabs
    assert parser.map_renderers == {"leaflet_geo", "simple_svg"}
    assert parser.map_basemaps == {"real_map", "none"}
    assert parser.demo_actions == {"single-route", "multi-route", "clear-route"}

    assert "/vendor/leaflet/leaflet.css" in html
    assert "/vendor/leaflet/leaflet.js" in html
    assert "unpkg.com" not in html
    assert "cdn.jsdelivr" not in html

    for function_name in [
        "loadSiteBootstrap",
        "renderMap",
        "renderSvgMap",
        "renderLeafletMap",
        "ensureLeafletMap",
        "syncLeafletRouteLayer",
        "fallbackToSvgMap",
    ]:
        assert f"function {function_name}" in app_js or f"async function {function_name}" in app_js
    for endpoint in ["/api/bootstrap", "/api/map/geojson", "/api/route", "/api/route/multi"]:
        assert endpoint in app_js


def test_m32b_twenty_extension_sites_have_ui_demo_materials():
    assert len(EXTENSION_SITE_IDS) == 20

    with _demo_api_server() as base_url:
        for site_id in EXTENSION_SITE_IDS:
            status, bootstrap = _get_json(base_url, "/api/bootstrap", {"site_id": site_id})
            assert status == 200
            assert bootstrap["site"]["id"] == site_id
            assert bootstrap["site"]["is_available"] is True
            assert {item["id"] for item in bootstrap["sites"]} == set(ALL_SITE_IDS)
            assert bootstrap["map_renderer"] == "leaflet_geo"
            assert "simple_svg" in bootstrap["map_capabilities"]["renderers"]
            assert bootstrap["map_capabilities"]["fallback_renderer"] == "simple_svg"

            start_node_ids = {item["id"] for item in bootstrap["start_nodes"]}
            route_target_ids = {item["id"] for item in bootstrap["route_targets"]}
            assert bootstrap["default_start_node"] in start_node_ids
            assert {"library", "canteen"} <= route_target_ids
            assert len(bootstrap["users"]) >= 3
            assert len(bootstrap["map_capabilities"]["indoor_supported_buildings"]) >= 5

            controls = bootstrap["controls"]
            assert _option_values(controls["route_strategies"]) == {"shortest_distance", "shortest_time"}
            assert _option_values(controls["transport_modes"]) == {"walk", "bike", "mixed"}
            assert controls["scenic_categories"]
            assert controls["place_categories"]
            assert controls["scenic_sort_options"]
            assert controls["diary_sort_options"]
            assert controls["nearby_radius_options"]
            assert controls["nearby_profiles"]

            presets = bootstrap["presets"]
            for key in ["scenic", "place", "catering", "diary", "route", "multi_route", "aigc"]:
                assert presets[key], f"{site_id} missing {key} presets"

            status, geojson = _get_json(base_url, "/api/map/geojson", {"site_id": site_id})
            assert status == 200
            assert geojson["success"] is True
            assert geojson["site_id"] == site_id
            assert geojson["geojson"]["type"] == "FeatureCollection"
            assert geojson["stats"]["feature_count"] == len(geojson["geojson"]["features"])
            assert geojson["stats"]["node_feature_count"] > 0
            assert geojson["stats"]["edge_feature_count"] > 0

            route_body = {
                "site_id": site_id,
                "start_node_id": bootstrap["default_start_node"],
                "target_node_id": "library",
                "strategy": "shortest_time",
                "transport_mode": "mixed",
            }
            status, route = _post_json(base_url, "/api/route", route_body)
            assert status == 200
            assert route["success"] is True
            assert route["site_id"] == site_id
            assert route["target_node_id"] == "library"
            assert route["ui"]["route_geojson"]["geometry"]["type"] == "LineString"

            status, multi_route = _post_json(
                base_url,
                "/api/route/multi",
                {
                    "site_id": site_id,
                    "start_node_id": bootstrap["default_start_node"],
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
