import json
from pathlib import Path

from src.graph.loader import GraphLoader
from src.routing.router import Router


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
PKU_ROOT = DATA_ROOT / "sites" / "PKU"

REQUIRED_BUILDING_IDS = {
    "library",
    "teaching_building_1",
    "teaching_building_2",
    "dormitory_1",
    "poi_osm_building_way_295071478",
    "poi_osm_building_way_295071692",
    "poi_osm_building_way_295072178",
    "poi_osm_building_way_295073722",
    "poi_osm_building_way_392552195",
    "poi_osm_building_way_392563329",
    "poi_osm_building_way_392563327",
    "poi_osm_education_way_866277614",
    "poi_osm_building_way_866277616",
    "poi_osm_education_node_11135733624",
    "poi_osm_education_way_628032101",
    "poi_osm_sports_way_33457546",
    "poi_osm_sports_way_240832253",
    "poi_osm_catering_way_444894329",
    "poi_osm_catering_way_372945805",
    "poi_osm_catering_way_446944417",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_m17_registry_and_template_catalog_cover_fixed_twenty_buildings():
    registry = load_json(PKU_ROOT / "geo" / "indoor_building_registry.json")["buildings"]
    templates = load_json(PKU_ROOT / "geo" / "indoor_template_catalog.json")["templates"]
    global_sites = load_json(DATA_ROOT / "global_sites.json")["sites"]
    pku_site = next(site for site in global_sites if site["id"] == "PKU")

    assert len(templates) == 5
    assert len(registry) == 20
    assert {item["building_id"] for item in registry} == REQUIRED_BUILDING_IDS

    registry_graph_ids = [item["indoor_graph_id"] for item in registry]
    assert pku_site["sub_graphs"] == ["outdoor", *registry_graph_ids]


def test_m17_indoor_graphs_have_required_floor_facilities_and_single_entry():
    registry = load_json(PKU_ROOT / "geo" / "indoor_building_registry.json")["buildings"]
    outdoor = load_json(PKU_ROOT / "outdoor.json")
    outdoor_nodes = {node["id"]: node for node in outdoor["nodes"]}

    for item in registry:
        graph = load_json(PKU_ROOT / f"{item['indoor_graph_id']}.json")
        floor_ids = item["floor_ids"]
        assert len(floor_ids) >= 2
        assert graph["default_floor_id"] == item["default_floor_id"]
        assert graph["floor_ids"] == floor_ids

        gate_nodes = [node for node in graph["nodes"] if node.get("is_gate")]
        assert len(gate_nodes) == 1

        for floor_id in floor_ids:
            floor_nodes = [node for node in graph["nodes"] if node.get("floor_id") == floor_id]
            assert floor_nodes
            categories = {node.get("category") for node in floor_nodes}
            types = {node.get("type") for node in floor_nodes}

            assert "restroom" in categories
            assert "elevator" in types
            assert "staircase" in types
            assert all("layout" in node and {"x", "y"} <= set(node["layout"]) for node in floor_nodes)

        outdoor_entry = outdoor_nodes[item["entry_node_id"]]
        assert outdoor_entry["is_gate"] is True
        assert outdoor_entry["sub_graph_id"] == item["indoor_graph_id"]


def test_m17_route_scenarios_cover_same_floor_and_cross_floor_indoor_navigation():
    router = Router(GraphLoader.load_site_graph("PKU"))
    scenarios = [
        ("教学楼入口 -> 教室", "teaching_building_1", "tb1_classroom_201", {"elevator"}),
        ("图书馆入口 -> 阅览室", "library", "lib_reading_room_1", set()),
        ("宿舍入口 -> 房间", "dormitory_1", "dorm1_room_201", {"elevator"}),
        ("食堂入口 -> 服务区", "poi_osm_catering_way_444894329", "jiayuan_service_counter_a", set()),
        ("体育馆入口 -> 洗手间", "poi_osm_sports_way_33457546", "qdb_sports_restroom_f2", {"elevator"}),
        ("电梯跨层路径", "library", "lib_digital_room_2f", {"elevator"}),
        ("楼梯跨层路径", "library", "lib_reading_room_2", {"stairs"}),
    ]

    for _, start_node_id, target_node_id, required_edge_types in scenarios:
        result = router.query_routing(start_node_id, target_node_id, site_id="PKU")
        assert result["success"] is True
        assert result["path"][0] == start_node_id
        assert result["path"][-1] == target_node_id
        assert result["route_overview"]["layer_sequence"]
        assert result["path_steps"]

        edge_types = {step["edge_type"] for step in result["path_steps"]}
        for edge_type in required_edge_types:
            assert edge_type in edge_types
