import json
import os
import sys
from pathlib import Path

try:
    from src.site_registry import (
        resolve_site_data_dir,
        resolve_site_node_name_overrides,
        resolve_site_subgraphs,
        resolve_site_text_replacements,
    )
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.site_registry import (
        resolve_site_data_dir,
        resolve_site_node_name_overrides,
        resolve_site_subgraphs,
        resolve_site_text_replacements,
    )

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
    def _load_json_file(path):
        path = Path(path)
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _resolve_data_root(data_root=None):
        if data_root is not None:
            return Path(data_root)
        return Path(__file__).resolve().parents[2] / "data"

    @staticmethod
    def _get_global_sites_path(data_root=None):
        return GraphLoader._resolve_data_root(data_root) / "global_sites.json"

    @staticmethod
    def _load_global_sites(data_root=None):
        global_sites_path = GraphLoader._get_global_sites_path(data_root)
        if not global_sites_path.exists():
            return []

        data = GraphLoader._load_json_file(global_sites_path)
        sites = data.get("sites", [])
        return sites if isinstance(sites, list) else []

    @staticmethod
    def _get_site_graph_paths(site_id="PKU", data_root=None, graph_paths=None):
        if graph_paths is not None:
            return [Path(path) for path in graph_paths]

        data_root_path = GraphLoader._resolve_data_root(data_root)
        normalized_site_id = str(site_id).strip()
        site_dir = resolve_site_data_dir(normalized_site_id, data_root_path)
        if not site_dir.exists():
            raise FileNotFoundError(f"Site directory not found: {site_dir}")

        sub_graphs = resolve_site_subgraphs(normalized_site_id, data_root_path)
        if sub_graphs:
            resolved_paths = [site_dir / f"{name}.json" for name in sub_graphs]
            return [path for path in resolved_paths if path.exists()]

        return sorted(site_dir.rglob("*.json"))

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

    @staticmethod
    def load_site_graph(site_id="PKU", data_root=None, graph_paths=None):
        """
        原生加载标准分层站点数据。

        标准目录：
        data/
          └── sites/{site_id}/
                ├── outdoor.json
                └── indoor_XXX.json

        当前策略：
        - 将标准分层图合并为一张可直接用于 Dijkstra 的总图
        - 自动补充室外门节点到室内入口节点的 0 距离桥接边
        """
        normalized_site_id = str(site_id).strip() or "PKU"
        resolved_paths = GraphLoader._get_site_graph_paths(
            site_id=normalized_site_id,
            data_root=data_root,
            graph_paths=graph_paths,
        )
        if not resolved_paths:
            raise FileNotFoundError(f"No graph json found for site: {normalized_site_id}")

        graph = Graph(layer_id=normalized_site_id, name=normalized_site_id)
        graph.site_id = normalized_site_id
        node_name_overrides = resolve_site_node_name_overrides(
            normalized_site_id,
            data_root,
        )
        text_replacements = resolve_site_text_replacements(
            normalized_site_id,
            data_root,
        )

        indoor_gate_nodes = {}
        outdoor_gate_links = []

        def display_text(value):
            if value is None:
                return ""
            text = str(value)
            for source, target in text_replacements:
                text = text.replace(source, target)
            return text.strip()

        def display_node_name(node_id, fallback_name):
            return node_name_overrides.get(str(node_id).strip()) or display_text(fallback_name or node_id)

        for graph_path in resolved_paths:
            data = GraphLoader._load_json_file(graph_path)
            graph_file_id = str(graph_path.stem).strip()
            graph_type = str(data.get("graph_type", "")).strip().lower() or (
                "outdoor" if graph_file_id == "outdoor" else "indoor"
            )

            for node in data.get("nodes", []):
                node_data = node.copy()
                node_id = str(node_data.pop("id", "")).strip()
                if not node_id:
                    continue

                node_data["name"] = display_node_name(node_id, node_data.get("name", node_id))
                for field_name in ("description", "indoor_building", "building_name"):
                    if field_name in node_data:
                        node_data[field_name] = display_text(node_data[field_name])

                node_data["source_sub_graph_id"] = graph_file_id
                node_data["graph_type"] = graph_type
                graph.add_node(node_id, **node_data)

                if graph_file_id == "outdoor":
                    linked_subgraph = str(node.get("sub_graph_id", "")).strip()
                    if linked_subgraph:
                        outdoor_gate_links.append((node_id, linked_subgraph))
                elif node.get("is_gate"):
                    indoor_gate_nodes.setdefault(graph_file_id, []).append(node_id)

            for edge in data.get("edges", []):
                edge_data = edge.copy()
                source = edge_data.pop("from")
                target = edge_data.pop("to")
                distance = edge_data.pop("distance")
                edge_data.setdefault("congestion", 1.0)
                edge_data.setdefault("ideal_speed", 1.0)
                edge_data.setdefault("type", "")
                edge_data.setdefault("vehicle_access", "all")
                edge_data.setdefault("name", "")
                edge_data.setdefault("description", "")
                edge_data["name"] = display_text(edge_data["name"])
                edge_data["description"] = display_text(edge_data["description"])
                graph.add_edge(
                    u=source,
                    v=target,
                    distance=distance,
                    **edge_data,
                )

        for outdoor_gate_id, indoor_graph_id in outdoor_gate_links:
            for indoor_gate_id in indoor_gate_nodes.get(indoor_graph_id, []):
                outdoor_gate_name = display_node_name(outdoor_gate_id, outdoor_gate_id)
                indoor_gate_name = display_node_name(indoor_gate_id, indoor_gate_id)
                graph.add_edge(
                    outdoor_gate_id,
                    indoor_gate_id,
                    distance=0,
                    congestion=1.0,
                    ideal_speed=1.0,
                    type="gate_link",
                    vehicle_access="pedestrian_only",
                    name=f"{outdoor_gate_name} -> {indoor_gate_name}",
                )
                graph.add_edge(
                    indoor_gate_id,
                    outdoor_gate_id,
                    distance=0,
                    congestion=1.0,
                    ideal_speed=1.0,
                    type="gate_link",
                    vehicle_access="pedestrian_only",
                    name=f"{indoor_gate_name} -> {outdoor_gate_name}",
                )

        return graph
