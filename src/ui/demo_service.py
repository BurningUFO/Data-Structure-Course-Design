"""Web demo UI service layer.

This module keeps the web demo thin:
- reuse search / recommend / routing business APIs directly
- provide a UI-friendly bootstrap payload
- normalize route overlays for the simple campus map
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.diary.diary_service import DiaryService, load_diary_records
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
from src.search.response import build_error_response, build_success_response


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
    "multi_route": [
        {"label": "图书馆 + 食堂", "target_node_ids": ["library", "canteen"]},
        {"label": "便利店 + 图书馆 + 食堂", "target_node_ids": ["convenience_store", "library", "canteen"]},
        {"label": "图书馆 + 宿舍 101", "target_node_ids": ["library", "dorm1_room_101"]},
    ],
    "aigc": [
        {"label": "秋日燕园", "sample_id": "aigc_sample_001"},
        {"label": "食堂美食", "sample_id": "aigc_sample_002"},
        {"label": "图书馆攻略", "sample_id": "aigc_sample_003"},
    ],
}

FEATURE_NAVIGATION = [
    {
        "id": "scenic",
        "label": "综合查询",
        "description": "查询景点、建筑和推荐对象，并可从结果进入路径规划。",
        "status": "ready",
    },
    {
        "id": "place",
        "label": "场所查询",
        "description": "按类别查找洗手间、便利店、教学楼等服务设施，并按真实路径距离排序。",
        "status": "ready",
    },
    {
        "id": "catering",
        "label": "美食推荐",
        "description": "按热度、评分、距离和菜系筛选餐饮地点。",
        "status": "ready",
    },
    {
        "id": "route",
        "label": "导航规划",
        "description": "规划单目标和多目标路径，展示访问顺序、总距离、总时间和关键步骤。",
        "status": "ready",
    },
    {
        "id": "diary",
        "label": "日记中心",
        "description": "支持全文检索，并已补齐创建、编辑、删除和评分业务接口。",
        "status": "ready",
    },
    {
        "id": "aigc",
        "label": "AIGC 演示",
        "description": "用图片占位和文字描述生成轻量分镜预览，当前不调用真实模型。",
        "status": "ready",
    },
    {
        "id": "help",
        "label": "帮助说明",
        "description": "查看系统演示链路、启动方式和页面操作提示。",
        "status": "ready",
    },
]

HELP_CONTENT = {
    "stage": "正式产品演示版 · 地图方案 B M7",
    "launch_command": "py -B -m src.ui.demo_server",
    "fallback_launch_command": "python -B -m src.ui.demo_server",
    "browser_url": "http://127.0.0.1:8765",
    "demo_flow": [
        "在首页确认当前站点和数据规模统计。",
        "进入主要网站后，先用地图区的 Leaflet / SVG 按钮展示双渲染器对比。",
        "点击地图区的演示单目标或演示多目标按钮，固定走可复现的答辩路线。",
        "进入综合查询，搜索图书馆或宿舍，并从结果规划单目标路线。",
        "进入场所查询或美食推荐，查看按真实路径距离排序的结果。",
        "进入日记中心，执行全文检索，或创建一条带评分和媒体占位的新日记。",
        "从日记结果载入编辑、更新评分，并从绑定目的地跳转到路线规划。",
        "进入 AIGC 演示，选择图片占位并输入文字描述，查看模板化分镜预览。",
    ],
    "checks": [
        "站点选择器已出现在主入口，当前远端数据只有 PKU 一个站点。",
        "主导航已固定为正式产品的页面结构。",
        "查询、推荐、路径、日记和 AIGC 轻量预览保持主链路可演示。",
    ],
    "map_acceptance": [
        "Leaflet GeoJSON 层默认展示真实瓦片底图、节点、道路和路线；SVG 简图作为现场可切换 fallback。",
        "底图可在真实瓦片和无底图之间切换，弱网时本地 GeoJSON 图层仍可展示。",
        "地图数据由现有图节点和边转换为 GeoJSON，坐标顺序统一为 [lng, lat]。",
        "M7 只接入 Leaflet tile layer，不继续扩大真实道路数据或路由算法改动。",
        "路线贴路能力通过 route_geojson 和 route_geometry_stats 说明，缺失 geometry 的边继续用直线段兜底。",
    ],
}

STATE_POLICY = {
    "site_switch_supported": True,
    "reset_on_site_change": [
        "current_results",
        "current_route",
        "focused_node",
        "forms",
        "map_highlight",
    ],
    "feedback_states": [
        "ready",
        "loading",
        "success",
        "empty",
        "error",
    ],
}

FEEDBACK_MESSAGES = {
    "ready": "页面就绪，可以从主导航选择功能。",
    "site_switching": "正在切换站点并重置页面状态...",
    "site_switched": "站点已切换，查询结果、路径和地图高亮已重置。",
    "query_loading": "正在查询，请稍候...",
    "query_empty": "查询成功，但当前没有命中结果。",
    "route_loading": "正在规划路径，请稍候...",
    "route_unreachable": "当前路径不可达，请更换起点、终点或交通方式。",
}

MAP_CAPABILITIES = {
    "renderers": ["simple_svg", "leaflet_geo"],
    "default_renderer": "leaflet_geo",
    "geojson_endpoint": "/api/map/geojson",
    "fallback_renderer": "simple_svg",
    "basemaps": {
        "default": "real_map",
        "fallback": "none",
        "modes": [
            {
                "id": "real_map",
                "label": "真实底图",
                "source": "OpenStreetMap 标准瓦片",
                "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
                "network_required": True,
                "max_zoom": 19,
                "usage_note": "仅适合低频课程演示；长期生产应切换合规瓦片服务或自托管。",
            },
            {
                "id": "none",
                "label": "无底图",
                "source": "本地空白底图",
                "tile_url": "",
                "attribution": "",
                "network_required": False,
                "max_zoom": 19,
                "usage_note": "网络异常或瓦片服务不可用时保留本地 GeoJSON 道路、节点和路线展示。",
            },
        ],
    },
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
        self.diary_service = DiaryService(records=self.diary_records)
        self.outdoor_graph_source = self._load_outdoor_graph_source(self.site_id)
        self.map_nodes = self._build_map_nodes(self.outdoor_graph_source)
        self.map_node_index = {node["id"]: node for node in self.map_nodes}
        self.map_edges = self._build_map_edges(self.outdoor_graph_source)
        self.map_edge_lookup = self._build_map_edge_lookup(self.map_edges)
        self.start_nodes = self._build_start_nodes()
        self.default_start_node = self._resolve_default_start_node()
        self.route_targets = self._build_route_targets()
        self.scenic_categories = self._build_scenic_categories()
        self.aigc_samples = self._load_aigc_samples()

    def get_bootstrap_payload(self) -> dict[str, Any]:
        """Return all static data needed by the one-page UI."""
        map_geometry_stats = self._build_map_geometry_stats()
        return {
            "product": {
                "name": "智能校园导览系统",
                "stage": "正式产品演示版",
            },
            "sites": self._build_site_options(),
            "site": self.site_meta,
            "navigation": FEATURE_NAVIGATION,
            "help": HELP_CONTENT,
            "state_policy": STATE_POLICY,
            "feedback_messages": FEEDBACK_MESSAGES,
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
                "aigc_styles": self._build_aigc_style_options(),
            },
            "aigc_samples": self._build_aigc_sample_options(),
            "presets": DEFAULT_PRESETS,
            "map_renderer": MAP_CAPABILITIES["default_renderer"],
            "map_capabilities": MAP_CAPABILITIES.copy(),
            "map": {
                "nodes": self.map_nodes,
                "edges": self.map_edges,
                "bounds": self._build_map_bounds(self.map_nodes),
                "node_count": len(self.map_nodes),
                "edge_count": len(self.map_edges),
                "geometry_edge_count": map_geometry_stats["geometry_edge_count"],
                "fallback_edge_count": map_geometry_stats["fallback_edge_count"],
                "geometry_coverage_ratio": map_geometry_stats["geometry_coverage_ratio"],
            },
            "stats": {
                "route_target_count": len(self.route_targets),
                "record_count": len(self.site_records),
                "diary_count": len(self.diary_service.records),
                "aigc_sample_count": len(self.aigc_samples),
                "site_count": len(load_global_sites()),
                "indoor_target_count": sum(
                    1 for item in self.route_targets if item["graph_type"] == "indoor"
                ),
            },
        }

    def get_map_geojson_payload(self) -> dict[str, Any]:
        """Return outdoor nodes and edges as a GeoJSON FeatureCollection."""
        features: list[dict[str, Any]] = []

        for node in self.map_nodes:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [node["lng"], node["lat"]],
                    },
                    "properties": {
                        "kind": "node",
                        "id": node["id"],
                        "name": node["name"],
                        "category": node["category"],
                        "category_label": node["category_label"],
                    },
                }
            )

        fallback_edge_count = 0
        edge_feature_count = 0
        for edge in self.map_edges:
            coordinates, used_fallback = self._build_edge_geojson_coordinates(edge)
            if len(coordinates) < 2:
                continue
            if used_fallback:
                fallback_edge_count += 1
            edge_feature_count += 1
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                    "properties": {
                        "kind": "edge",
                        "from": edge["from"],
                        "to": edge["to"],
                        "name": edge["name"],
                        "edge_type": edge["type"],
                        "distance_m": edge["distance_m"],
                        "geometry_source": "fallback_line" if used_fallback else "edge_geometry",
                        "is_fallback_geometry": used_fallback,
                    },
                }
            )

        node_feature_count = len(self.map_nodes)
        geometry_edge_count = edge_feature_count - fallback_edge_count
        geometry_coverage_ratio = (
            round(geometry_edge_count / edge_feature_count, 4)
            if edge_feature_count
            else 0.0
        )
        return {
            "success": True,
            "site_id": self.site_id,
            "geojson": {
                "type": "FeatureCollection",
                "features": features,
            },
            "stats": {
                "node_feature_count": node_feature_count,
                "edge_feature_count": edge_feature_count,
                "geometry_edge_count": geometry_edge_count,
                "fallback_edge_count": fallback_edge_count,
                "geometry_coverage_ratio": geometry_coverage_ratio,
                "feature_count": len(features),
            },
        }

    def _build_site_options(self) -> list[dict[str, Any]]:
        sites = []
        for site in load_global_sites():
            site_id = normalize_text(site.get("id"))
            sites.append(
                {
                    "id": site_id,
                    "name": normalize_text(site.get("name")) or site_id,
                    "description": normalize_text(site.get("description")),
                    "location": normalize_text(site.get("location")),
                    "is_current": site_id == self.site_id,
                    "sub_graphs": site.get("sub_graphs", []),
                }
            )
        return sites

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
        response = self.diary_service.search_fulltext(
            normalize_text(request.get("query")),
            limit=self._normalize_limit(request.get("limit"), default=6),
        )
        return self._decorate_query_response(response, source="diary_fulltext_search")

    def create_diary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.diary_service.create_diary(payload or {})
        return self._decorate_diary_management_response(response, source="diary_create")

    def update_diary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        diary_id = normalize_text(request.get("id") or request.get("diary_id"))
        updates = request.get("updates")
        if not isinstance(updates, dict):
            updates = {
                key: value
                for key, value in request.items()
                if key not in {"id", "diary_id", "site_id"}
            }
        response = self.diary_service.update_diary(diary_id, updates)
        return self._decorate_diary_management_response(response, source="diary_update")

    def delete_diary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        diary_id = normalize_text(request.get("id") or request.get("diary_id"))
        response = self.diary_service.delete_diary(diary_id)
        return self._decorate_diary_management_response(response, source="diary_delete")

    def rate_diary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        diary_id = normalize_text(request.get("id") or request.get("diary_id"))
        response = self.diary_service.rate_diary(diary_id, request.get("rating"))
        return self._decorate_diary_management_response(response, source="diary_rate")

    def aigc_preview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        sample_id = normalize_text(request.get("sample_id"))
        sample = self._resolve_aigc_sample(sample_id)
        if sample is None:
            return build_error_response(
                f"aigc sample not found: {sample_id}",
                query_type="aigc_preview",
                filters={"sample_id": sample_id},
                metadata=self._build_aigc_metadata(),
            )

        prompt = normalize_text(request.get("prompt")) or normalize_text(sample.get("text_prompt"))
        if not prompt:
            return build_error_response(
                "aigc prompt cannot be empty",
                query_type="aigc_preview",
                filters={"sample_id": sample_id},
                metadata=self._build_aigc_metadata(),
            )

        style = normalize_text(request.get("style")) or normalize_text(sample.get("style")) or "warm_storyboard"
        duration_s = self._normalize_duration(request.get("duration_s"), sample.get("duration_s"))
        preview = self._build_aigc_preview(sample, prompt, style, duration_s)

        return build_success_response(
            data=[preview],
            message="aigc preview generated",
            query_type="aigc_preview",
            filters={
                "sample_id": preview["sample_id"],
                "style": preview["style"],
                "duration_s": preview["duration_s"],
            },
            metadata=self._build_aigc_metadata(),
        )

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

    def plan_multi_route(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        target_node_ids = self._normalize_target_node_ids(request.get("target_node_ids"))
        strategy = self._normalize_strategy(request.get("strategy"))
        transport_mode = self._normalize_transport_mode(request.get("transport_mode"))
        return_to_start = self._normalize_bool(request.get("return_to_start"), default=True)

        if not target_node_ids:
            return {
                "success": False,
                "message": "多目标路径至少需要选择 1 个目标点。",
                "route_type": "multi_target",
            }

        result = self.router.query_multi_target(
            start_node_id=start_node_id,
            target_node_ids=target_node_ids,
            strategy=strategy,
            transport_mode=transport_mode,
            return_to_start=return_to_start,
            site_id=self.site_id,
        )
        if not result.get("success"):
            result["route_type"] = "multi_target"
            return result

        decorated = result.copy()
        decorated["route_type"] = "multi_target"
        decorated["start_node_id"] = start_node_id
        decorated["start_node_name"] = self._resolve_node_name(start_node_id)
        decorated["ui"] = self._build_multi_route_overlay(decorated)
        decorated["summary"] = {
            "distance_text": self.format_distance(decorated.get("total_distance_m")),
            "time_text": self.format_duration(decorated.get("estimated_time_s")),
            "visit_order_text": " -> ".join(decorated.get("visit_order_names", [])),
            "target_count": len(decorated.get("target_node_ids", [])),
            "leg_count": len(decorated.get("leg_results", [])),
            "return_to_start_text": "返回起点" if return_to_start else "不返回起点",
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

    def _load_aigc_samples(self) -> list[dict[str, Any]]:
        sample_path = self._aigc_sample_path()
        if not sample_path.exists():
            return []

        loaded = json.loads(sample_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            return []

        samples: list[dict[str, Any]] = []
        for index, item in enumerate(loaded):
            if not isinstance(item, dict):
                continue
            sample_id = normalize_text(item.get("sample_id")) or f"aigc_sample_{index + 1:03d}"
            samples.append(
                {
                    "sample_id": sample_id,
                    "diary_id": normalize_text(item.get("diary_id")),
                    "image_placeholder": normalize_text(item.get("image_placeholder")),
                    "text_prompt": normalize_text(item.get("text_prompt")),
                    "style": normalize_text(item.get("style")) or "warm_storyboard",
                    "duration_s": self._normalize_duration(item.get("duration_s"), 6),
                    "output_type": normalize_text(item.get("output_type")) or "storyboard",
                    "preview_placeholder": normalize_text(item.get("preview_placeholder")),
                    "status": normalize_text(item.get("status")) or "placeholder_ready",
                }
            )
        return samples

    def _aigc_sample_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "aigc_media_samples.json"

    def _build_aigc_style_options(self) -> list[dict[str, str]]:
        styles = {
            normalize_text(sample.get("style"))
            for sample in self.aigc_samples
            if normalize_text(sample.get("style"))
        }
        if not styles:
            styles = {"warm_storyboard", "food_review", "study_guide"}

        return [
            {
                "value": style,
                "label": self._aigc_style_label(style),
            }
            for style in sorted(styles)
        ]

    def _build_aigc_sample_options(self) -> list[dict[str, Any]]:
        return [
            {
                "sample_id": sample["sample_id"],
                "label": self._aigc_sample_label(sample),
                "diary_id": sample.get("diary_id", ""),
                "image_placeholder": sample.get("image_placeholder", ""),
                "text_prompt": sample.get("text_prompt", ""),
                "style": sample.get("style", ""),
                "duration_s": sample.get("duration_s", 6),
                "output_type": sample.get("output_type", ""),
                "preview_placeholder": sample.get("preview_placeholder", ""),
                "status": sample.get("status", ""),
            }
            for sample in self.aigc_samples
        ]

    def _resolve_aigc_sample(self, sample_id: str) -> dict[str, Any] | None:
        if not self.aigc_samples:
            return None
        if not sample_id:
            return self.aigc_samples[0]
        for sample in self.aigc_samples:
            if normalize_text(sample.get("sample_id")) == sample_id:
                return sample
        return None

    def _build_aigc_preview(
        self,
        sample: dict[str, Any],
        prompt: str,
        style: str,
        duration_s: int,
    ) -> dict[str, Any]:
        sample_id = normalize_text(sample.get("sample_id"))
        image_placeholder = normalize_text(sample.get("image_placeholder"))
        preview_placeholder = normalize_text(sample.get("preview_placeholder"))
        style_label = self._aigc_style_label(style)
        title = f"{style_label} · {self._aigc_sample_label(sample)}"
        storyboard = self._build_aigc_storyboard(prompt, style, duration_s)

        return {
            "id": f"preview_{sample_id}",
            "sample_id": sample_id,
            "diary_id": normalize_text(sample.get("diary_id")),
            "title": title,
            "image_placeholder": image_placeholder,
            "text_prompt": prompt,
            "style": style,
            "style_label": style_label,
            "duration_s": duration_s,
            "output_type": normalize_text(sample.get("output_type")) or "storyboard",
            "preview_placeholder": preview_placeholder,
            "status": "template_preview_ready",
            "prototype_notice": "轻量演示模式：当前只生成模板化预览，不调用真实 AIGC 模型。",
            "prompt_summary": self._summarize_prompt(prompt),
            "storyboard_frames": storyboard,
            "keyframes": [
                {
                    "time_s": frame["time_s"],
                    "visual": frame["visual"],
                }
                for frame in storyboard
            ],
            "generation_pipeline": [
                "读取媒体占位样例",
                "合并用户文字描述与样例风格",
                "按时长切分为轻量分镜",
                "返回可在 Web 中展示的预览结构",
            ],
            "source": {
                "sample_file": str(self._aigc_sample_path()),
                "real_model_called": False,
            },
        }

    def _build_aigc_storyboard(
        self,
        prompt: str,
        style: str,
        duration_s: int,
    ) -> list[dict[str, Any]]:
        style_label = self._aigc_style_label(style)
        frame_count = 4
        step = max(1, round(duration_s / frame_count))
        summary = self._summarize_prompt(prompt)
        frame_templates = [
            ("开场", f"用{style_label}建立场景氛围：{summary}"),
            ("推进", "突出地点、人物动作和路线线索，形成可跟随的游览节奏。"),
            ("重点", "放大体验亮点，并补充文字贴片说明推荐理由。"),
            ("收束", "以导览提示和下一步路线建议结束预览。"),
        ]

        return [
            {
                "frame_index": index,
                "time_s": min(duration_s, (index - 1) * step),
                "title": title,
                "visual": visual,
                "caption": f"{title}镜头：{visual}",
            }
            for index, (title, visual) in enumerate(frame_templates, start=1)
        ]

    def _build_aigc_metadata(self) -> dict[str, Any]:
        return {
            "prototype_mode": "template_preview",
            "real_model_called": False,
            "data_source": {
                "path": str(self._aigc_sample_path()),
                "sample_count": len(self.aigc_samples),
            },
            "input_contract": [
                "sample_id",
                "prompt",
                "style",
                "duration_s",
            ],
            "result_fields": [
                "sample_id",
                "image_placeholder",
                "text_prompt",
                "style",
                "duration_s",
                "preview_placeholder",
                "storyboard_frames",
                "keyframes",
            ],
        }

    @staticmethod
    def _aigc_style_label(style: str) -> str:
        labels = {
            "warm_storyboard": "暖色故事板",
            "food_review": "美食测评",
            "study_guide": "学习攻略",
            "template_animation": "模板动画",
        }
        return labels.get(style, style or "默认风格")

    @staticmethod
    def _aigc_sample_label(sample: dict[str, Any]) -> str:
        sample_id = normalize_text(sample.get("sample_id"))
        prompt = normalize_text(sample.get("text_prompt"))
        if prompt:
            return prompt[:14] + ("..." if len(prompt) > 14 else "")
        return sample_id

    @staticmethod
    def _summarize_prompt(prompt: str) -> str:
        normalized = normalize_text(prompt)
        return normalized[:36] + ("..." if len(normalized) > 36 else "")

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

            map_edge = {
                "from": source,
                "to": target,
                "name": normalize_text(edge.get("name")),
                "type": normalize_text(edge.get("type")) or "outdoor_road",
                "distance_m": float(edge.get("distance", 0)),
            }
            geometry = self._normalize_edge_geometry(edge.get("geometry"))
            if geometry:
                map_edge["geometry"] = geometry
            edges.append(map_edge)

        return edges

    def _build_map_geometry_stats(self) -> dict[str, int | float]:
        edge_count = len(self.map_edges)
        geometry_edge_count = sum(1 for edge in self.map_edges if edge.get("geometry"))
        fallback_edge_count = edge_count - geometry_edge_count
        geometry_coverage_ratio = (
            round(geometry_edge_count / edge_count, 4)
            if edge_count
            else 0.0
        )
        return {
            "geometry_edge_count": geometry_edge_count,
            "fallback_edge_count": fallback_edge_count,
            "geometry_coverage_ratio": geometry_coverage_ratio,
        }

    @staticmethod
    def _build_map_edge_lookup(
        edges: list[dict[str, Any]],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (edge["from"], edge["to"]): edge
            for edge in edges
            if edge.get("from") and edge.get("to")
        }

    def _build_edge_geojson_coordinates(
        self,
        edge: dict[str, Any],
    ) -> tuple[list[list[float]], bool]:
        geometry = edge.get("geometry")
        if isinstance(geometry, list) and len(geometry) >= 2:
            return [[point["lng"], point["lat"]] for point in geometry], False

        source = self.map_node_index.get(edge.get("from"))
        target = self.map_node_index.get(edge.get("to"))
        if not source or not target:
            return [], True
        return [[source["lng"], source["lat"]], [target["lng"], target["lat"]]], True

    @staticmethod
    def _normalize_edge_geometry(value: Any) -> list[dict[str, float]]:
        if not isinstance(value, list):
            return []

        points: list[dict[str, float]] = []
        for point in value:
            if not isinstance(point, dict):
                continue
            lat = point.get("lat")
            lng = point.get("lng")
            if lat is None or lng is None:
                continue
            try:
                points.append({"lat": float(lat), "lng": float(lng)})
            except (TypeError, ValueError):
                continue
        return points if len(points) >= 2 else []

    def _build_route_geojson_feature(
        self,
        route: dict[str, Any],
        route_type: str,
        extra_properties: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, list[list[float]], dict[str, int]]:
        coordinates, stats = self._build_route_line_coordinates(route.get("path", []))
        if len(coordinates) < 2:
            stats["feature_count"] = 0
            stats["coordinate_count"] = len(coordinates)
            return None, coordinates, stats

        properties = {
            "kind": "route",
            "route_type": route_type,
            "start_node_id": normalize_text(route.get("start_node_id")),
            "target_node_id": normalize_text(route.get("target_node_id")),
            "distance_m": route.get("total_distance_m"),
            "estimated_time_s": route.get("estimated_time_s"),
            "fallback_segment_count": stats["fallback_segment_count"],
            "geometry_segment_count": stats["geometry_segment_count"],
            "reverse_edge_reuse_count": stats["reverse_edge_reuse_count"],
        }
        if extra_properties:
            properties.update(extra_properties)

        stats["feature_count"] = 1
        stats["coordinate_count"] = len(coordinates)
        return (
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
                "properties": properties,
            },
            coordinates,
            stats,
        )

    def _build_multi_route_geojson(
        self,
        route: dict[str, Any],
    ) -> tuple[dict[str, Any], list[list[float]], dict[str, int]]:
        features: list[dict[str, Any]] = []
        stitched_coordinates: list[list[float]] = []
        aggregate_stats = self._empty_route_geometry_stats()

        for index, leg in enumerate(route.get("leg_results", []), start=1):
            feature, coordinates, stats = self._build_route_geojson_feature(
                leg,
                route_type="multi_target_leg",
                extra_properties={
                    "leg_index": index,
                    "from_node_id": normalize_text(leg.get("start_node_id")),
                    "to_node_id": normalize_text(leg.get("target_node_id")),
                },
            )
            self._merge_route_geometry_stats(aggregate_stats, stats)
            self._append_route_coordinates(stitched_coordinates, coordinates)
            if feature:
                features.append(feature)

        if not features:
            feature, coordinates, stats = self._build_route_geojson_feature(
                route,
                route_type="multi_target",
            )
            self._merge_route_geometry_stats(aggregate_stats, stats)
            self._append_route_coordinates(stitched_coordinates, coordinates)
            if feature:
                features.append(feature)

        aggregate_stats["feature_count"] = len(features)
        aggregate_stats["coordinate_count"] = len(stitched_coordinates)
        return (
            {
                "type": "FeatureCollection",
                "features": features,
            },
            stitched_coordinates,
            aggregate_stats,
        )

    def _build_route_line_coordinates(
        self,
        path: list[Any],
    ) -> tuple[list[list[float]], dict[str, int]]:
        node_ids = [normalize_text(node_id) for node_id in path if normalize_text(node_id)]
        coordinates: list[list[float]] = []
        stats = self._empty_route_geometry_stats()

        for source, target in zip(node_ids, node_ids[1:]):
            if source not in self.map_node_index or target not in self.map_node_index:
                stats["skipped_unmapped_segment_count"] += 1
                continue

            segment_coordinates, used_fallback, used_reverse, missing_edge = (
                self._resolve_route_segment_coordinates(source, target)
            )
            if len(segment_coordinates) < 2:
                stats["missing_edge_count"] += 1
                continue

            stats["route_segment_count"] += 1
            if used_fallback:
                stats["fallback_segment_count"] += 1
                stats["fallback_edge_count"] += 1
            else:
                stats["geometry_segment_count"] += 1
            if used_reverse:
                stats["reverse_edge_reuse_count"] += 1
            if missing_edge:
                stats["missing_edge_count"] += 1

            self._append_route_coordinates(coordinates, segment_coordinates)

        stats["coordinate_count"] = len(coordinates)
        return coordinates, stats

    def _resolve_route_segment_coordinates(
        self,
        source: str,
        target: str,
    ) -> tuple[list[list[float]], bool, bool, bool]:
        edge = self.map_edge_lookup.get((source, target))
        used_reverse = False

        if edge is None:
            edge = self.map_edge_lookup.get((target, source))
            used_reverse = edge is not None

        if edge is not None:
            coordinates, used_fallback = self._build_edge_geojson_coordinates(edge)
            if used_reverse:
                coordinates = list(reversed(coordinates))
            return coordinates, used_fallback, used_reverse, False

        source_node = self.map_node_index.get(source)
        target_node = self.map_node_index.get(target)
        if not source_node or not target_node:
            return [], True, False, True
        return (
            [
                [source_node["lng"], source_node["lat"]],
                [target_node["lng"], target_node["lat"]],
            ],
            True,
            False,
            True,
        )

    @staticmethod
    def _empty_route_geometry_stats() -> dict[str, int]:
        return {
            "route_segment_count": 0,
            "geometry_segment_count": 0,
            "fallback_segment_count": 0,
            "fallback_edge_count": 0,
            "reverse_edge_reuse_count": 0,
            "missing_edge_count": 0,
            "skipped_unmapped_segment_count": 0,
            "feature_count": 0,
            "coordinate_count": 0,
        }

    @staticmethod
    def _merge_route_geometry_stats(
        target: dict[str, int],
        source: dict[str, int],
    ) -> None:
        for key in (
            "route_segment_count",
            "geometry_segment_count",
            "fallback_segment_count",
            "fallback_edge_count",
            "reverse_edge_reuse_count",
            "missing_edge_count",
            "skipped_unmapped_segment_count",
        ):
            target[key] += int(source.get(key, 0))

    @classmethod
    def _append_route_coordinates(
        cls,
        target: list[list[float]],
        coordinates: list[list[float]],
    ) -> None:
        if not coordinates:
            return
        if target and cls._same_geojson_coordinate(target[-1], coordinates[0]):
            target.extend(coordinates[1:])
            return
        target.extend(coordinates)

    @staticmethod
    def _same_geojson_coordinate(left: list[float], right: list[float]) -> bool:
        return (
            len(left) == 2
            and len(right) == 2
            and abs(left[0] - right[0]) < 1e-9
            and abs(left[1] - right[1]) < 1e-9
        )

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

    def _normalize_duration(self, value: Any, default: Any = 6) -> int:
        try:
            duration = int(value)
        except (TypeError, ValueError):
            try:
                duration = int(default)
            except (TypeError, ValueError):
                duration = 6
        return max(3, min(duration, 15))

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

    def _normalize_target_node_ids(self, value: Any) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            candidates = [normalize_text(item) for item in value]
        else:
            normalized = normalize_text(value)
            for separator in ("，", "、", ";", "\n", "\t"):
                normalized = normalized.replace(separator, ",")
            candidates = [item.strip() for item in normalized.split(",")]

        node_ids: list[str] = []
        seen: set[str] = set()
        for node_id in candidates:
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            node_ids.append(node_id)
        return node_ids

    def _normalize_bool(self, value: Any, *, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        normalized = normalize_text(value).casefold()
        if normalized in {"1", "true", "yes", "y", "on", "返回起点"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "不返回"}:
            return False
        return default

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

    def _decorate_diary_management_response(
        self,
        response: dict[str, Any],
        *,
        source: str,
    ) -> dict[str, Any]:
        self.diary_records = self.diary_service.records
        items = response.get("results", response.get("data", []))
        decorated_items = [self._decorate_result_item(item) for item in items]
        routeable_count = sum(
            1 for item in decorated_items if item.get("route_target_node_id")
        )
        mappable_count = sum(
            1 for item in decorated_items if item.get("has_map_location")
        )

        metadata = dict(response.get("metadata") or {})
        metadata["site_id"] = self.site_id
        metadata["ui_contract"] = {
            "route_hint_field": "route_target_node_id",
            "media_fields": ["images", "videos"],
            "write_back": False,
        }

        decorated = response.copy()
        decorated["data"] = decorated_items
        decorated["results"] = decorated_items
        decorated["metadata"] = metadata
        decorated["ui"] = {
            "source": source,
            "storage_mode": metadata.get("storage_mode", "memory_only"),
            "record_count": len(self.diary_service.records),
            "routeable_result_count": routeable_count,
            "mappable_result_count": mappable_count,
        }
        return decorated

    def _decorate_result_item(self, item: dict[str, Any]) -> dict[str, Any]:
        copied = item.copy()
        diary_id = normalize_text(copied.get("diary_id"))
        if diary_id:
            copied = self._merge_diary_record_fields(copied, diary_id)
        category = normalize_text(copied.get("category")) or "diary"
        route_target_node_id = self._resolve_target_node_id(copied)
        copied["category_label"] = CATEGORY_LABELS.get(category, category if category != "diary" else "日记")
        copied["route_target_node_id"] = route_target_node_id
        copied["route_target_name"] = self._resolve_node_name(route_target_node_id) if route_target_node_id else ""
        copied["has_map_location"] = route_target_node_id in self.map_node_index
        return copied

    def _merge_diary_record_fields(
        self,
        item: dict[str, Any],
        diary_id: str,
    ) -> dict[str, Any]:
        for record in self.diary_service.records:
            if normalize_text(record.get("id")) != diary_id:
                continue

            merged = record.copy()
            merged.update(item)
            for field_name in ("content", "images", "videos", "tags", "author_id", "author_name"):
                if not merged.get(field_name) and record.get(field_name):
                    merged[field_name] = record[field_name]
            return merged
        return item

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
        route_geojson, route_line_coordinates, route_geometry_stats = self._build_route_geojson_feature(
            route,
            route_type="single_target",
        )
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
            "route_geojson": route_geojson,
            "route_line_coordinates": route_line_coordinates,
            "route_geometry_stats": route_geometry_stats,
            "stats": {
                "route_geometry": route_geometry_stats,
            },
        }

    def _build_multi_route_overlay(self, route: dict[str, Any]) -> dict[str, Any]:
        path = route.get("path", [])
        mappable_path_node_ids = [node_id for node_id in path if node_id in self.map_node_index]
        unmapped_path_node_ids = [node_id for node_id in path if node_id not in self.map_node_index]
        visit_order = route.get("visit_order", [])
        leg_summaries = []
        display_steps = []

        for index, leg in enumerate(route.get("leg_results", []), start=1):
            leg_steps = leg.get("path_steps", [])
            leg_summaries.append(
                {
                    "leg_index": index,
                    "start_node_id": leg.get("start_node_id"),
                    "target_node_id": leg.get("target_node_id"),
                    "start_node_name": leg.get("start_node_name"),
                    "target_node_name": leg.get("target_node_name"),
                    "distance_text": self.format_distance(leg.get("total_distance_m")),
                    "time_text": self.format_duration(leg.get("estimated_time_s")),
                    "step_count": len(leg_steps),
                    "path_node_names": leg.get("path_node_names", []),
                }
            )
            for step in leg_steps:
                copied_step = step.copy()
                copied_step["leg_index"] = index
                display_steps.append(copied_step)

        route_geojson, route_line_coordinates, route_geometry_stats = self._build_multi_route_geojson(route)
        return {
            "mappable_path_node_ids": mappable_path_node_ids,
            "mappable_path_nodes": [
                self.map_node_index[node_id]
                for node_id in mappable_path_node_ids
            ],
            "unmapped_path_node_ids": unmapped_path_node_ids,
            "highlight_node_ids": [node_id for node_id in visit_order if node_id],
            "caption": self._build_multi_route_caption(route, unmapped_path_node_ids),
            "leg_summaries": leg_summaries,
            "display_steps": display_steps,
            "route_geojson": route_geojson,
            "route_line_coordinates": route_line_coordinates,
            "route_geometry_stats": route_geometry_stats,
            "stats": {
                "route_geometry": route_geometry_stats,
            },
        }

    def _build_multi_route_caption(
        self,
        route: dict[str, Any],
        unmapped_path_node_ids: list[str],
    ) -> str:
        visit_order_text = " -> ".join(route.get("visit_order_names", []))
        base = f"多目标访问顺序：{visit_order_text}。"
        if not unmapped_path_node_ids:
            return f"{base} 路径已在地图区高亮。"

        indoor_names = [
            self._resolve_node_name(node_id)
            for node_id in unmapped_path_node_ids
        ]
        return (
            f"{base} 室外段已在地图区高亮；室内段请看右侧步骤卡片。"
            f" 未直接绘制的节点：{', '.join(indoor_names)}。"
        )

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

