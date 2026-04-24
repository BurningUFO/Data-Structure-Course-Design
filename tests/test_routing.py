import sys
import os
import unittest

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

if __name__ == '__main__':
    unittest.main()
