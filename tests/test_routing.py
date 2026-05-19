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

        self.assertGreater(default_distance, 0)
        self.assertEqual(scoped_distance, default_distance)
        self.assertTrue(route["success"])
        self.assertEqual(route["path"][0], "gate_north")
        self.assertEqual(route["path"][-1], "library")

    def test_standard_site_single_route_frozen_display_fields(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing(
            "library",
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
        self.assertEqual(route["start_node_id"], "library")
        self.assertEqual(route["path"], ["library", "lib_entrance", "lib_reading_room_1"])
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
        self.assertGreaterEqual(len(route["segments"]), 1)
        self.assertEqual(route["segments"][0]["layer"], "indoor_LIB")
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
            "library",
            "lib_reading_room_1",
            strategy="shortest_time",
            site_id="PKU",
        )

        self.assertTrue(route["success"])
        self.assertEqual(route["path"][0], "library")
        self.assertEqual(route["path"][-2:], ["lib_entrance", "lib_reading_room_1"])
        self.assertEqual(route["weight_unit"], "second")
        self.assertEqual(route["total_distance_m"], 25)
        self.assertAlmostEqual(route["total_weight"], route["estimated_time_s"])
        self.assertEqual([segment["layer"] for segment in route["segments"]], ["indoor_LIB"])
        self.assertEqual(route["path_node_names"][0], "图书馆")
        self.assertEqual(route["path_node_names"][-1], "中文社科阅览室")
        self.assertTrue(route["route_overview"]["cross_layer"])
        self.assertEqual(route["route_overview"]["cross_layer_step_count"], 1)
        self.assertEqual(route["route_overview"]["layer_sequence"], ["indoor_LIB"])
        gate_step = next(step for step in route["path_steps"] if step["edge_type"] == "gate_link")
        self.assertTrue(gate_step["is_gate_transition"])
        self.assertEqual(gate_step["transition_kind"], "cross_layer")
        self.assertEqual(route["segments"][0]["start_node_name"], "图书馆")
        self.assertEqual(route["segments"][0]["target_node_name"], "中文社科阅览室")
        self.assertIn("gate_link", route["segments"][0]["edge_types"])

    def test_same_indoor_graph_cross_floor_uses_floor_metadata(self):
        graph = Graph(layer_id="PKU")
        graph.add_node("building_entry", name="测试教学楼", source_sub_graph_id="outdoor")
        graph.add_node(
            "indoor_gate_f1",
            name="教学楼入口",
            source_sub_graph_id="indoor_TEST",
            floor_id="F1",
            floor_label="1F",
        )
        graph.add_node(
            "stairs_f1",
            name="一层楼梯间",
            source_sub_graph_id="indoor_TEST",
            floor_id="F1",
            floor_label="1F",
        )
        graph.add_node(
            "stairs_f2",
            name="二层楼梯间",
            source_sub_graph_id="indoor_TEST",
            floor_id="F2",
            floor_label="2F",
        )
        graph.add_node(
            "classroom_f2",
            name="201 教室",
            source_sub_graph_id="indoor_TEST",
            floor_id="F2",
            floor_label="2F",
        )

        directed_edges = [
            ("building_entry", "indoor_gate_f1", 0, "gate_link"),
            ("indoor_gate_f1", "building_entry", 0, "gate_link"),
            ("indoor_gate_f1", "stairs_f1", 8, "indoor_path"),
            ("stairs_f1", "indoor_gate_f1", 8, "indoor_path"),
            ("stairs_f1", "stairs_f2", 6, "stairs"),
            ("stairs_f2", "stairs_f1", 6, "stairs"),
            ("stairs_f2", "classroom_f2", 10, "indoor_path"),
            ("classroom_f2", "stairs_f2", 10, "indoor_path"),
        ]
        for source_id, target_id, distance, edge_type in directed_edges:
            graph.add_edge(
                source_id,
                target_id,
                distance=distance,
                congestion=1.0,
                ideal_speed=1.0,
                type=edge_type,
            )

        router = Router(graph)
        route = router.query_routing("building_entry", "classroom_f2")

        self.assertTrue(route["success"])
        self.assertEqual(
            route["path"],
            ["building_entry", "indoor_gate_f1", "stairs_f1", "stairs_f2", "classroom_f2"],
        )
        self.assertTrue(route["route_overview"]["cross_layer"])
        self.assertEqual(route["route_overview"]["cross_floor_step_count"], 1)
        self.assertEqual(route["route_overview"]["layer_sequence"], ["indoor_TEST", "indoor_TEST"])
        self.assertEqual(route["route_overview"]["floor_sequence"], ["1F", "2F"])
        self.assertEqual(
            [segment["floor_id"] for segment in route["segments"]],
            ["F1", "F2"],
        )
        stairs_step = next(step for step in route["path_steps"] if step["edge_type"] == "stairs")
        self.assertEqual(stairs_step["from_layer"], "indoor_TEST")
        self.assertEqual(stairs_step["to_layer"], "indoor_TEST")
        self.assertEqual(stairs_step["from_floor_id"], "F1")
        self.assertEqual(stairs_step["to_floor_id"], "F2")
        self.assertEqual(stairs_step["display_layer"], "2F")
        self.assertTrue(stairs_step["is_cross_floor_transition"])
        self.assertEqual(stairs_step["transition_kind"], "cross_layer")

    def test_m14_white_road_outdoor_graph_has_route_edges(self):
        graph = GraphLoader.load_site_graph("PKU")
        router = Router(graph)
        outdoor_node_ids = {
            node_id
            for node_id, attrs in graph.nodes.items()
            if attrs.get("source_sub_graph_id") == "outdoor"
        }
        outdoor_edges = [
            (source_id, edge["to"])
            for source_id, edges in graph.adj.items()
            for edge in edges
            if source_id in outdoor_node_ids
            and edge["to"] in outdoor_node_ids
            and edge.get("type") != "gate_link"
        ]

        self.assertGreater(len(outdoor_edges), 0)
        self.assertIn("road_access_gate_north", graph.nodes)
        self.assertEqual(graph.nodes["gate_north"]["route_anchor_node_id"], "road_access_gate_north")
        for start_node_id, target_node_id in (
            ("gate_south", "teaching_building_1"),
            ("gate_north", "canteen"),
        ):
            route = router.query_routing(start_node_id, target_node_id, site_id="PKU")
            self.assertTrue(route["success"])
            self.assertIn(f"road_access_{start_node_id}", route["path"])
            self.assertIn(f"road_access_{target_node_id}", route["path"])
            self.assertTrue(any(node_id.startswith("road_white_") for node_id in route["path"]))

    def test_standard_site_strategy_comparison_uses_real_graph(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        distance_route = router.query_routing("library", "lib_reception", strategy="shortest_distance")
        time_route = router.query_routing("library", "lib_reception", strategy="shortest_time")

        self.assertTrue(distance_route["success"])
        self.assertTrue(time_route["success"])
        self.assertEqual(distance_route["path"][0], "library")
        self.assertEqual(distance_route["path"][-2:], ["lib_entrance", "lib_reception"])
        self.assertEqual(time_route["path"][0], "library")
        self.assertEqual(time_route["path"][-3:], ["lib_entrance", "lib_self_serve", "lib_reception"])
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

        self.assertTrue(walk_to_parking["success"])
        self.assertFalse(car_to_library["success"])
        self.assertFalse(car_to_parking["success"])
        self.assertEqual(car_to_library["message"], "无法从起点到达终点。")
        self.assertEqual(car_to_parking["message"], "无法从起点到达终点。")

    def test_m21_pku_walk_bike_and_mixed_time_scenarios(self):
        router = Router(GraphLoader.load_site_graph("PKU"))

        walk_better = router.query_routing(
            "gate_east",
            "parking_lot",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="PKU",
        )
        bike_detour = router.query_routing(
            "gate_east",
            "parking_lot",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="PKU",
        )
        self.assertTrue(walk_better["success"])
        self.assertTrue(bike_detour["success"])
        self.assertLess(walk_better["total_weight"], bike_detour["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in walk_better["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in bike_detour["path_steps"]},
            {"bike"},
        )

        walk_sports = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="PKU",
        )
        bike_sports = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="PKU",
        )
        mixed_sports = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="PKU",
        )
        self.assertTrue(walk_sports["success"])
        self.assertTrue(bike_sports["success"])
        self.assertTrue(mixed_sports["success"])
        self.assertLess(bike_sports["total_weight"], walk_sports["total_weight"])
        self.assertLess(mixed_sports["total_weight"], bike_sports["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in mixed_sports["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m21_pku_mixed_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("PKU"))

        outdoor_to_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_1",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="PKU",
        )
        pure_indoor = router.query_routing(
            "library",
            "lib_reading_room_1",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="PKU",
        )
        bike_indoor = router.query_routing(
            "library",
            "lib_reading_room_1",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="PKU",
        )

        self.assertTrue(outdoor_to_indoor["success"])
        self.assertIn("bike", [step["transport_mode_used"] for step in outdoor_to_indoor["path_steps"]])
        indoor_steps = [
            step for step in outdoor_to_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

        self.assertTrue(pure_indoor["success"])
        self.assertEqual(pure_indoor["path"], ["library", "lib_entrance", "lib_reading_room_1"])
        self.assertEqual(
            {step["transport_mode_used"] for step in pure_indoor["path_steps"]},
            {"walk"},
        )

        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")

    def test_m21_pku_outdoor_data_declares_walk_bike_edge_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "PKU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        pedestrian_edges = [
            edge for edge in edges
            if edge.get("vehicle_access") == "pedestrian_only"
        ]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m21_transport_demo"
        ]

        self.assertGreater(len(pedestrian_edges), 0)
        self.assertGreaterEqual(len(shared_edges), 40)
        self.assertEqual(len(bike_only_edges), 8)
        self.assertTrue(any(edge["type"] == "bike_lane" for edge in bike_only_edges))

    def test_m31a_thu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("THU"))

        walk_to_main = router.query_routing(
            "gate_east",
            "main_building",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="THU",
        )
        bike_to_main = router.query_routing(
            "gate_east",
            "main_building",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="THU",
        )
        self.assertTrue(walk_to_main["success"])
        self.assertTrue(bike_to_main["success"])
        self.assertLess(walk_to_main["total_weight"], bike_to_main["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in walk_to_main["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in bike_to_main["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in bike_to_main["path_steps"])
        )

        west_to_north_walk = router.query_routing(
            "gate_west",
            "gate_north",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="THU",
        )
        west_to_north_bike = router.query_routing(
            "gate_west",
            "gate_north",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="THU",
        )
        self.assertTrue(west_to_north_walk["success"])
        self.assertTrue(west_to_north_bike["success"])
        self.assertLess(west_to_north_bike["total_weight"], west_to_north_walk["total_weight"])

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="THU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="THU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="THU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_thu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("THU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="THU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="THU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_thu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "THU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_thu_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_THU")
        self.assertGreaterEqual(len(shared_edges), 20)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(
            all("清华" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_whu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("WHU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="WHU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="WHU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="WHU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_walk["total_weight"], west_to_service_bike["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_service_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="WHU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="WHU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="WHU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_whu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("WHU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="WHU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="WHU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_whu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "WHU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_whu_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_WHU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertGreaterEqual(len(shared_edges), 40)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(all(edge.get("transport_semantics") for edge in edges))
        self.assertTrue(
            all("武汉大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_xmu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("XMU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="XMU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="XMU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="XMU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_walk["total_weight"], west_to_service_bike["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_service_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="XMU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="XMU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="XMU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_xmu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("XMU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="XMU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="XMU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_xmu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "XMU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_xmu_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_XMU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertGreaterEqual(len(shared_edges), 45)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(all(edge.get("transport_semantics") for edge in edges))
        self.assertTrue(
            all("厦门大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_zju_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("ZJU"))

        west_to_teaching_walk = router.query_routing(
            "gate_west",
            "teaching_building_2",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="ZJU",
        )
        west_to_teaching_bike = router.query_routing(
            "gate_west",
            "teaching_building_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="ZJU",
        )
        west_to_teaching_mixed = router.query_routing(
            "gate_west",
            "teaching_building_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="ZJU",
        )
        self.assertTrue(west_to_teaching_walk["success"])
        self.assertTrue(west_to_teaching_bike["success"])
        self.assertTrue(west_to_teaching_mixed["success"])
        self.assertLess(west_to_teaching_walk["total_weight"], west_to_teaching_bike["total_weight"])
        self.assertLess(west_to_teaching_mixed["total_weight"], west_to_teaching_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_teaching_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_teaching_bike["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_teaching_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="ZJU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="ZJU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="ZJU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_zju_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("ZJU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="ZJU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="ZJU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_zju_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "ZJU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_zju_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_ZJU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertGreaterEqual(len(shared_edges), 60)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(all(edge.get("transport_semantics") for edge in edges))
        self.assertTrue(
            all("浙江大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_nju_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("NJU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="NJU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="NJU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="NJU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_walk["total_weight"], west_to_service_bike["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_service_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="NJU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="NJU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="NJU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_nju_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("NJU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="NJU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="NJU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_nju_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "NJU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_nju_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_NJU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertGreaterEqual(len(shared_edges), 40)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(all(edge.get("transport_semantics") for edge in edges))
        self.assertTrue(
            all("南京大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_fdu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("FDU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="FDU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="FDU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="FDU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_walk["total_weight"], west_to_service_bike["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_service_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="FDU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="FDU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="FDU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")

    def test_m31a_fdu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("FDU"))

        mixed_indoor = router.query_routing(
            "gate_north",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="FDU",
        )
        bike_indoor = router.query_routing(
            "gate_north",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="FDU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_fdu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "FDU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_only_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_fdu_transport_calibration"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_FDU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertGreaterEqual(len(shared_edges), 40)
        self.assertEqual(len(bike_only_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(all(edge.get("transport_semantics") for edge in edges))
        self.assertTrue(
            all("复旦大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_only_edges)
        )

    def test_m31a_sjtu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("SJTU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SJTU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SJTU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SJTU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_walk["total_weight"], west_to_service_bike["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_walk["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(west_to_service_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("西门非机动车绕行接驳", west_to_service_bike["path_steps"][0]["edge_name"])
        self.assertEqual(west_to_service_mixed["path_steps"][0]["transport_mode_used"], "walk")
        self.assertIn("西门步行短接", west_to_service_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any(step["edge_type"] == "bike_lane" for step in west_to_service_bike["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SJTU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SJTU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SJTU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_sports_bike["path_steps"][0]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertIn("南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])

    def test_m31a_sjtu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("SJTU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SJTU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SJTU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_sjtu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "SJTU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_sjtu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") in {
                "sjtu_west_gate_bike_detour",
                "sjtu_south_gate_bike_detour",
            }
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_SJTU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 10)
        self.assertEqual(len(bike_calibration_edges), 8)
        self.assertEqual(len(bike_gate_detour_edges), 4)
        self.assertEqual(len(bike_poi_connector_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("上海交通大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("步行短接" in edge.get("description", "") for edge in pedestrian_gate_edges)
        )

    def test_m31a_tongji_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("TONGJI"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="TONGJI",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="TONGJI",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="TONGJI",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_bike["total_weight"], west_to_service_walk["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_bike["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(west_to_service_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("西门非机动车绕行接驳", west_to_service_bike["path_steps"][0]["edge_name"])
        self.assertEqual(west_to_service_mixed["path_steps"][0]["transport_mode_used"], "walk")
        self.assertIn("西门步行短接", west_to_service_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any("同济大学四平路校区步骑共享主路" in step["description"] for step in west_to_service_mixed["path_steps"])
        )

        south_to_teaching_walk = router.query_routing(
            "gate_south",
            "teaching_building",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="TONGJI",
        )
        south_to_teaching_bike = router.query_routing(
            "gate_south",
            "teaching_building",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="TONGJI",
        )
        south_to_teaching_mixed = router.query_routing(
            "gate_south",
            "teaching_building",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="TONGJI",
        )
        self.assertTrue(south_to_teaching_walk["success"])
        self.assertTrue(south_to_teaching_bike["success"])
        self.assertTrue(south_to_teaching_mixed["success"])
        self.assertLess(south_to_teaching_bike["total_weight"], south_to_teaching_walk["total_weight"])
        self.assertLess(south_to_teaching_mixed["total_weight"], south_to_teaching_bike["total_weight"])
        self.assertEqual(south_to_teaching_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_teaching_bike["path_steps"][0]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_teaching_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertIn("南门步行短接", south_to_teaching_mixed["path_steps"][0]["description"])

    def test_m31a_tongji_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("TONGJI"))

        mixed_indoor = router.query_routing(
            "gate_west",
            "tb1_classroom_101",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="TONGJI",
        )
        bike_indoor = router.query_routing(
            "gate_west",
            "tb1_classroom_101",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="TONGJI",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_tongji_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "TONGJI" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if set(edge.get("allowed_transports", [])) == {"walk", "bike"}
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_tongji_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") in {
                "tongji_west_gate_bike_detour",
                "tongji_south_gate_bike_detour",
            }
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_TONGJI")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 10)
        self.assertEqual(len(bike_calibration_edges), 8)
        self.assertEqual(len(bike_gate_detour_edges), 4)
        self.assertEqual(len(bike_poi_connector_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("同济大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )
        self.assertTrue(
            all("非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("步行短接" in edge.get("description", "") for edge in pedestrian_gate_edges)
        )

    def test_m31a_seu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("SEU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SEU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SEU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SEU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_bike["total_weight"], west_to_service_walk["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_bike["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(west_to_service_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("西门非机动车绕行接驳", west_to_service_bike["path_steps"][0]["edge_name"])
        self.assertEqual(west_to_service_mixed["path_steps"][0]["transport_mode_used"], "walk")
        self.assertIn("西门步行短接", west_to_service_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any("东南大学九龙湖校区步骑共享主路" in step["description"] for step in west_to_service_mixed["path_steps"])
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SEU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SEU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SEU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_sports_bike["path_steps"][0]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertIn("南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])

    def test_m31a_seu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("SEU"))

        mixed_indoor = router.query_routing(
            "gate_west",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SEU",
        )
        bike_indoor = router.query_routing(
            "gate_west",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SEU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_seu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "SEU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_seu_transport_calibration"
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_seu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") in {
                "seu_west_gate_bike_detour",
                "seu_south_gate_bike_detour",
            }
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_SEU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 12)
        self.assertEqual(len(bike_calibration_edges), 8)
        self.assertEqual(len(bike_gate_detour_edges), 4)
        self.assertEqual(len(bike_poi_connector_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk", "bike"} for edge in shared_edges)
        )
        self.assertTrue(
            all("步骑共享主路" in edge.get("description", "") for edge in shared_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("东南大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )

    def test_m31a_sysu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("SYSU"))

        west_to_service_walk = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SYSU",
        )
        west_to_service_bike = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SYSU",
        )
        west_to_service_mixed = router.query_routing(
            "gate_west",
            "service_center",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SYSU",
        )
        self.assertTrue(west_to_service_walk["success"])
        self.assertTrue(west_to_service_bike["success"])
        self.assertTrue(west_to_service_mixed["success"])
        self.assertLess(west_to_service_bike["total_weight"], west_to_service_walk["total_weight"])
        self.assertLess(west_to_service_mixed["total_weight"], west_to_service_bike["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in west_to_service_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(west_to_service_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("西门非机动车绕行接驳", west_to_service_bike["path_steps"][0]["edge_name"])
        self.assertEqual(west_to_service_mixed["path_steps"][0]["transport_mode_used"], "walk")
        self.assertIn("西门步行短接", west_to_service_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any(
                "中山大学广州校区南校园步骑共享主路" in step["description"]
                for step in west_to_service_mixed["path_steps"]
            )
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SYSU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SYSU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SYSU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_sports_bike["path_steps"][0]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertIn("南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])

    def test_m31a_sysu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("SYSU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SYSU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SYSU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_sysu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "SYSU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_sysu_transport_calibration"
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_sysu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") in {
                "sysu_west_gate_bike_detour",
                "sysu_south_gate_bike_detour",
            }
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_SYSU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 30)
        self.assertEqual(len(bike_calibration_edges), 8)
        self.assertEqual(len(bike_gate_detour_edges), 4)
        self.assertEqual(len(bike_poi_connector_edges), 4)
        self.assertEqual(len(pedestrian_gate_edges), 4)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk", "bike"} for edge in shared_edges)
        )
        self.assertTrue(
            all("中山大学广州校区南校园步骑共享主路" in edge.get("description", "") for edge in shared_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("中山大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )
        self.assertTrue(
            all("非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )

    def test_m31a_scu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("SCU"))

        south_to_teaching_axis_walk = router.query_routing(
            "gate_south",
            "road_teaching_axis",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SCU",
        )
        south_to_teaching_axis_bike = router.query_routing(
            "gate_south",
            "road_teaching_axis",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SCU",
        )
        self.assertTrue(south_to_teaching_axis_walk["success"])
        self.assertTrue(south_to_teaching_axis_bike["success"])
        self.assertLess(
            south_to_teaching_axis_walk["total_weight"],
            south_to_teaching_axis_bike["total_weight"],
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_teaching_axis_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_teaching_axis_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(south_to_teaching_axis_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertIn(
            "南门非机动车绕行接驳",
            south_to_teaching_axis_bike["path_steps"][0]["edge_name"],
        )

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SCU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SCU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SCU",
        )
        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertEqual(south_to_sports_bike["path_steps"][-1]["edge_type"], "bike_lane")
        self.assertIn("运动场非机动车接驳", south_to_sports_bike["path_steps"][-1]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertIn("南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])

    def test_m31a_scu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("SCU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SCU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SCU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        self.assertIn("bike", [step["transport_mode_used"] for step in mixed_indoor["path_steps"]])
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_scu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "SCU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_scu_transport_calibration"
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_scu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") == "scu_south_gate_bike_detour"
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
            and edge.get("m31a_demo_role") == "scu_sports_ground_bike_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_scu_transport_calibration"
            and edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_SCU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 36)
        self.assertEqual(len(bike_calibration_edges), 4)
        self.assertEqual(len(bike_gate_detour_edges), 2)
        self.assertEqual(len(bike_poi_connector_edges), 2)
        self.assertEqual(len(pedestrian_gate_edges), 2)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk", "bike"} for edge in shared_edges)
        )
        self.assertTrue(
            all("四川大学望江校区步骑共享主路" in edge.get("description", "") for edge in shared_edges)
        )
        self.assertTrue(all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges))
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_poi_connector_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_poi_connector_edges)
        )
        self.assertTrue(
            all("四川大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )
        self.assertTrue(
            all("非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("运动场非机动车接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_poi_connector_edges)
        )

    def test_m31a_hnu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("HNU"))

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="HNU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="HNU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="HNU",
        )

        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_sports_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_sports_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertEqual(south_to_sports_bike["path_steps"][-1]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_sports_bike["path_steps"][0]["edge_name"])
        self.assertIn("田径场非机动车接驳", south_to_sports_bike["path_steps"][-1]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertEqual(south_to_sports_mixed["path_steps"][0]["allowed_transports"], ["walk"])
        self.assertIn("南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any("湖南大学岳麓山校区步骑共享主路" in step["description"] for step in south_to_sports_mixed["path_steps"])
        )

    def test_m31a_hnu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("HNU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="HNU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "lib_reading_room_2",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="HNU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        mixed_modes = [step["transport_mode_used"] for step in mixed_indoor["path_steps"]]
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_hnu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "HNU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_hnu_transport_calibration"
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_hnu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") == "hnu_south_gate_bike_detour"
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
            and edge.get("m31a_demo_role") == "hnu_sports_ground_bike_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_hnu_transport_calibration"
            and edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_HNU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 8)
        self.assertEqual(len(bike_calibration_edges), 4)
        self.assertEqual(len(bike_gate_detour_edges), 2)
        self.assertEqual(len(bike_poi_connector_edges), 2)
        self.assertEqual(len(pedestrian_gate_edges), 2)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk", "bike"} for edge in shared_edges)
        )
        self.assertTrue(
            all("湖南大学岳麓山校区步骑共享主路" in edge.get("description", "") for edge in shared_edges)
        )
        self.assertTrue(all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges))
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all(edge.get("type") == "bike_lane" for edge in bike_poi_connector_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_poi_connector_edges)
        )
        self.assertTrue(
            all("湖南大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )
        self.assertTrue(
            all("非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("田径场非机动车接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_poi_connector_edges)
        )

    def test_m31a_sdu_transport_calibration_walk_bike_and_mixed(self):
        router = Router(GraphLoader.load_site_graph("SDU"))

        south_to_sports_walk = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="walk",
            site_id="SDU",
        )
        south_to_sports_bike = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SDU",
        )
        south_to_sports_mixed = router.query_routing(
            "gate_south",
            "sports_ground",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SDU",
        )

        self.assertTrue(south_to_sports_walk["success"])
        self.assertTrue(south_to_sports_bike["success"])
        self.assertTrue(south_to_sports_mixed["success"])
        self.assertLess(south_to_sports_bike["total_weight"], south_to_sports_walk["total_weight"])
        self.assertLess(south_to_sports_mixed["total_weight"], south_to_sports_bike["total_weight"])
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_sports_walk["path_steps"]},
            {"walk"},
        )
        self.assertEqual(
            {step["transport_mode_used"] for step in south_to_sports_bike["path_steps"]},
            {"bike"},
        )
        self.assertEqual(south_to_sports_bike["path_steps"][0]["edge_type"], "bike_lane")
        self.assertEqual(south_to_sports_bike["path_steps"][-1]["edge_type"], "bike_lane")
        self.assertIn("南门非机动车绕行接驳", south_to_sports_bike["path_steps"][0]["edge_name"])
        self.assertIn("田径场非机动车接驳", south_to_sports_bike["path_steps"][-1]["edge_name"])
        mixed_modes = [step["transport_mode_used"] for step in south_to_sports_mixed["path_steps"]]
        self.assertIn("walk", mixed_modes)
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        self.assertEqual(south_to_sports_mixed["path_steps"][0]["allowed_transports"], ["walk"])
        self.assertIn("山东大学中心校区南门步行短接", south_to_sports_mixed["path_steps"][0]["description"])
        self.assertTrue(
            any(
                "山东大学中心校区步骑共享主路示范段" in step["description"]
                for step in south_to_sports_mixed["path_steps"]
            )
        )

    def test_m31a_sdu_transport_keeps_indoor_segments_walk_only(self):
        router = Router(GraphLoader.load_site_graph("SDU"))

        mixed_indoor = router.query_routing(
            "gate_south",
            "gymnasium_court_2f",
            strategy="shortest_time",
            transport_mode="mixed",
            site_id="SDU",
        )
        bike_indoor = router.query_routing(
            "gate_south",
            "gymnasium_court_2f",
            strategy="shortest_time",
            transport_mode="bike",
            site_id="SDU",
        )

        self.assertTrue(mixed_indoor["success"])
        self.assertFalse(bike_indoor["success"])
        self.assertEqual(bike_indoor["message"], "无法从起点到达终点。")
        mixed_modes = [step["transport_mode_used"] for step in mixed_indoor["path_steps"]]
        self.assertIn("bike", mixed_modes)
        self.assertEqual(mixed_modes[0], "walk")
        indoor_steps = [
            step for step in mixed_indoor["path_steps"]
            if step["edge_type"] in {"gate_link", "indoor_path", "stairs", "elevator"}
        ]
        self.assertTrue(indoor_steps)
        self.assertEqual({step["transport_mode_used"] for step in indoor_steps}, {"walk"})

    def test_m31a_sdu_outdoor_data_declares_transport_semantics(self):
        outdoor_path = Path(__file__).resolve().parents[1] / "data" / "sites" / "SDU" / "outdoor.json"
        with outdoor_path.open("r", encoding="utf-8") as f:
            outdoor = json.load(f)

        edges = outdoor["edges"]
        shared_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_sdu_transport_calibration"
            and edge.get("transport_semantics") == "shared_walk_bike"
        ]
        bike_calibration_edges = [
            edge for edge in edges
            if edge.get("allowed_transports") == ["bike"]
            and edge.get("source") == "m31a_sdu_transport_calibration"
        ]
        bike_gate_detour_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_only"
            and edge.get("m31a_demo_role") == "sdu_south_gate_bike_detour"
        ]
        bike_poi_connector_edges = [
            edge for edge in bike_calibration_edges
            if edge.get("transport_semantics") == "bike_dismount_connector"
            and edge.get("m31a_demo_role") == "sdu_sports_ground_bike_connector"
        ]
        pedestrian_gate_edges = [
            edge for edge in edges
            if edge.get("source") == "m31a_sdu_transport_calibration"
            and edge.get("transport_semantics") == "pedestrian_gate_shortcut"
        ]

        self.assertEqual(outdoor["metadata"]["transport_calibration_stage"], "M31A_SDU")
        self.assertEqual(outdoor["metadata"]["transport_modes"], ["walk", "bike", "mixed"])
        self.assertEqual(len(shared_edges), 6)
        self.assertEqual(len(bike_calibration_edges), 6)
        self.assertEqual(len(bike_gate_detour_edges), 4)
        self.assertEqual(len(bike_poi_connector_edges), 2)
        self.assertEqual(len(pedestrian_gate_edges), 2)
        self.assertTrue(
            all(edge.get("allowed_transports") == ["walk"] for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(edge.get("vehicle_access") == "pedestrian_only" for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk"} for edge in pedestrian_gate_edges)
        )
        self.assertTrue(
            all(set(edge.get("transport_speeds", {}).keys()) == {"walk", "bike"} for edge in shared_edges)
        )
        self.assertTrue(
            all("山东大学中心校区步骑共享主路示范段" in edge.get("description", "") for edge in shared_edges)
        )
        self.assertTrue(all(edge.get("type") == "bike_lane" for edge in bike_gate_detour_edges))
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(all(edge.get("type") == "bike_lane" for edge in bike_poi_connector_edges))
        self.assertTrue(
            all(edge.get("vehicle_access") == "vehicle_only" for edge in bike_poi_connector_edges)
        )
        self.assertTrue(
            all("山东大学" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_calibration_edges)
        )
        self.assertTrue(
            all("南门非机动车绕行接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_gate_detour_edges)
        )
        self.assertTrue(
            all("田径场非机动车接驳" in f"{edge.get('name', '')}{edge.get('description', '')}" for edge in bike_poi_connector_edges)
        )

    def test_standard_site_multi_target_uses_white_road_graph(self):
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_multi_target(
            "gate_north",
            ["library", "canteen", "convenience_store"],
            strategy="shortest_distance",
            transport_mode="walk",
            return_to_start=True,
            site_id="PKU",
        )

        self.assertTrue(route["success"])
        self.assertEqual(route["visit_order"][0], "gate_north")
        self.assertEqual(route["visit_order"][-1], "gate_north")
        self.assertTrue(any(node_id.startswith("road_white_") for node_id in route["path"]))

    def test_diary_destination_node_routes_through_white_road_graph(self):
        diary_path = Path(__file__).resolve().parents[1] / "data" / "diary_data.json"
        with diary_path.open("r", encoding="utf-8") as f:
            diaries = json.load(f)

        diary = next(item for item in diaries if item.get("destination_node_id") == "canteen")
        router = Router(GraphLoader.load_site_graph("PKU"))
        route = router.query_routing("gate_north", diary["destination_node_id"])

        self.assertTrue(route["success"])
        self.assertEqual(route["path"][0], "gate_north")
        self.assertEqual(route["path"][-1], diary["destination_node_id"])
        self.assertTrue(any(node_id.startswith("road_white_") for node_id in route["path"]))

if __name__ == '__main__':
    unittest.main()
