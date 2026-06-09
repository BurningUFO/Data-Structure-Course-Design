from __future__ import annotations

import json
import math
from pathlib import Path

from src.ui.demo_service import DemoUIService


EXTENSION_BUILDING_SITE_IDS = [
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

M32E_SOURCE = "m32e_extension_building_minimum"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def haversine_m(a: dict[str, object], b: dict[str, object]) -> float:
    lat1 = math.radians(float(a["lat"]))
    lat2 = math.radians(float(b["lat"]))
    d_lat = lat2 - lat1
    d_lng = math.radians(float(b["lng"]) - float(a["lng"]))
    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    )
    return 6371000.0 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def outdoor_payload(site_id: str) -> dict:
    return load_json(Path(f"data/sites/{site_id}/outdoor.json"))


def m32e_buildings(outdoor: dict) -> list[dict]:
    return [
        node
        for node in outdoor["nodes"]
        if node.get("type") == "building" and node.get("source") == M32E_SOURCE
    ]


def test_m32e_extension_outdoor_buildings_reach_course_minimum():
    for site_id in EXTENSION_BUILDING_SITE_IDS:
        outdoor = outdoor_payload(site_id)
        registry = load_json(Path(f"data/sites/{site_id}/geo/indoor_building_registry.json"))[
            "buildings"
        ]
        indoor_supported = set(outdoor["metadata"].get("indoor_supported_buildings", []))
        registry_buildings = {item["building_id"] for item in registry}
        building_nodes = [node for node in outdoor["nodes"] if node.get("type") == "building"]
        added_buildings = m32e_buildings(outdoor)

        assert len(building_nodes) >= 20, site_id
        assert added_buildings, site_id
        assert indoor_supported == registry_buildings
        assert not ({node["id"] for node in added_buildings} & indoor_supported)
        assert outdoor["metadata"].get("indoor_supported_building_count") == 5

        for node in added_buildings:
            location = node["location"]
            assert node["category"] == "building"
            assert node["needs_review"] is True
            assert node["sub_graph_id"] is None
            assert node.get("indoor_supported") is None
            assert node.get("indoor_graph_id") is None
            assert node.get("indoor_entry_node_id") is None
            assert node["tags"]
            assert node["keywords"]
            assert isinstance(float(location["lat"]), float)
            assert isinstance(float(location["lng"]), float)


def test_m32e_extension_buildings_have_bidirectional_poi_access_edges():
    for site_id in EXTENSION_BUILDING_SITE_IDS:
        outdoor = outdoor_payload(site_id)
        nodes_by_id = {node["id"]: node for node in outdoor["nodes"]}
        edge_by_pair = {(edge["from"], edge["to"]): edge for edge in outdoor["edges"]}

        for node in m32e_buildings(outdoor):
            inbound_edges = [
                edge
                for edge in outdoor["edges"]
                if edge.get("to") == node["id"] and edge.get("source") == M32E_SOURCE
            ]
            outbound_edges = [
                edge
                for edge in outdoor["edges"]
                if edge.get("from") == node["id"] and edge.get("source") == M32E_SOURCE
            ]
            assert inbound_edges, (site_id, node["id"])
            assert outbound_edges, (site_id, node["id"])

            for outbound in outbound_edges:
                inbound = edge_by_pair.get((outbound["to"], outbound["from"]))
                assert inbound is not None, (site_id, node["id"], outbound["to"])
                for edge in (outbound, inbound):
                    assert edge["type"] == "poi_access"
                    assert edge["source"] == M32E_SOURCE
                    assert edge["vehicle_access"] == "all"
                    assert edge["allowed_transports"] == ["walk", "bike"]
                    assert edge["transport_speeds"] == {"walk": 1.25, "bike": 3.0}
                    assert edge["transport_semantics"] == "shared_walk_bike"
                    assert edge["congestion"] == 1.0
                    assert edge["ideal_speed"] == 1.25

                anchor = nodes_by_id[outbound["to"]]
                expected_distance = round(
                    haversine_m(node["location"], anchor["location"]),
                    2,
                )
                assert abs(float(outbound["distance"]) - expected_distance) <= 0.01
                assert abs(float(inbound["distance"]) - expected_distance) <= 0.01


def test_m32e_extension_buildings_are_route_targets_geojson_features_and_reachable():
    for site_id in EXTENSION_BUILDING_SITE_IDS:
        service = DemoUIService(site_id)
        bootstrap = service.get_bootstrap_payload()
        geojson_payload = service.get_map_geojson_payload()
        added_building_ids = {node["id"] for node in m32e_buildings(outdoor_payload(site_id))}
        route_target_ids = {item["id"] for item in bootstrap["route_targets"]}
        feature_ids = {
            feature["properties"]["id"]
            for feature in geojson_payload["geojson"]["features"]
            if feature["properties"]["kind"] == "node"
        }

        assert added_building_ids <= route_target_ids
        assert added_building_ids <= feature_ids
        assert bootstrap["map"]["node_count"] == geojson_payload["stats"]["node_feature_count"]
        assert bootstrap["map"]["edge_count"] == geojson_payload["stats"]["edge_feature_count"]
        assert bootstrap["map_capabilities"]["indoor_supported_building_count"] == 5
        assert bootstrap["stats"]["indoor_building_count"] == 5

        for building_id in sorted(added_building_ids)[:2]:
            route = service.plan_route(
                {
                    "start_node_id": bootstrap["default_start_node"],
                    "target_node_id": building_id,
                    "strategy": "shortest_distance",
                    "transport_mode": "walk",
                }
            )
            assert route["success"] is True, (site_id, building_id)
            assert route["target_node_id"] == building_id
            assert route["total_distance_m"] > 0
            assert route["ui"]["route_geojson"]["geometry"]["type"] == "LineString"


def test_m32e_pku_thu_and_template_clone_contracts_do_not_regress():
    pku_bootstrap = DemoUIService("PKU").get_bootstrap_payload()
    thu_bootstrap = DemoUIService("THU").get_bootstrap_payload()
    thu_outdoor = outdoor_payload("THU")
    global_sites = load_json(Path("data/global_sites.json"))["sites"]
    clone_sites = [
        site
        for site in global_sites
        if site.get("data_status") == "template_clone_available"
    ]

    assert pku_bootstrap["map_capabilities"]["indoor_supported_building_count"] >= 20
    assert len([node for node in thu_outdoor["nodes"] if node.get("type") == "building"]) >= 20
    assert thu_bootstrap["map_capabilities"]["indoor_supported_building_count"] == 5
    assert clone_sites
    assert all(not Path(f"data/sites/{site['id']}").exists() for site in clone_sites)
