import sys
import os

# 将 src 目录添加到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graph.loader import GraphLoader

def test_load():
    base_path = os.path.dirname(__file__)
    nodes_file = os.path.join(base_path, '../data/map_nodes.json')
    edges_file = os.path.join(base_path, '../data/map_edges.json')

    print(f"Loading from {nodes_file}...")
    
    try:
        graph = GraphLoader.load_from_json(nodes_file, edges_file)
        print("Success!")
        print(graph)
        
        # 验证节点是否存在
        assert "node_001" in graph.nodes
        assert graph.nodes["node_001"]["name"] == "北门"
        
        # 验证邻接表是否有边
        assert len(graph.adj["node_001"]) > 0
        print("Verification complete: Graph loaded correctly.")
        
    except Exception as e:
        print(f"Error during loading: {e}")

def test_load_site_graph():
    print("Loading standard site graph for PKU...")

    try:
        graph = GraphLoader.load_site_graph("PKU")
        print("Success!")
        print(graph)

        assert getattr(graph, "site_id", "") == "PKU"
        assert "library" in graph.nodes
        assert "lib_entrance" in graph.nodes

        linked_nodes = [edge["to"] for edge in graph.adj["library"]]
        assert "lib_entrance" in linked_nodes
        print("Verification complete: Standard site graph loaded correctly.")

    except Exception as e:
        print(f"Error during site graph loading: {e}")

if __name__ == "__main__":
    test_load()
    test_load_site_graph()
