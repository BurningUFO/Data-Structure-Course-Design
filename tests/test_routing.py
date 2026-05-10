import sys
import os
import unittest
import json
from pathlib import Path

# 将 src 目录添加到 Python 路径，方便导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graph.graph import Graph
from src.graph.loader import GraphLoader
from src.routing.router import Router

class TestRouting(unittest.TestCase):
    def setUp(self):
        # 构造包含 10+ 节点和 20+ 边的测试图
        self.graph = Graph(layer_id="test_layer")
        
        # 添加 12 个节点
        for i in range(1, 13):
            self.graph.add_node(f"node_{i}", name=f"Node {i}")
            
        # 添加 20+ 条双向边
        edges = [
            ("node_1", "node_2", 10, 1.0, 1.0),
            ("node_1", "node_3", 15, 1.0, 1.0),
            ("node_2", "node_4", 12, 1.0, 1.0),
            ("node_3", "node_4", 10, 1.0, 1.0),
            ("node_4", "node_5", 5,  1.0, 1.0),
            ("node_2", "node_5", 20, 1.0, 1.0),
            ("node_5", "node_6", 8,  1.0, 1.0),
            ("node_3", "node_6", 25, 1.0, 1.0),
            ("node_6", "node_7", 14, 1.0, 1.0),
            ("node_5", "node_7", 18, 1.0, 1.0),
            ("node_7", "node_8", 9,  1.0, 1.0),
            ("node_6", "node_8", 22, 1.0, 1.0),
            ("node_8", "node_9", 11, 1.0, 1.0),
            ("node_7", "node_9", 16, 1.0, 1.0),
            ("node_9", "node_10", 7, 1.0, 1.0),
            ("node_8", "node_10", 19, 1.0, 1.0),
            ("node_10", "node_11", 13, 1.0, 1.0),
            ("node_9", "node_11", 21, 1.0, 1.0),
            ("node_11", "node_12", 5, 1.0, 1.0),
            # 测试拥堵极度严重的边
            ("node_1", "node_12", 50, 0.1, 1.0)
        ]
        
        for u, v, dist, congestion, speed in edges:
            self.graph.add_edge(u, v, distance=dist, congestion=congestion, ideal_speed=speed)
            self.graph.add_edge(v, u, distance=dist, congestion=congestion, ideal_speed=speed)
            
        self.router = Router(self.graph)

    def test_shortest_distance(self):
        # 验证最短距离策略
        # 从 1 到 5：路径 1 -> 2 (10) -> 4 (12) -> 5 (5) = 27
        dist = self.router.query_distance("node_1", "node_5", strategy="shortest_distance")
        self.assertEqual(dist, 27)
        
        res = self.router.query_routing("node_1", "node_5", strategy="shortest_distance")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["node_1", "node_2", "node_4", "node_5"])

    def test_shortest_time_with_congestion(self):
        # 验证最短时间策略 (动态权重)
        # 增加一条旁路：距离长，但是理想速度极快（如可骑车且不拥堵）
        self.graph.add_node("node_bypass")
        # 距离 40，速度 4.0，时间 = 10
        self.graph.add_edge("node_1", "node_bypass", distance=40, congestion=1.0, ideal_speed=4.0) 
        self.graph.add_edge("node_bypass", "node_5", distance=40, congestion=1.0, ideal_speed=4.0) 
        
        # 1->2->4->5: 距离 27，时间 27
        # 1->bypass->5: 距离 80，时间 20
        
        # 最短距离策略应该依然走旧路
        dist = self.router.query_distance("node_1", "node_5", strategy="shortest_distance")
        self.assertEqual(dist, 27)
        
        # 最短时间策略应该走旁路
        time = self.router.query_distance("node_1", "node_5", strategy="shortest_time")
        self.assertEqual(time, 20)
        
        res = self.router.query_routing("node_1", "node_5", strategy="shortest_time")
        self.assertEqual(res["path"], ["node_1", "node_bypass", "node_5"])

    def test_unreachable_node(self):
        # 验证不可达节点的处理
        self.graph.add_node("isolated_node")
        dist = self.router.query_distance("node_1", "isolated_node")
        self.assertEqual(dist, float('inf'))
        
        res = self.router.query_routing("node_1", "isolated_node")
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "无法从起点到达终点。")

    def test_transport_mode_filter(self):
        # 添加一条仅允许自行车通过的快速边
        self.graph.add_edge(
            "node_1",
            "node_5",
            distance=5,
            congestion=1.0,
            ideal_speed=1.0,
            allowed_transports=["bike"],
        )
        self.graph.add_edge(
            "node_5",
            "node_1",
            distance=5,
            congestion=1.0,
            ideal_speed=1.0,
            allowed_transports=["bike"],
        )

        # 步行不应使用仅限自行车的边
        walk_distance = self.router.query_distance(
            "node_1",
            "node_5",
            strategy="shortest_distance",
            transport_mode="walk",
        )
        self.assertEqual(walk_distance, 27)

        # 自行车可以直接走快速边
        bike_distance = self.router.query_distance(
            "node_1",
            "node_5",
            strategy="shortest_distance",
            transport_mode="bike",
        )
        self.assertEqual(bike_distance, 5)

        bike_route = self.router.query_routing(
            "node_1",
            "node_5",
            strategy="shortest_distance",
            transport_mode="bike",
        )
        self.assertTrue(bike_route["success"])
        self.assertEqual(bike_route["path"], ["node_1", "node_5"])
        self.assertEqual(bike_route["transport_mode"], "bike")

    def test_vehicle_access_filter_for_walk_and_car(self):
        graph = Graph(layer_id="transport_demo")
        for node_id in ["start", "ped_zone", "parking", "finish"]:
            graph.add_node(node_id, name=node_id)

        graph.add_edge("start", "ped_zone", distance=1, vehicle_access="pedestrian_only")
        graph.add_edge("ped_zone", "finish", distance=1, vehicle_access="pedestrian_only")
        graph.add_edge("start", "parking", distance=5, vehicle_access="vehicle_only")
        graph.add_edge("parking", "finish", distance=5, vehicle_access="vehicle_only")

        router = Router(graph)
        walk_route = router.query_routing("start", "finish", transport_mode="walk")
        car_route = router.query_routing("start", "finish", transport_mode="car")

        self.assertTrue(walk_route["success"])
        self.assertEqual(walk_route["path"], ["start", "ped_zone", "finish"])
        self.assertEqual(walk_route["total_distance_m"], 2)

        self.assertTrue(car_route["success"])
        self.assertEqual(car_route["path"], ["start", "parking", "finish"])
        self.assertEqual(car_route["total_distance_m"], 10)

    def test_multi_target_routing(self):
        graph = Graph(layer_id="multi_target")
        for node_id in ["start", "a", "b", "c"]:
            graph.add_node(node_id, name=node_id)

        directed_edges = [
            ("start", "a", 2),
            ("a", "start", 2),
            ("start", "b", 8),
            ("b", "start", 6),
            ("start", "c", 20),
            ("c", "start", 1),
            ("a", "b", 2),
            ("b", "a", 2),
            ("b", "c", 2),
            ("c", "b", 2),
            ("a", "c", 10),
            ("c", "a", 10),
        ]

        for u, v, dist in directed_edges:
            graph.add_edge(u, v, distance=dist, congestion=1.0, ideal_speed=1.0)

        router = Router(graph)
        result = router.query_multi_target(
            "start",
            ["a", "c"],
            strategy="shortest_distance",
            return_to_start=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["visit_order"], ["start", "a", "c", "start"])
        self.assertEqual(result["path"], ["start", "a", "b", "c", "start"])
        self.assertEqual(result["total_weight"], 7)
        self.assertEqual(result["total_distance_m"], 7)
        self.assertEqual(result["estimated_time_s"], 7)
        self.assertEqual(result["total_distance"], 7)
        self.assertEqual(result["estimated_time"], 7)
        self.assertEqual(len(result["leg_results"]), 3)
        self.assertEqual(result["leg_results"][0]["weight_unit"], "meter")
        self.assertEqual(result["leg_results"][0]["total_distance_m"], 2)
        self.assertEqual(result["visit_order_names"], ["start", "a", "c", "start"])
        self.assertEqual(result["path_node_names"], ["start", "a", "b", "c", "start"])
        self.assertEqual(result["leg_results"][0]["route_overview"]["target_node_id"], "a")
        self.assertEqual(result["leg_results"][0]["path_steps"][0]["to_node_id"], "a")

    def test_multi_target_empty_targets_returns_start_only(self):
        graph = Graph(layer_id="multi_target_empty")
        graph.add_node("start", name="start")

        router = Router(graph)
        result = router.query_multi_target("start", [], return_to_start=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["start"])
        self.assertEqual(result["visit_order"], ["start"])
        self.assertEqual(result["path_node_names"], ["start"])
        self.assertEqual(result["visit_order_names"], ["start"])
        self.assertEqual(result["target_node_ids"], [])
        self.assertEqual(result["total_weight"], 0)
        self.assertEqual(result["leg_results"], [])

    def test_multi_target_ignores_duplicate_targets_and_start_node(self):
        graph = Graph(layer_id="multi_target_duplicate")
        for node_id in ["start", "a", "b"]:
            graph.add_node(node_id, name=node_id)

        graph.add_edge("start", "a", distance=2, congestion=1.0, ideal_speed=1.0)
        graph.add_edge("a", "start", distance=2, congestion=1.0, ideal_speed=1.0)
        graph.add_edge("a", "b", distance=3, congestion=1.0, ideal_speed=1.0)
        graph.add_edge("b", "a", distance=3, congestion=1.0, ideal_speed=1.0)

        router = Router(graph)
        result = router.query_multi_target(
            "start",
            ["a", "a", "start", "b"],
            return_to_start=False,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["target_node_ids"], ["a", "b"])
        self.assertEqual(result["visit_order"], ["start", "a", "b"])
        self.assertEqual(result["path"], ["start", "a", "b"])
        self.assertEqual(result["total_distance_m"], 5)

    def test_multi_target_unreachable_target_returns_failure(self):
        graph = Graph(layer_id="multi_target_unreachable")
        for node_id in ["start", "a", "isolated"]:
            graph.add_node(node_id, name=node_id)

        graph.add_edge("start", "a", distance=2, congestion=1.0, ideal_speed=1.0)
        graph.add_edge("a", "start", distance=2, congestion=1.0, ideal_speed=1.0)

        router = Router(graph)
        result = router.query_multi_target("start", ["a", "isolated"])

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "无法找到覆盖所有目标点的可行路径。")

    def test_multi_target_rejects_more_than_twelve_targets(self):
        graph = Graph(layer_id="multi_target_limit")
        graph.add_node("start", name="start")
        targets = [f"target_{index}" for index in range(13)]
        for target in targets:
            graph.add_node(target, name=target)
            graph.add_edge("start", target, distance=1, congestion=1.0, ideal_speed=1.0)
            graph.add_edge(target, "start", distance=1, congestion=1.0, ideal_speed=1.0)

        router = Router(graph)
        result = router.query_multi_target("start", targets)

        self.assertFalse(result["success"])
        self.assertIn("12 个及以下目标点", result["message"])

    def test_standard_site_distance_with_optional_site_id(self):
        router = Router(GraphLoader.load_site_graph("PKU"))

        default_distance = router.query_distance("gate_north", "library")
        scoped_distance = router.query_distance("gate_north", "library", site_id="PKU")
        route = router.query_routing("gate_north", "library", site_id="PKU")

        self.assertEqual(default_distance, 110)
        self.assertEqual(scoped_distance, 110)
        self.assertTrue(route["success"])
        self.assertEqual(route["site_id"], "PKU")
        self.assertEqual(route["path"], ["gate_north", "square_center", "library"])
        self.assertEqual(route["weight_unit"], "meter")
        self.assertEqual(route["total_distance_m"], 110)
        self.assertAlmostEqual(route["estimated_time_s"], (80 / (1.5 * 0.6)) + (30 / (1.5 * 0.4)))
        self.assertEqual(route["segments"][0]["layer"], "outdoor")
        self.assertEqual(route["start_node_name"], "北大西门")
        self.assertEqual(route["target_node_name"], "图书馆")
        self.assertEqual(route["path_node_names"], ["北大西门", "百周年纪念广场", "图书馆"])
        self.assertEqual(route["layer_sequence"], ["outdoor"])
        self.assertEqual(route["route_overview"]["segment_count"], 1)
        self.assertFalse(route["route_overview"]["cross_layer"])
        self.assertEqual(route["route_overview"]["node_count"], 3)
        self.assertEqual(route["path_steps"][0]["edge_name"], "西门大道")
        self.assertEqual(route["path_steps"][1]["edge_name"], "图书馆前广场")
        self.assertEqual(route["segments"][0]["edge_names"], ["西门大道", "图书馆前广场"])
        self.assertEqual(route["segments"][0]["target_node_name"], "图书馆")

    def test_standard_site_single_route_frozen_display_fields(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing(
            "gate_north",
            "lib_reading_room_1",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="PKU",
        )

        required_top_level_fields = {
            "success",
            "site_id",
            "start_node_id",
            "target_node_id",
            "start_node_name",
            "target_node_name",
            "path",
            "path_node_names",
            "total_weight",
            "weight_unit",
            "total_distance_m",
            "estimated_time_s",
            "total_distance",
            "estimated_time",
            "strategy",
            "transport_mode",
            "layer_sequence",
            "route_overview",
            "path_steps",
            "segments",
        }

        self.assertTrue(route["success"])
        self.assertTrue(required_top_level_fields.issubset(route.keys()))
        self.assertEqual(route["site_id"], "PKU")
        self.assertEqual(route["strategy"], "shortest_time")
        self.assertEqual(route["transport_mode"], "walk")
        self.assertEqual(route["weight_unit"], "second")
        self.assertEqual(route["total_distance"], route["total_distance_m"])
        self.assertEqual(route["estimated_time"], route["estimated_time_s"])
        self.assertEqual(len(route["path"]), len(route["path_node_names"]))
        self.assertEqual(route["route_overview"]["start_node_name"], route["start_node_name"])
        self.assertEqual(route["route_overview"]["target_node_name"], route["target_node_name"])
        self.assertEqual(route["route_overview"]["transport_mode"], "walk")
        self.assertTrue(route["route_overview"]["cross_layer"])
        self.assertGreaterEqual(len(route["path_steps"]), 1)
        self.assertGreaterEqual(len(route["segments"]), 2)
        self.assertIn("from_node_name", route["path_steps"][0])
        self.assertIn("to_node_name", route["path_steps"][0])
        self.assertIn("distance_m", route["path_steps"][0])
        self.assertIn("estimated_time_s", route["path_steps"][0])

    def test_site_id_mismatch_is_rejected(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing("gate_north", "library", site_id="THU")

        self.assertFalse(route["success"])
        self.assertIn("site_id 不匹配", route["message"])

    def test_shortest_time_uses_seconds_and_supports_cross_layer_path(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing(
            "gate_north",
            "lib_reading_room_1",
            strategy="shortest_time",
            site_id="PKU",
        )

        expected_time = (
            (80 / (1.5 * 0.6))
            + (30 / (1.5 * 0.4))
            + (25 / (1.5 * 0.4))
        )

        self.assertTrue(route["success"])
        self.assertEqual(route["path"], ["gate_north", "square_center", "library", "lib_entrance", "lib_reading_room_1"])
        self.assertEqual(route["weight_unit"], "second")
        self.assertEqual(route["total_distance_m"], 135)
        self.assertAlmostEqual(route["total_weight"], expected_time)
        self.assertAlmostEqual(route["estimated_time_s"], expected_time)
        self.assertEqual([segment["layer"] for segment in route["segments"]], ["outdoor", "indoor_LIB"])
        self.assertEqual(route["path_node_names"], ["北大西门", "百周年纪念广场", "图书馆", "图书馆入口大厅", "中文社科阅览室"])
        self.assertTrue(route["route_overview"]["cross_layer"])
        self.assertEqual(route["route_overview"]["cross_layer_step_count"], 1)
        self.assertEqual(route["route_overview"]["layer_sequence"], ["outdoor", "indoor_LIB"])
        self.assertEqual(route["path_steps"][2]["edge_type"], "gate_link")
        self.assertTrue(route["path_steps"][2]["is_gate_transition"])
        self.assertEqual(route["path_steps"][2]["transition_kind"], "cross_layer")
        self.assertEqual(route["segments"][1]["start_node_name"], "图书馆")
        self.assertEqual(route["segments"][1]["target_node_name"], "中文社科阅览室")
        self.assertIn("gate_link", route["segments"][1]["edge_types"])

    def test_standard_site_strategy_comparison_uses_real_graph(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        distance_route = router.query_routing("gate_north", "lib_reception", strategy="shortest_distance")
        time_route = router.query_routing("gate_north", "lib_reception", strategy="shortest_time")

        self.assertTrue(distance_route["success"])
        self.assertTrue(time_route["success"])
        self.assertEqual(distance_route["path"], ["gate_north", "square_center", "library", "lib_entrance", "lib_reception"])
        self.assertEqual(time_route["path"], ["gate_north", "square_center", "library", "lib_entrance", "lib_self_serve", "lib_reception"])
        self.assertEqual(distance_route["weight_unit"], "meter")
        self.assertEqual(time_route["weight_unit"], "second")
        self.assertEqual(distance_route["route_overview"]["target_node_name"], "总服务台")
        self.assertEqual(time_route["path_steps"][-1]["edge_name"], "")
        self.assertEqual(time_route["path_steps"][-1]["description"], "服务台旁的自助区")
        self.assertGreater(time_route["route_overview"]["edge_count"], distance_route["route_overview"]["edge_count"])

    def test_standard_site_transport_filter_blocks_incompatible_modes(self):
        router = Router(GraphLoader.load_site_graph("PKU"))

        walk_to_parking = router.query_routing("gate_north", "parking_lot", transport_mode="walk")
        car_to_library = router.query_routing("gate_north", "library", transport_mode="car")
        car_to_parking = router.query_routing("gate_east", "parking_lot", transport_mode="car")

        self.assertFalse(walk_to_parking["success"])
        self.assertFalse(car_to_library["success"])
        self.assertTrue(car_to_parking["success"])
        self.assertEqual(car_to_parking["path"], ["gate_east", "parking_lot"])
        self.assertEqual(car_to_parking["path_steps"][0]["vehicle_access"], "vehicle_only")
        self.assertEqual(car_to_parking["route_overview"]["transport_mode"], "car")

    def test_standard_site_multi_target_frozen_display_fields(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_multi_target(
            "gate_north",
            ["library", "canteen", "convenience_store"],
            strategy="shortest_distance",
            transport_mode="walk",
            return_to_start=True,
            site_id="PKU",
        )

        required_top_level_fields = {
            "success",
            "site_id",
            "path",
            "path_node_names",
            "visit_order",
            "visit_order_names",
            "target_node_ids",
            "total_weight",
            "weight_unit",
            "total_distance_m",
            "estimated_time_s",
            "total_distance",
            "estimated_time",
            "strategy",
            "transport_mode",
            "return_to_start",
            "segments",
            "leg_results",
        }

        self.assertTrue(route["success"])
        self.assertTrue(required_top_level_fields.issubset(route.keys()))
        self.assertEqual(route["site_id"], "PKU")
        self.assertEqual(route["strategy"], "shortest_distance")
        self.assertEqual(route["transport_mode"], "walk")
        self.assertTrue(route["return_to_start"])
        self.assertEqual(route["weight_unit"], "meter")
        self.assertEqual(route["visit_order"][0], "gate_north")
        self.assertEqual(route["visit_order"][-1], "gate_north")
        self.assertEqual(len(route["visit_order"]), len(route["visit_order_names"]))
        self.assertEqual(len(route["path"]), len(route["path_node_names"]))
        self.assertEqual(route["target_node_ids"], ["library", "canteen", "convenience_store"])
        self.assertEqual(len(route["leg_results"]), 4)
        self.assertEqual(route["total_distance"], route["total_distance_m"])
        self.assertEqual(route["estimated_time"], route["estimated_time_s"])
        self.assertAlmostEqual(
            route["total_distance_m"],
            sum(leg["total_distance_m"] for leg in route["leg_results"]),
        )
        self.assertAlmostEqual(
            route["estimated_time_s"],
            sum(leg["estimated_time_s"] for leg in route["leg_results"]),
        )

        first_leg = route["leg_results"][0]
        self.assertIn("path_node_names", first_leg)
        self.assertIn("path_steps", first_leg)
        self.assertIn("route_overview", first_leg)
        self.assertIn("segments", first_leg)
        self.assertEqual(first_leg["start_node_name"], "北大西门")
        self.assertEqual(first_leg["route_overview"]["start_node_id"], first_leg["start_node_id"])

    def test_diary_destination_node_can_route_with_summary_fields(self):
        diary_path = Path(__file__).resolve().parents[1] / "data" / "diary_data.json"
        with diary_path.open("r", encoding="utf-8") as f:
            diaries = json.load(f)

        diary = next(item for item in diaries if item.get("destination_node_id") == "canteen")
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing("gate_north", diary["destination_node_id"])

        self.assertTrue(route["success"])
        self.assertEqual(route["target_node_id"], "canteen")
        self.assertEqual(route["target_node_name"], "农园食堂")
        self.assertEqual(route["route_overview"]["target_node_name"], "农园食堂")
        self.assertEqual(route["path"][-1], diary["destination_node_id"])
        self.assertEqual(route["path_node_names"][-1], "农园食堂")

if __name__ == '__main__':
    unittest.main()
