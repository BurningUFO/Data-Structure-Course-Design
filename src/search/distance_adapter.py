"""
成员 B：成员 A 距离接口适配层

本模块只负责把成员 A 的图加载与 `Router.query_distance` 封装成
成员 B 服务层可直接调用的 `distance_provider`。

这样做可以避免业务层直接依赖成员 A 的具体初始化细节；如果后续 A 将接口升级
为带 `site_id` 的分层版本，只需要调整本适配层即可。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.graph.loader import GraphLoader
from src.routing.router import Router


DistanceProvider = Callable[[str, str, str], float]


def get_default_map_nodes_path() -> Path:
    """返回当前成员 A loader 可读取的默认节点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "map_nodes.json"


def get_default_map_edges_path() -> Path:
    """返回当前成员 A loader 可读取的默认边数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "map_edges.json"


class RouterDistanceAdapter:
    """将成员 A 的 Router 封装成成员 B 可注入的距离查询对象。"""

    def __init__(
        self,
        nodes_path: str | Path | None = None,
        edges_path: str | Path | None = None,
    ) -> None:
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
) -> DistanceProvider:
    """创建默认距离 provider。"""
    return RouterDistanceAdapter(nodes_path=nodes_path, edges_path=edges_path).as_provider()
