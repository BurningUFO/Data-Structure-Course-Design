import sys
import os
import unittest

# 将 src 目录添加到 Python 路径，方便导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graph.graph import Graph
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

if __name__ == '__main__':
    unittest.main()
