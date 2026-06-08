"""
成员 B：成员 A 距离接口适配层

本模块只负责把成员 A 的图加载与 `Router.query_distance` 封装成
成员 B 服务层可直接调用的 `distance_provider`。

这样做可以避免业务层直接依赖成员 A 的具体初始化细节；当前适配层已经兼容
标准分层数据与成员 A 的可选 `site_id` 接口。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.graph.loader import GraphLoader
from src.routing.router import Router
from src.site_registry import load_global_sites, resolve_site_data_dir, resolve_site_subgraphs


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
    sites = load_global_sites()
    if not sites:
        return "PKU"

    return str(sites[0].get("id", "PKU")).strip() or "PKU"


def get_default_site_graph_paths(site_id: str | None = None) -> list[Path]:
    """返回标准分层图数据文件列表。"""
    target_site_id = site_id or get_default_site_id()
    site_dir = resolve_site_data_dir(target_site_id)
    if not site_dir.exists():
        return []

    sub_graphs = resolve_site_subgraphs(target_site_id)
    if sub_graphs:
        return [path for path in (site_dir / f"{name}.json" for name in sub_graphs) if path.exists()]

    return sorted(site_dir.glob("*.json"))


class RouterDistanceAdapter:
    """将成员 A 的 Router 封装成成员 B 可注入的距离查询对象。"""

    def __init__(
        self,
        nodes_path: str | Path | None = None,
        edges_path: str | Path | None = None,
        site_id: str | None = None,
        merged_paths: list[str | Path] | None = None,
    ) -> None:
        self.site_id = site_id or get_default_site_id()

        if merged_paths is not None:
            graph_paths = [Path(path) for path in merged_paths]
            graph = GraphLoader.load_site_graph(site_id=self.site_id, graph_paths=graph_paths)
        elif nodes_path is None and edges_path is None:
            default_site_paths = get_default_site_graph_paths(site_id)
            if default_site_paths:
                graph = GraphLoader.load_site_graph(site_id=self.site_id, graph_paths=default_site_paths)
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
        return float(
            self.router.query_distance(
                start_node_id,
                target_node_id,
                strategy,
                site_id=self.site_id,
            )
        )

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
