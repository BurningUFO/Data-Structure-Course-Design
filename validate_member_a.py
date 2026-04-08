import sys
import os
import json

# 设置搜索路径
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from graph.graph import Graph
from graph.loader import GraphLoader

def validate():
    print("=== Member A: Infrastructure Validation ===")
    
    # 1. 检查数据格式是否符合要求
    print("\n[Step 1] Checking data format...")
    nodes_path = 'data/map_nodes.json'
    edges_path = 'data/map_edges.json'
    
    with open(nodes_path, 'r', encoding='utf-8') as f:
        nodes_data = json.load(f)
        assert "nodes" in nodes_data, "map_nodes.json missing 'nodes' key"
        for n in nodes_data["nodes"]:
            assert "id" in n and "name" in n, f"Node {n} missing id/name"
    
    with open(edges_path, 'r', encoding='utf-8') as f:
        edges_data = json.load(f)
        assert "edges" in edges_data, "map_edges.json missing 'edges' key"
        for e in edges_data["edges"]:
            assert all(k in e for k in ["from", "to", "distance"]), f"Edge {e} missing core fields"
    print("OK: Data format matches standards.")

    # 2. 检查加载器与图结构功能
    print("\n[Step 2] Checking loader and graph functionality...")
    graph = GraphLoader.load_from_json(nodes_path, edges_path)
    
    # 检查节点数量
    print(f"Loaded {len(graph.nodes)} nodes.")
    assert len(graph.nodes) == 5, "Should have 5 sample nodes"
    
    # 检查边与邻接表
    edge_count = sum(len(edges) for edges in graph.adj.values())
    print(f"Loaded {edge_count} edges.")
    assert edge_count == 5, "Should have 5 sample edges"
    
    # 3. 检查核心算法接口：通行时间计算 (权重逻辑)
    print("\n[Step 3] Checking weight/time calculation...")
    # 测试 node_002 到 node_003 的通行时间
    # 距离: 150, 拥挤度: 0.8, 速度: 1.5
    # 预期时间 = 150 / (1.5 * 0.8) = 150 / 1.2 = 125
    edge_to_003 = next(e for e in graph.adj["node_002"] if e["to"] == "node_003")
    travel_time = graph.get_travel_time("node_002", edge_to_003)
    print(f"Travel time from 002 to 003: {travel_time}s")
    assert abs(travel_time - 125.0) < 0.001, "Travel time calculation mismatch"
    print("OK: Graph weights and interface consistent with docs.")

    print("\n=== Validation Result: SUCCESS ===")

if __name__ == "__main__":
    try:
        validate()
    except Exception as e:
        print(f"\nValidation FAILED: {e}")
        sys.exit(1)
