import json
import os
import sys

# 尝试从包中导入，或者从当前目录导入
try:
    from .graph import Graph
except (ImportError, ValueError):
    try:
        from graph import Graph
    except ImportError:
        # 兼容根目录直接运行
        sys.path.append(os.path.dirname(__file__))
        from graph import Graph

class GraphLoader:
    @staticmethod
    def load_from_json(nodes_path, edges_path):
        """
        从 JSON 文件加载图数据
        :param nodes_path: 节点 JSON 文件路径
        :param edges_path: 边 JSON 文件路径
        :return: 初始化完成的 Graph 对象
        """
        graph = Graph()

        # 加载节点
        if not os.path.exists(nodes_path):
            raise FileNotFoundError(f"Nodes file not found: {nodes_path}")
        
        with open(nodes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for node in data.get("nodes", []):
                # 保护性代码：提取 id 并将其余字段作为属性
                node_data = node.copy()
                if "id" not in node_data:
                    continue
                node_id = node_data.pop("id")
                graph.add_node(node_id, **node_data)

        # 加载边
        if not os.path.exists(edges_path):
            raise FileNotFoundError(f"Edges file not found: {edges_path}")
            
        with open(edges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for edge in data.get("edges", []):
                graph.add_edge(
                    u=edge["from"],
                    v=edge["to"],
                    distance=edge["distance"],
                    congestion=edge.get("congestion", 1.0),
                    ideal_speed=edge.get("ideal_speed", 1.0)
                )
        
        return graph
