"""
成员 B：成员 A 距离接口适配层

本模块只负责把成员 A 的图加载与 `Router.query_distance` 封装成
成员 B 服务层可直接调用的 `distance_provider`。

这样做可以避免业务层直接依赖成员 A 的具体初始化细节；如果后续 A 将接口升级
为带 `site_id` 的分层版本，只需要调整本适配层即可。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from src.graph.graph import Graph
from src.graph.loader import GraphLoader
from src.routing.router import Router


DistanceProvider = Callable[[str, str, str], float]


def get_default_map_nodes_path() -> Path:
    """返回当前成员 A loader 可读取的默认节点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "map_nodes.json"


def get_default_map_edges_path() -> Path:
    """返回当前成员 A loader 可读取的默认边数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "map_edges.json"


def get_global_sites_path() -> Path:
    """返回全局景区注册表路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "global_sites.json"


def get_default_site_id() -> str:
    """返回默认景区 ID。"""
    path = get_global_sites_path()
    if not path.exists():
        return "PKU"

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    if not sites:
        return "PKU"

    return str(sites[0].get("id", "PKU")).strip() or "PKU"


def get_default_site_graph_paths(site_id: str | None = None) -> list[Path]:
    """返回标准分层图数据文件列表。"""
    target_site_id = site_id or get_default_site_id()
    site_dir = Path(__file__).resolve().parents[2] / "data" / "sites" / target_site_id
    if not site_dir.exists():
        return []

    global_sites_path = get_global_sites_path()
    if global_sites_path.exists():
        with global_sites_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for site in data.get("sites", []):
            if str(site.get("id", "")).strip() != target_site_id:
                continue
            sub_graphs = [str(name).strip() for name in site.get("sub_graphs", []) if str(name).strip()]
            if sub_graphs:
                return [path for path in (site_dir / f"{name}.json" for name in sub_graphs) if path.exists()]

    return sorted(site_dir.glob("*.json"))


def load_merged_site_graph(paths: list[Path], site_id: str) -> Graph:
    """加载标准分层图，并在 B 侧补充门节点与室内入口的桥接边。"""
    graph = Graph(layer_id=site_id, name=site_id)
    indoor_gate_nodes: dict[str, list[str]] = {}
    outdoor_gate_links: list[tuple[str, str]] = []

    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        sub_graph_id = path.stem
        graph_type = str(data.get("graph_type", "")).strip().lower()

        for node in data.get("nodes", []):
            node_data = node.copy()
            node_id = str(node_data.pop("id", "")).strip()
            if not node_id:
                continue

            node_data["source_sub_graph_id"] = sub_graph_id
            node_data["graph_type"] = graph_type
            graph.add_node(node_id, **node_data)

            if sub_graph_id == "outdoor":
                linked_subgraph = str(node.get("sub_graph_id", "")).strip()
                if linked_subgraph:
                    outdoor_gate_links.append((node_id, linked_subgraph))
            elif node.get("is_gate"):
                indoor_gate_nodes.setdefault(sub_graph_id, []).append(node_id)

        for edge in data.get("edges", []):
            graph.add_edge(
                u=edge["from"],
                v=edge["to"],
                distance=edge["distance"],
                congestion=edge.get("congestion", 1.0),
                ideal_speed=edge.get("ideal_speed", 1.0),
                type=edge.get("type", ""),
                vehicle_access=edge.get("vehicle_access", "all"),
                name=edge.get("name", ""),
                description=edge.get("description", ""),
            )

    for outdoor_gate_id, indoor_graph_id in outdoor_gate_links:
        for indoor_gate_id in indoor_gate_nodes.get(indoor_graph_id, []):
            graph.add_edge(
                outdoor_gate_id,
                indoor_gate_id,
                distance=0,
                congestion=1.0,
                ideal_speed=1.0,
                type="gate_link",
                vehicle_access="pedestrian_only",
                name=f"{outdoor_gate_id}->{indoor_gate_id}",
            )
            graph.add_edge(
                indoor_gate_id,
                outdoor_gate_id,
                distance=0,
                congestion=1.0,
                ideal_speed=1.0,
                type="gate_link",
                vehicle_access="pedestrian_only",
                name=f"{indoor_gate_id}->{outdoor_gate_id}",
            )

    return graph


class RouterDistanceAdapter:
    """将成员 A 的 Router 封装成成员 B 可注入的距离查询对象。"""

    def __init__(
        self,
        nodes_path: str | Path | None = None,
        edges_path: str | Path | None = None,
        site_id: str | None = None,
        merged_paths: list[str | Path] | None = None,
    ) -> None:
        if merged_paths is not None:
            graph_paths = [Path(path) for path in merged_paths]
            graph = load_merged_site_graph(graph_paths, site_id or get_default_site_id())
        elif nodes_path is None and edges_path is None:
            default_site_paths = get_default_site_graph_paths(site_id)
            if default_site_paths:
                graph = load_merged_site_graph(default_site_paths, site_id or get_default_site_id())
            else:
                self.nodes_path = get_default_map_nodes_path()
                self.edges_path = get_default_map_edges_path()
                graph = GraphLoader.load_from_json(self.nodes_path, self.edges_path)
        else:
            self.nodes_path = Path(nodes_path) if nodes_path is not None else get_default_map_nodes_path()
            self.edges_path = Path(edges_path) if edges_path is not None else get_default_map_edges_path()
            graph = GraphLoader.load_from_json(self.nodes_path, self.edges_path)

        self.router = Router(graph)

    def query_distance(
        self,
        start_node_id: str,
        target_node_id: str,
        strategy: str = "shortest_distance",
    ) -> float:
        """调用成员 A 的 `Router.query_distance`。"""
        return float(self.router.query_distance(start_node_id, target_node_id, strategy))

    def as_provider(self) -> DistanceProvider:
        """返回可直接传给 `search_and_recommend` 的函数。"""
        return self.query_distance


def build_distance_provider(
    nodes_path: str | Path | None = None,
    edges_path: str | Path | None = None,
    site_id: str | None = None,
    merged_paths: list[str | Path] | None = None,
) -> DistanceProvider:
    """创建默认距离 provider。"""
    return RouterDistanceAdapter(
        nodes_path=nodes_path,
        edges_path=edges_path,
        site_id=site_id,
        merged_paths=merged_paths,
    ).as_provider()
