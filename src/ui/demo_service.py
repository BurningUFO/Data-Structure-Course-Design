"""Member B minimal demo UI service layer.

This module keeps the web demo thin:
- reuse search / recommend / routing business APIs directly
- provide a UI-friendly bootstrap payload
- normalize route overlays for the simple campus map
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.diary.diary_service import load_diary_records, search_diaries_fulltext
from src.graph.loader import GraphLoader
from src.recommend.catering_service import recommend_catering
from src.routing.router import Router
from src.search.search_service import (
    PLACE_CATEGORY_SET,
    get_default_site_id,
    load_global_sites,
    load_site_records,
    search_and_recommend,
    search_places,
)


Record = dict[str, Any]

CATEGORY_LABELS = {
    "entrance": "校门",
    "education": "教学 / 学习",
    "landmark": "地标",
    "dormitory": "宿舍",
    "catering": "餐饮",
    "shopping": "购物",
    "sports": "运动",
    "restroom": "洗手间",
    "parking": "停车",
    "hall": "大厅",
    "reading_room": "阅览室",
    "service": "服务",
    "passage": "通道",
    "road": "道路",
}

START_NODE_PRIORITY = {
    "gate_north": 0,
    "gate_east": 1,
    "gate_south": 2,
    "square_center": 3,
    "library": 4,
    "canteen": 5,
}

TARGET_CATEGORY_PRIORITY = {
    "education": 0,
    "landmark": 1,
    "catering": 2,
    "shopping": 3,
    "restroom": 4,
    "dormitory": 5,
    "hall": 6,
    "reading_room": 7,
    "service": 8,
    "sports": 9,
    "entrance": 10,
    "parking": 11,
    "passage": 12,
    "road": 13,
}

DEFAULT_PRESETS = {
    "scenic": [
        {"label": "图书馆", "keyword": "图书馆", "category": "education"},
        {"label": "宿舍", "keyword": "宿舍", "category": "dormitory"},
        {"label": "广场", "keyword": "广场", "category": "landmark"},
    ],
    "place": [
        {"label": "洗手间", "keyword": "洗手间", "category": "restroom"},
        {"label": "便利店", "keyword": "便利店", "category": "shopping"},
        {"label": "教学楼", "keyword": "教学楼", "category": "education"},
    ],
    "catering": [
        {"label": "全部餐饮", "keyword": "", "cuisine": ""},
        {"label": "咖啡", "keyword": "", "cuisine": "咖啡"},
        {"label": "食堂", "keyword": "食堂", "cuisine": ""},
    ],
    "diary": [
        {"label": "图书馆 自习", "query": "图书馆 自习"},
        {"label": "食堂 美食", "query": "食堂 美食"},
        {"label": "北大 校园", "query": "北京大学 校园"},
    ],
    "route": [
        {"label": "去图书馆", "target_node_id": "library"},
        {"label": "去阅览室", "target_node_id": "lib_reading_room_1"},
        {"label": "去宿舍 101", "target_node_id": "dorm1_room_101"},
    ],
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class DemoUIService:
    """Thin service layer for the minimal demonstrable web UI."""

    def __init__(self, site_id: str | None = None) -> None:
        self.site_id = normalize_text(site_id) or get_default_site_id()
        self.site_meta = self._load_site_meta(self.site_id)
        self.graph = GraphLoader.load_site_graph(self.site_id)
        self.router = Router(self.graph)
        self.site_records = load_site_records(self.site_id)
        self.diary_records = load_diary_records()
        self.outdoor_graph_source = self._load_outdoor_graph_source(self.site_id)
        self.map_nodes = self._build_map_nodes(self.outdoor_graph_source)
        self.map_node_index = {node["id"]: node for node in self.map_nodes}
        self.map_edges = self._build_map_edges(self.outdoor_graph_source)
        self.start_nodes = self._build_start_nodes()
        self.default_start_node = self._resolve_default_start_node()
        self.route_targets = self._build_route_targets()
        self.scenic_categories = self._build_scenic_categories()

    def get_bootstrap_payload(self) -> dict[str, Any]:
        """Return all static data needed by the one-page UI."""
        return {
            "site": self.site_meta,
            "default_start_node": self.default_start_node,
            "start_nodes": self.start_nodes,
            "route_targets": self.route_targets,
            "controls": {
                "scenic_categories": self.scenic_categories,
                "place_categories": [
                    {
                        "value": category,
                        "label": CATEGORY_LABELS.get(category, category),
                    }
                    for category in sorted(PLACE_CATEGORY_SET)
                ],
                "sort_options": [
                    {"value": "heat", "label": "按热度"},
                    {"value": "rating", "label": "按评分"},
                    {"value": "distance_m", "label": "按真实距离"},
                ],
                "route_strategies": [
                    {"value": "shortest_distance", "label": "最短距离"},
                    {"value": "shortest_time", "label": "最短时间"},
                ],
                "transport_modes": [
                    {"value": "any", "label": "不限交通方式"},
                    {"value": "walk", "label": "步行优先"},
                ],
            },
            "presets": DEFAULT_PRESETS,
            "map": {
                "nodes": self.map_nodes,
                "edges": self.map_edges,
                "bounds": self._build_map_bounds(self.map_nodes),
                "node_count": len(self.map_nodes),
                "edge_count": len(self.map_edges),
            },
            "stats": {
                "route_target_count": len(self.route_targets),
                "record_count": len(self.site_records),
                "diary_count": len(self.diary_records),
                "indoor_target_count": sum(
                    1 for item in self.route_targets if item["graph_type"] == "indoor"
                ),
            },
        }

    def scenic_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        response = search_and_recommend(
            keyword=normalize_text(request.get("keyword")),
            category=normalize_text(request.get("category")),
            start_node_id=start_node_id,
            match_mode="fuzzy",
            sort_field=normalize_text(request.get("sort_field")) or "heat",
            limit=self._normalize_limit(request.get("limit"), default=6),
            records=self.site_records,
            distance_provider=self._distance_provider,
            use_default_distance_provider=False,
        )
        return self._decorate_query_response(response, source="scenic_search")

    def place_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        response = search_places(
            keyword=normalize_text(request.get("keyword")),
            category=normalize_text(request.get("category")),
            site_id=self.site_id,
            start_node_id=start_node_id,
            match_mode="fuzzy",
            sort_field=normalize_text(request.get("sort_field")) or "distance_m",
            limit=self._normalize_limit(request.get("limit"), default=6),
            records=self.site_records,
            distance_provider=self._distance_provider,
            use_default_distance_provider=False,
        )
        return self._decorate_query_response(response, source="place_search")

    def catering_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        response = recommend_catering(
            keyword=normalize_text(request.get("keyword")),
            cuisine=normalize_text(request.get("cuisine")),
            site_id=self.site_id,
            start_node_id=start_node_id,
            match_mode="fuzzy",
            sort_field=normalize_text(request.get("sort_field")) or "distance_m",
            limit=self._normalize_limit(request.get("limit"), default=6),
            records=self.site_records,
            distance_provider=self._distance_provider,
            use_default_distance_provider=False,
        )
        return self._decorate_query_response(response, source="catering_recommend")

    def diary_fulltext_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        response = search_diaries_fulltext(
            query=normalize_text(request.get("query")),
            limit=self._normalize_limit(request.get("limit"), default=6),
            records=self.diary_records,
        )
        return self._decorate_query_response(response, source="diary_fulltext_search")

    def plan_route(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        target_node_id = normalize_text(request.get("target_node_id"))
        strategy = self._normalize_strategy(request.get("strategy"))
        transport_mode = self._normalize_transport_mode(request.get("transport_mode"))

        result = self.router.query_routing(
            start_node_id=start_node_id,
            target_node_id=target_node_id,
            strategy=strategy,
            transport_mode=transport_mode,
            site_id=self.site_id,
        )
        if not result.get("success"):
            return result

        decorated = result.copy()
        decorated["ui"] = self._build_route_overlay(decorated)
        decorated["summary"] = {
            "distance_text": self.format_distance(decorated.get("total_distance_m")),
            "time_text": self.format_duration(decorated.get("estimated_time_s")),
            "layer_text": " -> ".join(decorated.get("layer_sequence", [])) or "outdoor",
            "transport_text": "步行优先" if transport_mode == "walk" else "不限交通方式",
            "strategy_text": "最短时间" if strategy == "shortest_time" else "最短距离",
        }
        return decorated

    def _load_site_meta(self, site_id: str) -> dict[str, Any]:
        for site in load_global_sites():
            if normalize_text(site.get("id")) == site_id:
                return {
                    "id": site_id,
                    "name": normalize_text(site.get("name")) or site_id,
                    "description": normalize_text(site.get("description")),
                    "location": normalize_text(site.get("location")),
                }
        return {
            "id": site_id,
            "name": site_id,
            "description": "",
            "location": "",
        }

    def _load_outdoor_graph_source(self, site_id: str) -> dict[str, Any]:
        outdoor_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "sites"
            / site_id
            / "outdoor.json"
        )
        if not outdoor_path.exists():
            return {"nodes": [], "edges": []}
        return json.loads(outdoor_path.read_text(encoding="utf-8"))

    def _build_map_nodes(self, graph_data: dict[str, Any]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for node in graph_data.get("nodes", []):
            location = node.get("location") or {}
            lat = location.get("lat")
            lng = location.get("lng")
            if lat is None or lng is None:
                continue

            category = normalize_text(node.get("category") or node.get("type")) or "unknown"
            nodes.append(
                {
                    "id": normalize_text(node.get("id")),
                    "name": normalize_text(node.get("name")) or normalize_text(node.get("id")),
                    "category": category,
                    "category_label": CATEGORY_LABELS.get(category, category),
                    "graph_type": "outdoor",
                    "lat": float(lat),
                    "lng": float(lng),
                    "is_gate": bool(node.get("is_gate", False)),
                }
            )

        nodes.sort(
            key=lambda item: (
                TARGET_CATEGORY_PRIORITY.get(item["category"], 99),
                item["name"],
            )
        )
        return nodes

    def _build_map_edges(self, graph_data: dict[str, Any]) -> list[dict[str, Any]]:
        node_ids = {node["id"] for node in self.map_nodes}
        seen_pairs: set[tuple[str, str, str]] = set()
        edges: list[dict[str, Any]] = []

        for edge in graph_data.get("edges", []):
            source = normalize_text(edge.get("from"))
            target = normalize_text(edge.get("to"))
            if source not in node_ids or target not in node_ids:
                continue

            pair_key = tuple(sorted((source, target)) + [normalize_text(edge.get("name"))])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            edges.append(
                {
                    "from": source,
                    "to": target,
                    "name": normalize_text(edge.get("name")),
                    "type": normalize_text(edge.get("type")) or "outdoor_road",
                    "distance_m": float(edge.get("distance", 0)),
                }
            )

        return edges

    def _build_map_bounds(self, nodes: list[dict[str, Any]]) -> dict[str, float]:
        if not nodes:
            return {
                "lat_min": 0.0,
                "lat_max": 1.0,
                "lng_min": 0.0,
                "lng_max": 1.0,
            }

        latitudes = [node["lat"] for node in nodes]
        longitudes = [node["lng"] for node in nodes]
        return {
            "lat_min": min(latitudes),
            "lat_max": max(latitudes),
            "lng_min": min(longitudes),
            "lng_max": max(longitudes),
        }

    def _build_start_nodes(self) -> list[dict[str, Any]]:
        start_nodes = [node.copy() for node in self.map_nodes if node["category"] != "road"]
        start_nodes.sort(
            key=lambda item: (
                START_NODE_PRIORITY.get(item["id"], 99),
                TARGET_CATEGORY_PRIORITY.get(item["category"], 99),
                item["name"],
            )
        )
        return start_nodes

    def _resolve_default_start_node(self) -> str:
        for node_id in ("gate_north", "gate_east", "gate_south", "library"):
            if node_id in self.graph.nodes:
                return node_id
        if self.start_nodes:
            return self.start_nodes[0]["id"]
        return next(iter(self.graph.nodes), "")

    def _build_route_targets(self) -> list[dict[str, Any]]:
        targets: list[dict[str, Any]] = []

        for node_id, node_data in self.graph.nodes.items():
            category = normalize_text(node_data.get("category") or node_data.get("type")) or "unknown"
            if category == "road":
                continue

            graph_type = normalize_text(node_data.get("graph_type")) or "indoor"
            location = node_data.get("location") or {}
            has_location = node_id in self.map_node_index
            targets.append(
                {
                    "id": node_id,
                    "name": normalize_text(node_data.get("name")) or node_id,
                    "category": category,
                    "category_label": CATEGORY_LABELS.get(category, category),
                    "graph_type": graph_type,
                    "layer": normalize_text(node_data.get("source_sub_graph_id")) or graph_type,
                    "has_map_location": has_location,
                    "lat": float(location.get("lat")) if location.get("lat") is not None else None,
                    "lng": float(location.get("lng")) if location.get("lng") is not None else None,
                }
            )

        targets.sort(
            key=lambda item: (
                TARGET_CATEGORY_PRIORITY.get(item["category"], 99),
                item["graph_type"] != "outdoor",
                item["name"],
            )
        )
        return targets

    def _build_scenic_categories(self) -> list[dict[str, str]]:
        categories = {
            normalize_text(record.get("category"))
            for record in self.site_records
            if normalize_text(record.get("category"))
        }
        ordered = sorted(
            categories,
            key=lambda category: (
                TARGET_CATEGORY_PRIORITY.get(category, 99),
                category,
            ),
        )
        return [
            {
                "value": category,
                "label": CATEGORY_LABELS.get(category, category),
            }
            for category in ordered
        ]

    def _distance_provider(
        self,
        start_node_id: str,
        target_node_id: str,
        strategy: str,
    ) -> float:
        return float(
            self.router.query_distance(
                start_node_id,
                target_node_id,
                strategy=strategy,
                site_id=self.site_id,
            )
        )

    def _normalize_start_node(self, value: Any) -> str:
        node_id = normalize_text(value)
        if node_id and node_id in self.graph.nodes:
            return node_id
        return self.default_start_node

    def _normalize_limit(self, value: Any, *, default: int = 6) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(limit, 20))

    def _normalize_strategy(self, value: Any) -> str:
        normalized = normalize_text(value)
        if normalized == "shortest_time":
            return "shortest_time"
        return "shortest_distance"

    def _normalize_transport_mode(self, value: Any) -> str | None:
        normalized = normalize_text(value).casefold()
        if normalized in {"", "any", "all", "none", "不限交通方式"}:
            return None
        return normalized

    def _decorate_query_response(
        self,
        response: dict[str, Any],
        *,
        source: str,
    ) -> dict[str, Any]:
        items = response.get("results", response.get("data", []))
        decorated_items = [self._decorate_result_item(item) for item in items]
        decorated = response.copy()
        decorated["data"] = decorated_items
        decorated["results"] = decorated_items
        decorated["ui"] = {
            "source": source,
            "routeable_result_count": sum(
                1 for item in decorated_items if item.get("route_target_node_id")
            ),
            "mappable_result_count": sum(
                1 for item in decorated_items if item.get("has_map_location")
            ),
        }
        return decorated

    def _decorate_result_item(self, item: dict[str, Any]) -> dict[str, Any]:
        copied = item.copy()
        category = normalize_text(copied.get("category")) or "diary"
        route_target_node_id = self._resolve_target_node_id(copied)
        copied["category_label"] = CATEGORY_LABELS.get(category, category if category != "diary" else "日记")
        copied["route_target_node_id"] = route_target_node_id
        copied["route_target_name"] = self._resolve_node_name(route_target_node_id) if route_target_node_id else ""
        copied["has_map_location"] = route_target_node_id in self.map_node_index
        return copied

    def _resolve_target_node_id(self, item: dict[str, Any]) -> str:
        for field_name in ("route_target_node_id", "target_node_id", "node_id", "map_node_id", "destination_node_id"):
            value = normalize_text(item.get(field_name))
            if value:
                return value
        return ""

    def _resolve_node_name(self, node_id: str) -> str:
        if not node_id:
            return ""
        node_data = self.graph.nodes.get(node_id, {})
        return normalize_text(node_data.get("name")) or node_id

    def _build_route_overlay(self, route: dict[str, Any]) -> dict[str, Any]:
        path = route.get("path", [])
        mappable_path_node_ids = [node_id for node_id in path if node_id in self.map_node_index]
        unmapped_path_node_ids = [node_id for node_id in path if node_id not in self.map_node_index]
        return {
            "mappable_path_node_ids": mappable_path_node_ids,
            "mappable_path_nodes": [
                self.map_node_index[node_id]
                for node_id in mappable_path_node_ids
            ],
            "unmapped_path_node_ids": unmapped_path_node_ids,
            "highlight_node_ids": [
                route.get("start_node_id"),
                route.get("target_node_id"),
            ],
            "caption": self._build_route_caption(route, unmapped_path_node_ids),
        }

    def _build_route_caption(
        self,
        route: dict[str, Any],
        unmapped_path_node_ids: list[str],
    ) -> str:
        base = (
            f"{normalize_text(route.get('start_node_name'))} -> "
            f"{normalize_text(route.get('target_node_name'))}"
        )
        if not unmapped_path_node_ids:
            return f"{base} 的整条路径都已在地图区高亮。"

        indoor_names = [
            self._resolve_node_name(node_id)
            for node_id in unmapped_path_node_ids
        ]
        return (
            f"{base} 的室外段已高亮；室内段请看右侧步骤卡片。"
            f" 未直接绘制的节点：{', '.join(indoor_names)}。"
        )

    @staticmethod
    def format_distance(distance_m: Any) -> str:
        if distance_m is None:
            return "未知"
        try:
            return f"{float(distance_m):.1f} m"
        except (TypeError, ValueError):
            return "未知"

    @staticmethod
    def format_duration(seconds: Any) -> str:
        if seconds is None:
            return "未知"
        try:
            total_seconds = int(round(float(seconds)))
        except (TypeError, ValueError):
            return "未知"

        minutes, remaining_seconds = divmod(total_seconds, 60)
        if minutes <= 0:
            return f"{remaining_seconds} 秒"
        return f"{minutes} 分 {remaining_seconds} 秒"

