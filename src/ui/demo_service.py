"""Web demo UI service layer.

This module keeps the web demo thin:
- reuse search / recommend / routing business APIs directly
- provide a UI-friendly bootstrap payload
- normalize route overlays for the simple campus map
"""

from __future__ import annotations

import base64
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.diary.diary_service import DiaryService, load_diary_records
from src.graph.loader import GraphLoader
from src.recommend.catering_service import recommend_catering
from src.recommend.interest import (
    build_user_options,
    collect_interest_options,
    is_interest_sort_field,
    load_users,
    normalize_interest_list,
    resolve_user_by_id,
    resolve_user_interests,
)
from src.routing.router import Router
from src.search.search_service import (
    PLACE_CATEGORY_SET,
    get_default_site_id,
    get_site_graph_paths,
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
    "shopping": "便利店 / 购物",
    "sports": "运动",
    "restroom": "洗手间",
    "parking": "停车",
    "building": "建筑",
    "building_entrance": "楼门",
    "hall": "大厅",
    "reading_room": "阅览室",
    "service": "服务",
    "passage": "通道",
    "road": "道路",
}

TRANSPORT_MODE_LABELS = {
    None: "兼容模式",
    "walk": "步行",
    "bike": "自行车",
    "mixed": "步行 + 自行车最短时间",
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
    "building": 10,
    "building_entrance": 11,
    "entrance": 12,
    "parking": 13,
    "passage": 14,
    "road": 15,
}

LABEL_PRIORITY_BY_CATEGORY = {
    "entrance": 90,
    "education": 86,
    "landmark": 82,
    "catering": 78,
    "sports": 74,
    "shopping": 70,
    "restroom": 66,
    "dormitory": 62,
    "parking": 58,
    "building": 56,
    "building_entrance": 55,
    "hall": 54,
    "reading_room": 50,
    "service": 46,
    "passage": 36,
    "road": 10,
}

INDOOR_FLOORPLAN_RENDERER = "svg_floorplan"
INDOOR_FLOORPLAN_VERSION = "m20_realistic_floorplan_v1"
INDOOR_FLOORPLAN_PASSAGE_CATEGORIES = {"passage"}
INDOOR_FLOORPLAN_ROOM_DIMENSIONS = {
    "lobby": (116, 80),
    "corridor_node": (74, 48),
    "restroom": (68, 56),
    "elevator": (60, 54),
    "stairs": (66, 58),
    "reading_room": (118, 72),
    "education": (108, 66),
    "dormitory": (86, 58),
    "catering": (112, 62),
    "sports": (124, 76),
    "service": (98, 58),
    "generic": (92, 58),
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
        "id": "route",
        "label": "导航规划",
        "description": "规划单目标和多目标路径，展示访问顺序、总距离、总时间和关键步骤。",
        "status": "ready",
    },
    {
        "id": "place",
        "label": "场所与美食",
        "description": "按类别查找洗手间、便利店、教学楼等服务设施，并查看餐饮推荐结果。",
        "status": "ready",
    },
    {
        "id": "diary",
        "label": "日记中心",
        "description": "支持浏览推荐、全文检索，并已补齐创建、编辑、删除和评分业务接口。",
        "status": "ready",
    },
    {
        "id": "aigc",
        "label": "AIGC 预览",
        "description": "选择本地图片样例并输入文字描述，直接浏览 GIF 分镜预览。",
        "status": "ready",
    },
    {
        "id": "help",
        "label": "帮助与演示",
        "description": "查看系统演示链路、启动方式、页面操作提示和冻结版口径。",
        "status": "ready",
    },
]

HELP_CONTENT = {
    "stage": "第13周正式产品冻结版 · 地图方案 B M14",
    "launch_command": "py -B -m src.ui.demo_server",
    "fallback_launch_command": "python -B -m src.ui.demo_server",
    "browser_url": "http://127.0.0.1:8765",
    "demo_flow": [
        "在首页确认当前站点和数据规模统计。",
        "进入主要网站后，先用地图区的 Leaflet / SVG 按钮展示双渲染器对比。",
        "点击地图区的演示单目标或演示多目标按钮，固定走可复现的答辩路线。",
        "进入综合查询，搜索图书馆或宿舍，并从结果规划单目标路线。",
        "进入场所与美食，先查询附近设施，再展开美食推荐，查看按真实路径距离排序的结果。",
        "进入日记中心，执行全文检索，或创建一条带评分和媒体占位的新日记。",
        "从日记结果载入编辑、更新评分，并从绑定目的地跳转到路线规划。",
        "进入 AIGC 演示，选择样例并输入文字描述，查看模板化分镜预览。",
    ],
    "checks": [
        "站点选择器已出现在主入口，PKU 为深度导航核心站点，扩展校园用于站点切换和课程规模演示。",
        "主导航已固定为正式产品的页面结构，入口顺序以综合查询、导航规划、场所与美食、日记中心、AIGC 预览、帮助与演示为准。",
        "查询、推荐、路径、日记和 AIGC 轻量预览保持主链路可演示。",
    ],
    "map_acceptance": [
        "Leaflet GeoJSON 层默认展示真实瓦片底图、POI、弱化路网点、道路和路线；SVG 简图作为现场可切换 fallback。",
        "底图可在真实瓦片和无底图之间切换，弱网时本地 GeoJSON 图层仍可展示。",
        "地图数据由课程图节点和边转换为 GeoJSON，坐标顺序统一为 [lng, lat]。",
        "M14 只沿本地 OSM 白线道路相邻节点建立室外边，每条边带可渲染 geometry。",
        "POI 只通过短接驳边连接到自己的 road_access 接驳点，课程图仍是路由权威。",
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
    "osm_layers_endpoint": "/api/map/osm-layers",
    "fallback_renderer": "simple_svg",
    "osm_layers": {
        "default_visible": {
            "roads": True,
            "buildings": True,
            "water_landuse": True,
        },
        "layers": [
            {
                "id": "roads",
                "label": "OSM 道路",
                "file": "osm_roads_simplified.geojson",
                "source": "本地 OSM 派生 GeoJSON",
            },
            {
                "id": "buildings",
                "label": "建筑",
                "file": "osm_buildings.geojson",
                "source": "本地 OSM 派生 GeoJSON",
            },
            {
                "id": "water_landuse",
                "label": "水域 / 绿地",
                "file": "osm_water_landuse.geojson",
                "source": "本地 OSM 派生 GeoJSON",
            },
        ],
    },
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
                "usage_note": "网络异常或瓦片服务不可用时保留本地 GeoJSON 道路、POI 和路线展示。",
            },
        ],
    },
}

OSM_LAYER_FILES = {
    "roads": "osm_roads_simplified.geojson",
    "buildings": "osm_buildings.geojson",
    "water_landuse": "osm_water_landuse.geojson",
}

OSM_METADATA_FILE = "osm_extract_metadata.json"
OSM_EDGE_MATCHES_FILE = "edge_osm_geometry_matches.json"
DEFAULT_NEARBY_RADIUS_OPTIONS = (200, 500, 800, 1200)
AIGC_GENERATED_STATIC_DIR = Path(__file__).resolve().parent / "static" / "generated" / "aigc"
AIGC_GENERATED_URL_PREFIX = "/generated/aigc"
AIGC_MAX_FRAME_COUNT = 4
AIGC_OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"
AIGC_OPENAI_IMAGE_TIMEOUT_S = 45
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-1"


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
        self.site_records = self._filter_searchable_site_records(load_site_records(self.site_id))
        self.diary_records = load_diary_records()
        self.diary_service = DiaryService(records=self.diary_records)
        self.users = load_users(site_id=self.site_id)
        self.outdoor_graph_source = self._load_outdoor_graph_source(self.site_id)
        self.outdoor_metadata = self._load_outdoor_metadata()
        self.map_nodes = self._build_map_nodes(self.outdoor_graph_source)
        self.map_node_index = {node["id"]: node for node in self.map_nodes}
        self.osm_edge_matches, self.osm_edge_match_warnings = self._load_osm_edge_geometry_matches()
        self.osm_edge_match_lookup = self._build_osm_edge_match_lookup(self.osm_edge_matches)
        self.map_edges = self._build_map_edges(self.outdoor_graph_source)
        self.map_edge_lookup = self._build_map_edge_lookup(self.map_edges)
        self.indoor_template_catalog = self._load_indoor_template_catalog()
        self.indoor_template_lookup = {
            normalize_text(item.get("template_id")): item
            for item in self.indoor_template_catalog
            if normalize_text(item.get("template_id"))
        }
        self.indoor_building_registry = self._load_indoor_building_registry()
        self.indoor_building_lookup = {
            normalize_text(item.get("building_id")): item
            for item in self.indoor_building_registry
            if normalize_text(item.get("building_id"))
        }
        self.indoor_graph_lookup = {
            normalize_text(item.get("indoor_graph_id")): item
            for item in self.indoor_building_registry
            if normalize_text(item.get("indoor_graph_id"))
        }
        self.indoor_graph_sources = self._load_indoor_graph_sources()
        self.start_nodes = self._build_start_nodes()
        self.default_start_node = self._resolve_default_start_node()
        self.route_targets = self._build_route_targets()
        self.nearby_radius_options = self._build_nearby_radius_options()
        self.nearby_profiles = self._build_nearby_profiles()
        self.scenic_categories = self._build_scenic_categories()
        self.aigc_samples = self._load_aigc_samples()

    def get_bootstrap_payload(self) -> dict[str, Any]:
        """Return all static data needed by the one-page UI."""
        map_geometry_stats = self._build_map_geometry_stats()
        map_capabilities = json.loads(json.dumps(MAP_CAPABILITIES, ensure_ascii=False))
        indoor_buildings = self._build_indoor_building_summaries()
        map_capabilities["indoor_map_endpoint"] = "/api/map/indoor"
        map_capabilities["indoor_navigation"] = bool(self.indoor_building_registry)
        map_capabilities["indoor_buildings"] = indoor_buildings
        map_capabilities["indoor_supported_buildings"] = indoor_buildings
        map_capabilities["indoor_supported_building_count"] = len(indoor_buildings)
        return {
            "product": {
                "name": "智能校园导览系统",
                "stage": "正式产品演示版",
            },
            "sites": self._build_site_options(),
            "site": self.site_meta,
            "users": self._build_user_options(),
            "default_user_id": self._resolve_default_user_id(),
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
                "scenic_sort_options": [
                    {"value": "interest", "label": "按兴趣综合"},
                    {"value": "heat", "label": "按热度"},
                    {"value": "rating", "label": "按评分"},
                    {"value": "distance_m", "label": "按真实距离"},
                ],
                "diary_sort_options": [
                    {"value": "interest", "label": "按兴趣推荐"},
                    {"value": "heat", "label": "按热度"},
                    {"value": "rating", "label": "按评分"},
                    {"value": "views", "label": "按浏览量"},
                    {"value": "created_at", "label": "按发布时间"},
                ],
                "interest_options": collect_interest_options(self.users),
                "nearby_radius_options": self.nearby_radius_options,
                "nearby_profiles": self.nearby_profiles,
                "route_strategies": [
                    {"value": "shortest_distance", "label": "最短距离"},
                    {"value": "shortest_time", "label": "最短时间"},
                ],
                "transport_modes": [
                    {"value": "walk", "label": "步行"},
                    {"value": "bike", "label": "自行车"},
                    {"value": "mixed", "label": "步行 + 自行车最短时间"},
                ],
                "aigc_styles": self._build_aigc_style_options(),
            },
            "aigc_samples": self._build_aigc_sample_options(),
            "presets": DEFAULT_PRESETS,
            "map_renderer": MAP_CAPABILITIES["default_renderer"],
            "map_capabilities": map_capabilities,
            "indoor_buildings": indoor_buildings,
            "map": {
                "nodes": self.map_nodes,
                "edges": self.map_edges,
                "bounds": self._build_map_bounds(self.map_nodes),
                "node_count": len(self.map_nodes),
                "poi_node_count": sum(1 for node in self.map_nodes if not node["is_waypoint"]),
                "waypoint_node_count": sum(1 for node in self.map_nodes if node["is_waypoint"]),
                "edge_count": len(self.map_edges),
                "geometry_edge_count": map_geometry_stats["geometry_edge_count"],
                "osm_matched_edge_count": map_geometry_stats["osm_matched_edge_count"],
                "manual_geometry_edge_count": map_geometry_stats["manual_geometry_edge_count"],
                "fallback_edge_count": map_geometry_stats["fallback_edge_count"],
                "geometry_coverage_ratio": map_geometry_stats["geometry_coverage_ratio"],
                "osm_matched_coverage_ratio": map_geometry_stats["osm_matched_coverage_ratio"],
            },
            "stats": {
                "route_target_count": len(self.route_targets),
                "record_count": len(self.site_records),
                "diary_count": len(self.diary_service.records),
                "aigc_sample_count": len(self.aigc_samples),
                "site_count": len(load_global_sites()),
                "user_count": len(self.users),
                "indoor_target_count": sum(
                    1 for item in self.route_targets if item["graph_type"] == "indoor"
                ),
                "indoor_building_count": len(self.indoor_building_registry),
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
                        "display_role": node["display_role"],
                        "is_waypoint": node["is_waypoint"],
                        "label_priority": node["label_priority"],
                        "show_label": node["show_label"],
                        "is_searchable": node["is_searchable"],
                        **self._build_node_extra_properties(node),
                    },
                }
            )

        edge_feature_count = 0
        source_counts = {
            "osm_matched": 0,
            "manual": 0,
            "fallback_line": 0,
        }
        for edge in self.map_edges:
            coordinates, geometry_source = self._build_edge_geojson_coordinates(edge)
            if len(coordinates) < 2:
                continue
            source_counts[geometry_source] = source_counts.get(geometry_source, 0) + 1
            edge_feature_count += 1
            is_fallback_geometry = geometry_source == "fallback_line"
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
                        "vehicle_access": edge.get("vehicle_access", "all"),
                        "allowed_transports": edge.get("allowed_transports", []),
                        "transport_semantics": edge.get("transport_semantics", ""),
                        "m21_demo_role": edge.get("m21_demo_role", ""),
                        "geometry_source": geometry_source,
                        "geometry_confidence": edge.get("geometry_confidence"),
                        "osm_way_ids": edge.get("osm_way_ids", []),
                        "source_osm_id": edge.get("source_osm_id"),
                        "source_highway": edge.get("source_highway"),
                        "is_fallback_geometry": is_fallback_geometry,
                    },
                }
            )

        node_feature_count = len(self.map_nodes)
        osm_matched_edge_count = source_counts["osm_matched"]
        manual_geometry_edge_count = source_counts["manual"]
        fallback_edge_count = source_counts["fallback_line"]
        geometry_edge_count = osm_matched_edge_count + manual_geometry_edge_count
        geometry_coverage_ratio = (
            round(geometry_edge_count / edge_feature_count, 4)
            if edge_feature_count
            else 0.0
        )
        osm_matched_coverage_ratio = (
            round(osm_matched_edge_count / edge_feature_count, 4)
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
                "poi_node_count": sum(1 for node in self.map_nodes if not node["is_waypoint"]),
                "waypoint_node_count": sum(1 for node in self.map_nodes if node["is_waypoint"]),
                "edge_feature_count": edge_feature_count,
                "geometry_edge_count": geometry_edge_count,
                "osm_matched_edge_count": osm_matched_edge_count,
                "manual_geometry_edge_count": manual_geometry_edge_count,
                "fallback_edge_count": fallback_edge_count,
                "geometry_coverage_ratio": geometry_coverage_ratio,
                "osm_matched_coverage_ratio": osm_matched_coverage_ratio,
                "feature_count": len(features),
            },
        }

    def get_osm_layers_payload(self) -> dict[str, Any]:
        """Return local OSM-derived contextual layers for the Leaflet renderer."""
        layers: dict[str, Any] = {}
        layer_stats: dict[str, Any] = {}
        warnings: list[dict[str, str]] = []
        missing_files: list[str] = []

        for layer_id, file_name in OSM_LAYER_FILES.items():
            path = self._osm_geo_dir() / file_name
            geojson, warning = self._load_osm_feature_collection(path)
            if warning:
                warnings.append(
                    {
                        "layer": layer_id,
                        "file": file_name,
                        "message": warning,
                    }
                )
                if "missing" in warning:
                    missing_files.append(file_name)

            feature_count = len(geojson.get("features", []))
            layers[layer_id] = geojson
            layer_stats[layer_id] = {
                "file": file_name,
                "feature_count": feature_count,
                "available": feature_count > 0,
                "geometry_types": self._count_geojson_geometry_types(geojson),
            }

        metadata, metadata_warning = self._load_osm_metadata()
        if metadata_warning:
            warnings.append(
                {
                    "layer": "metadata",
                    "file": OSM_METADATA_FILE,
                    "message": metadata_warning,
                }
            )
            missing_files.append(OSM_METADATA_FILE)

        return {
            "success": True,
            "site_id": self.site_id,
            "layers": layers,
            "metadata": metadata,
            "stats": {
                "layers": layer_stats,
                "roads_feature_count": layer_stats["roads"]["feature_count"],
                "buildings_feature_count": layer_stats["buildings"]["feature_count"],
                "water_landuse_feature_count": layer_stats["water_landuse"]["feature_count"],
                "feature_count": sum(item["feature_count"] for item in layer_stats.values()),
                "available_layer_count": sum(1 for item in layer_stats.values() if item["available"]),
                "missing_files": missing_files,
                "missing_file_count": len(missing_files),
            },
            "warnings": warnings,
        }

    def get_indoor_map_payload(
        self,
        building_id: str,
        floor_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_building_id = normalize_text(building_id)
        building_entry = self.indoor_building_lookup.get(normalized_building_id)
        if building_entry is None:
            return {
                "success": False,
                "site_id": self.site_id,
                "message": f"building not found or indoor navigation unsupported: {normalized_building_id}",
            }

        indoor_graph_id = normalize_text(building_entry.get("indoor_graph_id"))
        graph_data = self.indoor_graph_sources.get(indoor_graph_id)
        if graph_data is None:
            return {
                "success": False,
                "site_id": self.site_id,
                "message": f"indoor graph missing: {indoor_graph_id}",
            }

        default_floor_id = normalize_text(building_entry.get("default_floor_id")) or "F1"
        available_floors = self._build_available_floor_summaries(
            graph_data,
            default_floor_id=default_floor_id,
        )
        available_floor_ids = {item["floor_id"] for item in available_floors}
        requested_floor_id = normalize_text(floor_id)
        if requested_floor_id and requested_floor_id not in available_floor_ids:
            return {
                "success": False,
                "site_id": self.site_id,
                "building_id": normalized_building_id,
                "message": f"floor not found for building {normalized_building_id}: {requested_floor_id}",
            }

        current_floor_id = requested_floor_id or default_floor_id
        if current_floor_id not in available_floor_ids and available_floors:
            current_floor_id = available_floors[0]["floor_id"]

        current_floor = {
            "id": current_floor_id,
            "label": self._floor_label_for_id(current_floor_id),
        }

        current_nodes = [
            {
                "id": normalize_text(node.get("id")),
                "name": normalize_text(node.get("name")),
                "type": normalize_text(node.get("type")),
                "category": normalize_text(node.get("category")),
                "category_label": CATEGORY_LABELS.get(
                    normalize_text(node.get("category")),
                    normalize_text(node.get("category")),
                ),
                "floor_id": normalize_text(node.get("floor_id")),
                "floor_label": normalize_text(node.get("floor_label")) or current_floor["label"],
                "layout": node.get("layout", {}),
                "is_gate": bool(node.get("is_gate", False)),
                "description": normalize_text(node.get("description")),
                "facilities": list(node.get("facilities", [])),
                "tags": node.get("tags", []),
            }
            for node in graph_data.get("nodes", [])
            if normalize_text(node.get("floor_id")) == current_floor_id
        ]
        current_node_ids = {node["id"] for node in current_nodes}
        current_edges = [
            {
                "from": normalize_text(edge.get("from")),
                "to": normalize_text(edge.get("to")),
                "distance_m": float(edge.get("distance", 0)),
                "edge_type": normalize_text(edge.get("type")) or "indoor_path",
                "name": normalize_text(edge.get("name")),
                "description": normalize_text(edge.get("description")),
                "vehicle_access": normalize_text(edge.get("vehicle_access")) or "pedestrian_only",
                "from_floor_id": current_floor_id,
                "to_floor_id": current_floor_id,
                "from_floor_label": current_floor["label"],
                "to_floor_label": current_floor["label"],
                "is_cross_floor_transition": False,
            }
            for edge in graph_data.get("edges", [])
            if normalize_text(edge.get("from")) in current_node_ids
            and normalize_text(edge.get("to")) in current_node_ids
        ]
        floorplan, node_rendering = self._build_indoor_floorplan(
            current_nodes,
            current_edges,
            current_floor,
            building_entry,
        )
        for node in current_nodes:
            render_fields = node_rendering.get(node["id"])
            if render_fields:
                node.update(render_fields)

        zones = [
            node
            for node in current_nodes
            if node["category"] not in {"passage", "hall"}
        ]

        return {
            "success": True,
            "site_id": self.site_id,
            "building_id": normalized_building_id,
            "building_name": normalize_text(building_entry.get("building_name")) or normalized_building_id,
            "entry_node_id": normalize_text(building_entry.get("entry_node_id")),
            "indoor_graph_id": indoor_graph_id,
            "template_id": normalize_text(building_entry.get("template_id")),
            "template_name": normalize_text(
                self.indoor_template_lookup.get(normalize_text(building_entry.get("template_id")), {}).get("template_name")
            ),
            "available_floors": [
                {
                    **item,
                    "id": item["floor_id"],
                    "label": item["floor_label"],
                }
                for item in available_floors
            ],
            "current_floor": current_floor,
            "current_floor_id": current_floor["id"],
            "nodes": current_nodes,
            "edges": current_edges,
            "zones": zones,
            "floorplan": floorplan,
            "stats": {
                "node_count": len(current_nodes),
                "edge_count": len(current_edges),
                "zone_count": len(zones),
                "floor_count": len(available_floors),
                "floorplan_room_count": floorplan["stats"]["room_count"],
                "floorplan_corridor_count": floorplan["stats"]["corridor_count"],
                "floorplan_icon_count": floorplan["stats"]["icon_count"],
            },
        }

    def _build_indoor_floorplan(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        current_floor: dict[str, str],
        building_entry: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        node_points = {
            normalize_text(node.get("id")): point
            for node in nodes
            if (point := self._indoor_layout_point(node)) is not None
        }
        node_lookup = {
            normalize_text(node.get("id")): node
            for node in nodes
            if normalize_text(node.get("id"))
        }
        room_rects: dict[str, dict[str, Any]] = {}
        node_rendering: dict[str, dict[str, Any]] = {}

        for node_id, node in node_lookup.items():
            point = node_points.get(node_id)
            if point is None:
                continue

            zone_type = self._indoor_floorplan_zone_type(node)
            icon_type = self._indoor_floorplan_icon_type(node)
            label_anchor = {"x": point[0], "y": point[1] + 6}
            render_fields = {
                "zone_type": zone_type,
                "zone_shape": "point",
                "icon_type": icon_type,
                "label_anchor": label_anchor,
            }

            if self._should_render_indoor_floorplan_room(node, zone_type):
                width, height = self._indoor_floorplan_room_dimensions(zone_type)
                rect = self._indoor_rect_from_center(point[0], point[1], width, height)
                room_rects[node_id] = rect
                render_fields.update(
                    {
                        "zone_shape": "polygon",
                        "polygon": rect["polygon"],
                        "label_anchor": {"x": point[0], "y": point[1] + height * 0.18},
                    }
                )
            elif zone_type == "corridor":
                render_fields["corridor_segment"] = {
                    "x": point[0],
                    "y": point[1],
                    "width": 44,
                }

            node_rendering[node_id] = render_fields

        corridors = []
        doors_by_node: dict[str, list[dict[str, Any]]] = {}
        seen_edge_keys: set[str] = set()

        for edge in edges:
            from_id = normalize_text(edge.get("from"))
            to_id = normalize_text(edge.get("to"))
            if not from_id or not to_id or from_id == to_id:
                continue
            from_point = node_points.get(from_id)
            to_point = node_points.get(to_id)
            if from_point is None or to_point is None:
                continue

            edge_key = "::".join(sorted((from_id, to_id)))
            if edge_key in seen_edge_keys:
                continue
            seen_edge_keys.add(edge_key)

            corridor_width = self._indoor_corridor_width(edge)
            start = self._indoor_connect_point(room_rects.get(from_id), from_point, to_point)
            end = self._indoor_connect_point(room_rects.get(to_id), to_point, from_point)
            if self._indoor_points_equal(start, end):
                continue
            orthogonal_path = self._indoor_orthogonal_path(start, end)

            corridors.append(
                {
                    "id": f"corridor:{edge_key}",
                    "edge_key": edge_key,
                    "from": from_id,
                    "to": to_id,
                    "name": normalize_text(edge.get("name")),
                    "edge_type": normalize_text(edge.get("edge_type")) or "indoor_path",
                    "width": corridor_width,
                    "segment": [self._round_point(start), self._round_point(end)],
                    "path": [self._round_point(point) for point in orthogonal_path],
                    "is_orthogonal": self._is_indoor_orthogonal_path(orthogonal_path),
                    "turn_count": max(len(orthogonal_path) - 2, 0),
                    "polygon": self._indoor_band_polygon(start, end, corridor_width),
                }
            )

            for node_id, point, other_point in (
                (from_id, from_point, to_point),
                (to_id, to_point, from_point),
            ):
                rect = room_rects.get(node_id)
                if rect is None:
                    continue
                door = self._build_indoor_door(
                    node_id=node_id,
                    edge_key=edge_key,
                    rect=rect,
                    center=point,
                    toward=other_point,
                    edge_to=to_id if node_id == from_id else from_id,
                )
                doors_by_node.setdefault(node_id, []).append(door)

        rooms = []
        walls = []
        icons = []
        labels = []
        all_points: list[tuple[float, float]] = []

        for room in room_rects.values():
            all_points.extend((float(x), float(y)) for x, y in room["polygon"])
        for corridor in corridors:
            all_points.extend((float(x), float(y)) for x, y in corridor["polygon"])
        all_points.extend(node_points.values())

        if all_points:
            min_x = min(point[0] for point in all_points) - 42
            min_y = min(point[1] for point in all_points) - 42
            max_x = max(point[0] for point in all_points) + 42
            max_y = max(point[1] for point in all_points) + 42
        else:
            min_x, min_y, max_x, max_y = 0.0, 0.0, 360.0, 260.0

        view_box = {
            "x": round(min_x, 2),
            "y": round(min_y, 2),
            "width": round(max(max_x - min_x, 320), 2),
            "height": round(max(max_y - min_y, 240), 2),
        }
        outer_shell = self._indoor_rect_from_bounds(
            view_box["x"] + 14,
            view_box["y"] + 14,
            view_box["x"] + view_box["width"] - 14,
            view_box["y"] + view_box["height"] - 14,
        )
        walls.extend(self._indoor_wall_segments("outer", outer_shell["polygon"], "outer"))

        for node_id, rect in room_rects.items():
            node = node_lookup[node_id]
            render_fields = node_rendering[node_id]
            door_positions = doors_by_node.get(node_id, [])
            render_fields["door_positions"] = [
                {
                    "x": door["x"],
                    "y": door["y"],
                    "edge_to": door["edge_to"],
                    "side": door["side"],
                }
                for door in door_positions
            ]
            room = {
                "id": f"room:{node_id}",
                "node_id": node_id,
                "name": normalize_text(node.get("name")) or node_id,
                "category": normalize_text(node.get("category")),
                "category_label": normalize_text(node.get("category_label"))
                or CATEGORY_LABELS.get(normalize_text(node.get("category")), ""),
                "zone_type": render_fields["zone_type"],
                "zone_shape": "polygon",
                "icon_type": render_fields["icon_type"],
                "is_gate": bool(node.get("is_gate")),
                "is_targetable": normalize_text(node.get("category")) not in INDOOR_FLOORPLAN_PASSAGE_CATEGORIES,
                "polygon": rect["polygon"],
                "label_anchor": render_fields["label_anchor"],
                "door_positions": door_positions,
            }
            rooms.append(room)
            walls.extend(self._indoor_wall_segments(node_id, rect["polygon"], "room"))
            icons.append(
                {
                    "id": f"icon:{node_id}",
                    "node_id": node_id,
                    "type": render_fields["icon_type"],
                    "x": round(float(rect["x"]), 2),
                    "y": round(float(rect["y"]) - float(rect["height"]) * 0.18, 2),
                }
            )
            labels.append(
                {
                    "id": f"label:{node_id}",
                    "node_id": node_id,
                    "text": normalize_text(node.get("name")) or node_id,
                    "x": round(float(render_fields["label_anchor"]["x"]), 2),
                    "y": round(float(render_fields["label_anchor"]["y"]), 2),
                    "priority": LABEL_PRIORITY_BY_CATEGORY.get(normalize_text(node.get("category")), 20),
                }
            )

        doors = [
            door
            for node_doors in doors_by_node.values()
            for door in node_doors
        ]

        floorplan = {
            "renderer": INDOOR_FLOORPLAN_RENDERER,
            "version": INDOOR_FLOORPLAN_VERSION,
            "units": "layout_px",
            "building_id": normalize_text(building_entry.get("building_id")),
            "building_name": normalize_text(building_entry.get("building_name")),
            "floor_id": current_floor["id"],
            "floor_label": current_floor["label"],
            "view_box": view_box,
            "outer_shell": {
                "polygon": outer_shell["polygon"],
            },
            "rooms": rooms,
            "corridors": corridors,
            "walls": walls,
            "doors": doors,
            "icons": icons,
            "labels": labels,
            "route_overlay": {
                "source": "indoor_route_views.path_segments",
                "edge_key_field": "edge_key",
                "aligns_to": "corridors.path",
            },
            "stats": {
                "room_count": len(rooms),
                "corridor_count": len(corridors),
                "wall_count": len(walls),
                "door_count": len(doors),
                "icon_count": len(icons),
                "label_count": len(labels),
            },
        }
        return floorplan, node_rendering

    @staticmethod
    def _indoor_layout_point(node: dict[str, Any]) -> tuple[float, float] | None:
        layout = node.get("layout")
        if not isinstance(layout, dict):
            return None
        try:
            x = float(layout.get("x"))
            y = float(layout.get("y"))
        except (TypeError, ValueError):
            return None
        return x, y

    @staticmethod
    def _indoor_floorplan_zone_type(node: dict[str, Any]) -> str:
        category = normalize_text(node.get("category"))
        node_type = normalize_text(node.get("type"))
        name = normalize_text(node.get("name"))
        tags = " ".join(str(item) for item in (node.get("tags") or []))
        facilities = " ".join(str(item) for item in (node.get("facilities") or []))
        text = f"{name} {tags} {facilities}"

        if bool(node.get("is_gate")) or category == "hall" or "入口" in text or "大厅" in text:
            return "lobby"
        if category == "restroom" or "洗手间" in text or "卫生间" in text:
            return "restroom"
        if node_type == "elevator" or "电梯" in text:
            return "elevator"
        if node_type == "staircase" or "楼梯" in text:
            return "stairs"
        if category == "passage" or "走廊" in text or "通道" in text:
            return "corridor"
        if category == "reading_room":
            return "reading_room"
        if category in {"education", "dormitory", "catering", "sports", "service"}:
            return category
        return "generic"

    @staticmethod
    def _indoor_floorplan_icon_type(node: dict[str, Any]) -> str:
        zone_type = DemoUIService._indoor_floorplan_zone_type(node)
        if zone_type in {"restroom", "elevator", "stairs", "lobby", "reading_room", "dormitory", "catering", "sports"}:
            return zone_type
        if zone_type == "education":
            return "classroom"
        if zone_type == "service":
            return "service"
        return "area"

    @staticmethod
    def _should_render_indoor_floorplan_room(node: dict[str, Any], zone_type: str) -> bool:
        return zone_type != "corridor" or bool(node.get("is_gate"))

    @staticmethod
    def _indoor_floorplan_room_dimensions(zone_type: str) -> tuple[float, float]:
        return INDOOR_FLOORPLAN_ROOM_DIMENSIONS.get(
            zone_type,
            INDOOR_FLOORPLAN_ROOM_DIMENSIONS["generic"],
        )

    @staticmethod
    def _indoor_corridor_width(edge: dict[str, Any]) -> float:
        edge_type = normalize_text(edge.get("edge_type"))
        if edge_type in {"elevator", "stairs"}:
            return 34.0
        return 44.0

    @staticmethod
    def _indoor_rect_from_center(x: float, y: float, width: float, height: float) -> dict[str, Any]:
        left = x - width / 2
        top = y - height / 2
        right = x + width / 2
        bottom = y + height / 2
        return DemoUIService._indoor_rect_from_bounds(left, top, right, bottom)

    @staticmethod
    def _indoor_rect_from_bounds(left: float, top: float, right: float, bottom: float) -> dict[str, Any]:
        width = right - left
        height = bottom - top
        center_x = left + width / 2
        center_y = top + height / 2
        return {
            "x": round(center_x, 2),
            "y": round(center_y, 2),
            "width": round(width, 2),
            "height": round(height, 2),
            "left": round(left, 2),
            "right": round(right, 2),
            "top": round(top, 2),
            "bottom": round(bottom, 2),
            "polygon": [
                [round(left, 2), round(top, 2)],
                [round(right, 2), round(top, 2)],
                [round(right, 2), round(bottom, 2)],
                [round(left, 2), round(bottom, 2)],
            ],
        }

    @staticmethod
    def _indoor_connect_point(
        rect: dict[str, Any] | None,
        center: tuple[float, float],
        toward: tuple[float, float],
    ) -> tuple[float, float]:
        if rect is None:
            return center

        dx = toward[0] - center[0]
        dy = toward[1] - center[1]
        if abs(dx) >= abs(dy):
            x = float(rect["right"] if dx >= 0 else rect["left"])
            y = center[1] if dx == 0 else center[1] + dy * ((x - center[0]) / dx)
            y = min(max(y, float(rect["top"]) + 10), float(rect["bottom"]) - 10)
            return x, y

        y = float(rect["bottom"] if dy >= 0 else rect["top"])
        x = center[0] if dy == 0 else center[0] + dx * ((y - center[1]) / dy)
        x = min(max(x, float(rect["left"]) + 10), float(rect["right"]) - 10)
        return x, y

    @classmethod
    def _indoor_orthogonal_path(
        cls,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> list[tuple[float, float]]:
        if cls._indoor_points_equal(start, end):
            return [start]
        if abs(start[0] - end[0]) < 0.001 or abs(start[1] - end[1]) < 0.001:
            return [start, end]

        if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
            bend = (end[0], start[1])
        else:
            bend = (start[0], end[1])

        path = [start, bend, end]
        compacted = [path[0]]
        for point in path[1:]:
            if not cls._indoor_points_equal(compacted[-1], point):
                compacted.append(point)
        return compacted

    @classmethod
    def _is_indoor_orthogonal_path(cls, path: list[tuple[float, float]]) -> bool:
        if len(path) < 2:
            return True
        for start, end in zip(path, path[1:]):
            if cls._indoor_points_equal(start, end):
                continue
            if abs(start[0] - end[0]) >= 0.001 and abs(start[1] - end[1]) >= 0.001:
                return False
        return True

    @staticmethod
    def _indoor_band_polygon(
        start: tuple[float, float],
        end: tuple[float, float],
        width: float,
    ) -> list[list[float]]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length <= 0:
            return []
        nx = -dy / length * width / 2
        ny = dx / length * width / 2
        return [
            [round(start[0] + nx, 2), round(start[1] + ny, 2)],
            [round(end[0] + nx, 2), round(end[1] + ny, 2)],
            [round(end[0] - nx, 2), round(end[1] - ny, 2)],
            [round(start[0] - nx, 2), round(start[1] - ny, 2)],
        ]

    @staticmethod
    def _build_indoor_door(
        node_id: str,
        edge_key: str,
        rect: dict[str, Any],
        center: tuple[float, float],
        toward: tuple[float, float],
        edge_to: str,
    ) -> dict[str, Any]:
        point = DemoUIService._indoor_connect_point(rect, center, toward)
        left = abs(point[0] - float(rect["left"]))
        right = abs(point[0] - float(rect["right"]))
        top = abs(point[1] - float(rect["top"]))
        bottom = abs(point[1] - float(rect["bottom"]))
        side = min(
            (("left", left), ("right", right), ("top", top), ("bottom", bottom)),
            key=lambda item: item[1],
        )[0]
        half_width = 9.0
        if side in {"left", "right"}:
            segment = [
                [round(point[0], 2), round(point[1] - half_width, 2)],
                [round(point[0], 2), round(point[1] + half_width, 2)],
            ]
        else:
            segment = [
                [round(point[0] - half_width, 2), round(point[1], 2)],
                [round(point[0] + half_width, 2), round(point[1], 2)],
            ]
        return {
            "id": f"door:{node_id}:{edge_key}",
            "node_id": node_id,
            "edge_key": edge_key,
            "edge_to": edge_to,
            "kind": "room_door",
            "side": side,
            "x": round(point[0], 2),
            "y": round(point[1], 2),
            "segment": segment,
        }

    @staticmethod
    def _indoor_wall_segments(
        owner_id: str,
        polygon: list[list[float]],
        wall_type: str,
    ) -> list[dict[str, Any]]:
        segments = []
        if len(polygon) < 2:
            return segments
        for index, point in enumerate(polygon):
            next_point = polygon[(index + 1) % len(polygon)]
            segments.append(
                {
                    "id": f"wall:{owner_id}:{index}",
                    "owner_id": owner_id,
                    "wall_type": wall_type,
                    "points": [point, next_point],
                }
            )
        return segments

    @staticmethod
    def _round_point(point: tuple[float, float]) -> list[float]:
        return [round(point[0], 2), round(point[1], 2)]

    @staticmethod
    def _indoor_points_equal(left: tuple[float, float], right: tuple[float, float]) -> bool:
        return abs(left[0] - right[0]) < 0.001 and abs(left[1] - right[1]) < 0.001

    def _build_site_options(self) -> list[dict[str, Any]]:
        sites = []
        for site in load_global_sites():
            site_id = normalize_text(site.get("id"))
            is_available, data_status = self._resolve_site_status(site)
            sites.append(
                {
                    "id": site_id,
                    "name": normalize_text(site.get("name")) or site_id,
                    "description": normalize_text(site.get("description")),
                    "location": normalize_text(site.get("location")),
                    "is_current": site_id == self.site_id,
                    "is_available": is_available,
                    "data_status": data_status,
                    "sub_graphs": site.get("sub_graphs", []),
                }
            )
        return sites

    @staticmethod
    def _resolve_site_status(site: dict[str, Any]) -> tuple[bool, str]:
        site_id = normalize_text(site.get("id"))
        explicit_data_status = normalize_text(site.get("data_status"))
        explicit_is_available = site.get("is_available")
        if isinstance(explicit_is_available, bool):
            is_available = explicit_is_available
            data_status = explicit_data_status or ("available" if is_available else "scaffold_only")
        elif explicit_data_status == "scaffold_only":
            is_available = False
            data_status = explicit_data_status
        else:
            is_available = bool(get_site_graph_paths(site_id))
            data_status = explicit_data_status or ("available" if is_available else "scaffold_only")
        return is_available, data_status

    def _build_user_options(self) -> list[dict[str, Any]]:
        return build_user_options(self.users)

    def _resolve_default_user_id(self) -> str:
        options = self._build_user_options()
        if not options:
            return ""
        for option in options:
            if option.get("is_default"):
                return normalize_text(option.get("id"))
        return normalize_text(options[0].get("id"))

    def _resolve_interest_context(self, request: dict[str, Any]) -> dict[str, Any]:
        user_id = normalize_text(request.get("user_id") or request.get("current_user_id"))
        requested_interests = normalize_interest_list(
            request.get("interests")
            or request.get("interest_tags")
            or request.get("interest_text")
        )
        selected_user = resolve_user_by_id(self.users, user_id)
        user_interests = resolve_user_interests(self.users, user_id)
        interests = requested_interests or user_interests

        return {
            "user_id": user_id,
            "user_name": normalize_text(selected_user.get("name")) if selected_user else "",
            "role": normalize_text(selected_user.get("role")) if selected_user else "",
            "interests": interests,
            "source": "custom_interests" if requested_interests else ("user_profile" if user_interests else "none"),
        }

    @staticmethod
    def _attach_interest_context(
        response: dict[str, Any],
        interest_context: dict[str, Any],
    ) -> dict[str, Any]:
        if not interest_context.get("user_id") and not interest_context.get("interests"):
            return response

        decorated = response.copy()
        filters = dict(decorated.get("filters") or {})
        filters["user_id"] = interest_context.get("user_id", "")
        filters["interests"] = list(interest_context.get("interests", []))
        decorated["filters"] = filters

        metadata = dict(decorated.get("metadata") or {})
        metadata["user_interest_context"] = {
            "user_id": interest_context.get("user_id", ""),
            "user_name": interest_context.get("user_name", ""),
            "role": interest_context.get("role", ""),
            "interests": list(interest_context.get("interests", [])),
            "source": interest_context.get("source", "none"),
        }
        decorated["metadata"] = metadata
        return decorated

    def scenic_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        interest_context = self._resolve_interest_context(request)
        sort_field = normalize_text(request.get("sort_field")) or "heat"
        response = search_and_recommend(
            keyword=normalize_text(request.get("keyword")),
            category=normalize_text(request.get("category")),
            start_node_id=start_node_id,
            match_mode="fuzzy",
            sort_field=sort_field,
            limit=self._normalize_limit(request.get("limit"), default=6),
            records=self.site_records,
            distance_provider=self._distance_provider,
            use_default_distance_provider=False,
            interests=interest_context["interests"],
            allow_empty_query=is_interest_sort_field(sort_field),
        )
        response = self._attach_interest_context(response, interest_context)
        return self._decorate_query_response(response, source="scenic_search")

    def place_search(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        start_node_id = self._normalize_start_node(request.get("start_node_id"))
        center_node_id = normalize_text(request.get("center_node_id"))
        if center_node_id and center_node_id not in self.graph.nodes:
            return build_error_response(
                "center_node_id is not a valid node in current site",
                query_type="place_search",
                filters={
                    "site_id": self.site_id,
                    "center_node_id": center_node_id,
                },
            )
        response = search_places(
            keyword=normalize_text(request.get("keyword")),
            category=normalize_text(request.get("category")),
            site_id=self.site_id,
            start_node_id=start_node_id,
            center_node_id=center_node_id,
            radius_m=self._normalize_radius_m(request.get("radius_m")),
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

    def diary_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = payload or {}
        interest_context = self._resolve_interest_context(request)
        sort_field = normalize_text(request.get("sort_field")) or (
            "interest" if interest_context["interests"] else "heat"
        )
        response = self.diary_service.search(
            keyword=normalize_text(request.get("keyword")),
            destination=normalize_text(request.get("destination")),
            match_mode="fuzzy",
            sort_field=sort_field,
            sort_order=normalize_text(request.get("sort_order")),
            limit=self._normalize_limit(request.get("limit"), default=6),
            interests=interest_context["interests"],
        )
        response = response.copy()
        response["query_type"] = "diary_list"
        if response.get("success"):
            response["message"] = (
                "diary recommendation success"
                if is_interest_sort_field(sort_field) and interest_context["interests"]
                else "diary list success"
            )
        response = self._attach_interest_context(response, interest_context)
        return self._decorate_query_response(response, source="diary_list")

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
        mode = self._normalize_aigc_mode(request.get("mode"))
        provider = self._normalize_aigc_provider(request.get("provider"))
        frame_count = self._normalize_aigc_frame_count(request.get("frame_count"))
        if sample is None:
            return build_error_response(
                f"aigc sample not found: {sample_id}",
                query_type="aigc_preview",
                filters={"sample_id": sample_id},
                metadata=self._build_aigc_metadata(generation_mode=mode),
            )

        prompt = normalize_text(request.get("prompt")) or normalize_text(sample.get("text_prompt"))
        if not prompt:
            return build_error_response(
                "aigc prompt cannot be empty",
                query_type="aigc_preview",
                filters={"sample_id": sample_id},
                metadata=self._build_aigc_metadata(generation_mode=mode),
            )

        style = normalize_text(request.get("style")) or normalize_text(sample.get("style")) or "warm_storyboard"
        duration_s = self._normalize_duration(request.get("duration_s"), sample.get("duration_s"))
        preview = self._build_aigc_preview(
            sample,
            prompt,
            style,
            duration_s,
            frame_count=frame_count,
        )
        message = "aigc preview generated"
        metadata = self._build_aigc_metadata(generation_mode=preview["generation_mode"])

        if mode == "live_image":
            preview, message = self._build_aigc_live_image_preview(
                preview,
                sample,
                prompt,
                style,
                duration_s,
                frame_count,
                provider,
            )
            metadata = self._build_aigc_metadata(
                generation_mode=preview["generation_mode"],
                provider=provider,
                real_model_called=preview["source"]["real_model_called"],
                fallback_used=preview["fallback_used"],
            )

        return build_success_response(
            data=[preview],
            message=message,
            query_type="aigc_preview",
            filters={
                "sample_id": preview["sample_id"],
                "style": preview["style"],
                "duration_s": preview["duration_s"],
                "mode": mode,
                "provider": provider,
                "frame_count": frame_count,
            },
            metadata=metadata,
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
            "transport_text": self._transport_mode_label(transport_mode),
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
            "transport_text": self._transport_mode_label(transport_mode),
            "strategy_text": "最短时间" if strategy == "shortest_time" else "最短距离",
        }
        return decorated

    def _load_site_meta(self, site_id: str) -> dict[str, Any]:
        for site in load_global_sites():
            if normalize_text(site.get("id")) == site_id:
                is_available, data_status = self._resolve_site_status(site)
                return {
                    "id": site_id,
                    "name": normalize_text(site.get("name")) or site_id,
                    "description": normalize_text(site.get("description")),
                    "location": normalize_text(site.get("location")),
                    "is_available": is_available,
                    "data_status": data_status,
                    "sub_graphs": site.get("sub_graphs", []),
                }
        return {
            "id": site_id,
            "name": site_id,
            "description": "",
            "location": "",
            "is_available": bool(get_site_graph_paths(site_id)),
            "data_status": "available" if get_site_graph_paths(site_id) else "scaffold_only",
            "sub_graphs": [],
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

    def _load_outdoor_metadata(self) -> dict[str, Any]:
        metadata = self.outdoor_graph_source.get("metadata")
        return metadata if isinstance(metadata, dict) else {}

    def _build_nearby_radius_options(self) -> list[dict[str, Any]]:
        raw_options = self.outdoor_metadata.get("nearby_radius_options")
        source_options = raw_options if isinstance(raw_options, list) and raw_options else list(DEFAULT_NEARBY_RADIUS_OPTIONS)
        options: list[dict[str, Any]] = []

        for item in source_options:
            value = item.get("value") if isinstance(item, dict) else item
            label = normalize_text(item.get("label")) if isinstance(item, dict) else ""
            try:
                radius_value = int(float(value))
            except (TypeError, ValueError):
                continue
            if radius_value <= 0 or any(existing["value"] == radius_value for existing in options):
                continue
            options.append(
                {
                    "value": radius_value,
                    "label": label or f"{radius_value} m",
                }
            )

        if options:
            return options
        return [{"value": value, "label": f"{value} m"} for value in DEFAULT_NEARBY_RADIUS_OPTIONS]

    def _build_nearby_profiles(self) -> dict[str, dict[str, Any]]:
        raw_profiles = self.outdoor_metadata.get("nearby_profiles")
        if not isinstance(raw_profiles, list):
            return {}

        profiles: dict[str, dict[str, Any]] = {}
        for item in raw_profiles:
            if not isinstance(item, dict):
                continue
            center_node_id = normalize_text(item.get("center_node_id"))
            if not center_node_id or center_node_id not in self.graph.nodes:
                continue

            default_category = normalize_text(item.get("default_category"))
            if default_category and default_category not in PLACE_CATEGORY_SET:
                default_category = ""

            profiles[center_node_id] = {
                "center_node_id": center_node_id,
                "center_name": self._resolve_node_name(center_node_id) or center_node_id,
                "default_radius_m": float(self._normalize_radius_m(item.get("default_radius_m"))),
                "default_category": default_category,
                "notes": normalize_text(item.get("notes")),
            }

        return profiles

    def _osm_geo_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "sites" / self.site_id / "geo"

    def _indoor_registry_path(self) -> Path:
        return self._osm_geo_dir() / "indoor_building_registry.json"

    def _indoor_template_catalog_path(self) -> Path:
        return self._osm_geo_dir() / "indoor_template_catalog.json"

    def _load_indoor_building_registry(self) -> list[dict[str, Any]]:
        path = self._indoor_registry_path()
        if not path.exists():
            return []
        loaded = json.loads(path.read_text(encoding="utf-8"))
        records = loaded.get("buildings", []) if isinstance(loaded, dict) else []
        return [item for item in records if isinstance(item, dict)]

    def _load_indoor_template_catalog(self) -> list[dict[str, Any]]:
        path = self._indoor_template_catalog_path()
        if not path.exists():
            return []
        loaded = json.loads(path.read_text(encoding="utf-8"))
        records = loaded.get("templates", []) if isinstance(loaded, dict) else []
        return [item for item in records if isinstance(item, dict)]

    def _indoor_graph_path(self, indoor_graph_id: str) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "sites" / self.site_id / f"{indoor_graph_id}.json"

    def _load_indoor_graph_sources(self) -> dict[str, dict[str, Any]]:
        graph_sources: dict[str, dict[str, Any]] = {}
        for item in self.indoor_building_registry:
            indoor_graph_id = normalize_text(item.get("indoor_graph_id"))
            if not indoor_graph_id or indoor_graph_id in graph_sources:
                continue
            path = self._indoor_graph_path(indoor_graph_id)
            if not path.exists():
                continue
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                graph_sources[indoor_graph_id] = loaded
        return graph_sources

    def _build_indoor_building_summaries(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for item in self.indoor_building_registry:
            building_id = normalize_text(item.get("building_id"))
            outdoor_node = self.graph.nodes.get(building_id, {})
            template_id = normalize_text(item.get("template_id"))
            summaries.append(
                {
                    "building_id": building_id,
                    "building_name": normalize_text(item.get("building_name")) or building_id,
                    "entry_node_id": normalize_text(item.get("entry_node_id")),
                    "entry_node_name": self._resolve_node_name(normalize_text(item.get("entry_node_id"))),
                    "indoor_graph_id": normalize_text(item.get("indoor_graph_id")),
                    "template_id": template_id,
                    "template_name": normalize_text(
                        self.indoor_template_lookup.get(template_id, {}).get("template_name")
                    ),
                    "floor_ids": list(item.get("floor_ids", [])),
                    "default_floor_id": normalize_text(item.get("default_floor_id")) or "F1",
                    "building_category": normalize_text(outdoor_node.get("category")),
                    "entry_mapping_reason": normalize_text(item.get("entry_mapping_reason")),
                }
            )
        return summaries

    def _resolve_indoor_building_entry(
        self,
        node_id: str,
        node_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if node_id in self.indoor_building_lookup:
            return self.indoor_building_lookup[node_id]

        explicit_building_id = normalize_text(node_data.get("building_id"))
        if explicit_building_id and explicit_building_id in self.indoor_building_lookup:
            return self.indoor_building_lookup[explicit_building_id]

        indoor_graph_id = (
            normalize_text(node_data.get("indoor_graph_id"))
            or normalize_text(node_data.get("source_sub_graph_id"))
            or normalize_text(node_data.get("sub_graph_id"))
        )
        if indoor_graph_id and indoor_graph_id in self.indoor_graph_lookup:
            return self.indoor_graph_lookup[indoor_graph_id]
        return None

    def _build_indoor_node_context(
        self,
        node_id: str,
        node_data: dict[str, Any],
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        building_entry = self._resolve_indoor_building_entry(node_id, node_data)
        indoor_graph_id = normalize_text(node_data.get("indoor_graph_id"))
        if building_entry is not None:
            context["building_id"] = normalize_text(building_entry.get("building_id")) or node_id
            context["building_name"] = (
                normalize_text(building_entry.get("building_name"))
                or self._resolve_node_name(context["building_id"])
                or context["building_id"]
            )
            context["entry_node_id"] = normalize_text(building_entry.get("entry_node_id"))
            context["entry_node_name"] = self._resolve_node_name(context["entry_node_id"])
            context["indoor_graph_id"] = normalize_text(building_entry.get("indoor_graph_id"))
            context["indoor_entry_node_id"] = normalize_text(building_entry.get("entry_node_id"))
            context["default_floor_id"] = normalize_text(building_entry.get("default_floor_id")) or "F1"
            context["template_id"] = normalize_text(building_entry.get("template_id"))
            context["indoor_supported"] = True
        elif indoor_graph_id:
            context["indoor_graph_id"] = indoor_graph_id
            context["indoor_supported"] = bool(node_data.get("indoor_supported"))
            context["indoor_entry_node_id"] = normalize_text(node_data.get("indoor_entry_node_id"))

        source_sub_graph_id = normalize_text(
            node_data.get("source_sub_graph_id") or node_data.get("sub_graph_id")
        )
        if source_sub_graph_id:
            context["source_sub_graph_id"] = source_sub_graph_id

        floor_id = normalize_text(node_data.get("floor_id"))
        if floor_id:
            context["floor_id"] = floor_id
            context["floor_label"] = (
                normalize_text(node_data.get("floor_label"))
                or self._floor_label_for_id(floor_id)
            )

        layout = node_data.get("layout")
        if isinstance(layout, dict) and layout:
            context["layout"] = layout

        description = normalize_text(node_data.get("description"))
        if description:
            context["description"] = description

        facilities = node_data.get("facilities")
        if isinstance(facilities, list) and facilities:
            context["facilities"] = facilities

        tags = node_data.get("tags")
        if isinstance(tags, list) and tags:
            context["tags"] = tags

        if "is_gate" in node_data:
            context["is_gate"] = bool(node_data.get("is_gate"))

        return context

    @staticmethod
    def _floor_label_for_id(floor_id: str) -> str:
        normalized = normalize_text(floor_id)
        if normalized.startswith("F") and normalized[1:].isdigit():
            return f"{normalized[1:]}F"
        return normalized

    def _build_available_floor_summaries(
        self,
        graph_data: dict[str, Any],
        *,
        default_floor_id: str,
    ) -> list[dict[str, Any]]:
        floor_ids = graph_data.get("floor_ids", [])
        if not isinstance(floor_ids, list):
            floor_ids = []

        floor_nodes: dict[str, list[dict[str, Any]]] = {}
        for node in graph_data.get("nodes", []):
            floor_id = normalize_text(node.get("floor_id"))
            if not floor_id:
                continue
            floor_nodes.setdefault(floor_id, []).append(node)

        summaries = []
        for floor_id in floor_ids or sorted(floor_nodes):
            nodes = floor_nodes.get(floor_id, [])
            zone_count = sum(
                1
                for node in nodes
                if normalize_text(node.get("category")) not in {"passage", "hall"}
            )
            summaries.append(
                {
                    "floor_id": floor_id,
                    "floor_label": self._floor_label_for_id(floor_id),
                    "zone_count": zone_count,
                    "is_default": floor_id == default_floor_id,
                }
            )
        return summaries

    def _load_osm_metadata(self) -> tuple[dict[str, Any], str]:
        metadata_path = self._osm_geo_dir() / OSM_METADATA_FILE
        if not metadata_path.exists():
            return {}, "missing metadata file"
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return {}, f"metadata read failed: {type(error).__name__}: {error}"
        if not isinstance(loaded, dict):
            return {}, "metadata root is not an object"
        return loaded, ""

    def _load_osm_feature_collection(self, path: Path) -> tuple[dict[str, Any], str]:
        if not path.exists():
            return self._empty_feature_collection(), "missing GeoJSON file"
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return self._empty_feature_collection(), f"GeoJSON read failed: {type(error).__name__}: {error}"

        if not isinstance(loaded, dict) or loaded.get("type") != "FeatureCollection":
            return self._empty_feature_collection(), "GeoJSON root is not a FeatureCollection"
        if not isinstance(loaded.get("features"), list):
            return self._empty_feature_collection(), "GeoJSON features field is not a list"
        return loaded, ""

    def _load_osm_edge_geometry_matches(self) -> tuple[list[dict[str, Any]], list[str]]:
        path = self._osm_geo_dir() / OSM_EDGE_MATCHES_FILE
        if not path.exists():
            return [], [f"missing {OSM_EDGE_MATCHES_FILE}"]
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return [], [f"edge match read failed: {type(error).__name__}: {error}"]

        if not isinstance(loaded, dict):
            return [], ["edge match root is not an object"]

        raw_matches = loaded.get("matches")
        if not isinstance(raw_matches, list):
            return [], ["edge match matches field is not a list"]

        matches: list[dict[str, Any]] = []
        warnings: list[str] = []
        for index, item in enumerate(raw_matches):
            match = self._normalize_osm_edge_match(item)
            if match:
                matches.append(match)
            else:
                warnings.append(f"skipped invalid edge match at index {index}")
        return matches, warnings

    def _normalize_osm_edge_match(self, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}

        source = normalize_text(item.get("from"))
        target = normalize_text(item.get("to"))
        if not source or not target:
            edge_key = normalize_text(item.get("edge_key"))
            if "->" in edge_key:
                source, target = [part.strip() for part in edge_key.split("->", 1)]
        if not source or not target:
            return {}

        geometry = self._normalize_edge_geometry(item.get("geometry"))
        if not geometry:
            return {}

        raw_confidence = item.get("confidence")
        try:
            confidence = float(raw_confidence) if raw_confidence is not None else None
        except (TypeError, ValueError):
            confidence = None

        raw_way_ids = item.get("osm_way_ids")
        if isinstance(raw_way_ids, (list, tuple, set)):
            osm_way_ids = [normalize_text(way_id) for way_id in raw_way_ids if normalize_text(way_id)]
        else:
            osm_way_ids = []

        raw_geometry_source = normalize_text(item.get("geometry_source")).casefold()
        geometry_source = "manual" if raw_geometry_source in {"manual", "manual_real_map"} else "osm_matched"

        return {
            "edge_key": normalize_text(item.get("edge_key")) or f"{source}->{target}",
            "from": source,
            "to": target,
            "geometry_source": geometry_source,
            "confidence": confidence,
            "osm_way_ids": osm_way_ids,
            "source_osm_id": normalize_text(item.get("source_osm_id")),
            "source_highway": normalize_text(item.get("source_highway")),
            "geometry": geometry,
            "notes": normalize_text(item.get("notes")),
        }

    @staticmethod
    def _build_osm_edge_match_lookup(
        matches: list[dict[str, Any]],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        lookup: dict[tuple[str, str], dict[str, Any]] = {}
        for match in matches:
            source = normalize_text(match.get("from"))
            target = normalize_text(match.get("to"))
            if source and target and (source, target) not in lookup:
                lookup[(source, target)] = match
        return lookup

    def _resolve_osm_edge_match(
        self,
        source: str,
        target: str,
    ) -> tuple[dict[str, Any] | None, bool]:
        match = self.osm_edge_match_lookup.get((source, target))
        if match is not None:
            return match, False
        match = self.osm_edge_match_lookup.get((target, source))
        if match is not None:
            return match, True
        return None, False

    @staticmethod
    def _empty_feature_collection() -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [],
        }

    @staticmethod
    def _count_geojson_geometry_types(geojson: dict[str, Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for feature in geojson.get("features", []):
            if not isinstance(feature, dict):
                continue
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                geometry_type = "unknown"
            else:
                geometry_type = normalize_text(geometry.get("type")) or "unknown"
            counts[geometry_type] = counts.get(geometry_type, 0) + 1
        return counts

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
        *,
        frame_count: int | None = None,
    ) -> dict[str, Any]:
        sample_id = normalize_text(sample.get("sample_id"))
        image_placeholder = normalize_text(sample.get("image_placeholder"))
        preview_placeholder = normalize_text(sample.get("preview_placeholder"))
        style_label = self._aigc_style_label(style)
        title = f"{style_label} · {self._aigc_sample_label(sample)}"
        storyboard = self._build_aigc_storyboard(
            prompt,
            style,
            duration_s,
            frame_count=frame_count or AIGC_MAX_FRAME_COUNT,
        )

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
            "generation_mode": "template_preview",
            "provider": "local_template",
            "fallback_used": False,
            "fallback_reason": "",
            "generated_images": [],
            "frame_count": len(storyboard),
            "prototype_notice": "AIGC 模板化预览：基于用户描述生成校园导览分镜动画，使用本地 JPG / GIF 可见输出。",
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

    def _build_aigc_live_image_preview(
        self,
        preview: dict[str, Any],
        sample: dict[str, Any],
        prompt: str,
        style: str,
        duration_s: int,
        frame_count: int,
        provider: str,
    ) -> tuple[dict[str, Any], str]:
        api_key = normalize_text(os.environ.get("OPENAI_API_KEY"))
        if not api_key:
            return self._mark_aigc_template_fallback(preview, "missing OPENAI_API_KEY")

        if provider != "openai":
            return self._mark_aigc_template_fallback(preview, f"unsupported provider: {provider}")

        model = normalize_text(os.environ.get("OPENAI_IMAGE_MODEL")) or DEFAULT_OPENAI_IMAGE_MODEL
        try:
            generated_images = self._call_openai_image_generation(
                api_key=api_key,
                model=model,
                sample=sample,
                prompt=prompt,
                style=style,
                duration_s=duration_s,
                frame_count=frame_count,
            )
        except Exception as error:  # pragma: no cover - exercised through focused stubs
            return self._mark_aigc_template_fallback(
                preview,
                f"{type(error).__name__}: {error}",
            )

        if not generated_images:
            return self._mark_aigc_template_fallback(preview, "OpenAI returned no generated images")

        storyboard = self._build_aigc_storyboard(
            prompt,
            style,
            duration_s,
            frame_count=len(generated_images),
            image_urls=generated_images,
        )
        live_preview = preview.copy()
        live_preview.update(
            {
                "id": f"live_{preview['sample_id']}_{int(time.time())}",
                "preview_placeholder": generated_images[0],
                "output_type": "live_image_storyboard",
                "status": "live_image_ready",
                "generation_mode": "live_image",
                "provider": provider,
                "fallback_used": False,
                "fallback_reason": "",
                "generated_images": generated_images,
                "frame_count": len(generated_images),
                "prototype_notice": "AIGC 实时分镜：已调用 OpenAI 图片生成 API，生成图片由前端轻量动画播放。",
                "storyboard_frames": storyboard,
                "keyframes": [
                    {
                        "time_s": frame["time_s"],
                        "visual": frame["visual"],
                        "image_url": frame.get("image_url", ""),
                    }
                    for frame in storyboard
                ],
                "generation_pipeline": [
                    "读取本地输入图片样例和用户文字描述",
                    f"调用 OpenAI 图片生成模型 {model}",
                    f"生成 {len(generated_images)} 张实时分镜图",
                    "保存到本地静态生成目录并返回前端播放",
                ],
                "source": {
                    "sample_file": str(self._aigc_sample_path()),
                    "real_model_called": True,
                    "provider": provider,
                    "model": model,
                },
            }
        )
        return live_preview, "aigc live image preview generated"

    def _mark_aigc_template_fallback(
        self,
        preview: dict[str, Any],
        reason: str,
    ) -> tuple[dict[str, Any], str]:
        fallback = preview.copy()
        fallback.update(
            {
                "status": "template_fallback_ready",
                "generation_mode": "template_fallback",
                "provider": "openai",
                "fallback_used": True,
                "fallback_reason": reason,
                "generated_images": [],
                "prototype_notice": (
                    "AIGC 实时分镜已回退到模板预览：保留本地 JPG / GIF 可见输出，"
                    f"原因：{reason}。"
                ),
                "generation_pipeline": [
                    "请求实时图片分镜",
                    f"实时生成不可用：{reason}",
                    "自动回退到第十三周模板预览",
                    "返回可在 Web 中展示的本地 GIF 和分镜结构",
                ],
                "source": {
                    **fallback.get("source", {}),
                    "real_model_called": False,
                    "fallback_used": True,
                    "fallback_reason": reason,
                },
            }
        )
        return fallback, "aigc live image fallback to template preview"

    def _call_openai_image_generation(
        self,
        *,
        api_key: str,
        model: str,
        sample: dict[str, Any],
        prompt: str,
        style: str,
        duration_s: int,
        frame_count: int,
    ) -> list[str]:
        generated_by_index: dict[int, str] = {}
        errors: list[BaseException] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(frame_count, AIGC_MAX_FRAME_COUNT)) as executor:
            futures = {
                executor.submit(
                    self._request_openai_image_batch_with_retry,
                    api_key=api_key,
                    model=model,
                    sample=sample,
                    prompt=prompt,
                    style=style,
                    duration_s=duration_s,
                    frame_count=frame_count,
                    batch_count=1,
                    start_index=frame_index,
                ): frame_index
                for frame_index in range(1, frame_count + 1)
            }
            for future in concurrent.futures.as_completed(futures):
                frame_index = futures[future]
                try:
                    image_urls = future.result()
                except Exception as error:  # pragma: no cover - network edge path
                    errors.append(error)
                    continue
                for offset, image_url in enumerate(image_urls):
                    generated_by_index[frame_index + offset] = image_url

        generated_images = [
            generated_by_index[index]
            for index in range(1, frame_count + 1)
            if index in generated_by_index
        ]
        if generated_images:
            return generated_images[:frame_count]
        if errors:
            raise errors[0]
        return []

    def _request_openai_image_batch_with_retry(self, **kwargs: Any) -> list[str]:
        last_error: BaseException | None = None
        for attempt in range(2):
            try:
                return self._request_openai_image_batch(**kwargs)
            except (RuntimeError, TimeoutError, urllib.error.URLError, OSError) as error:
                last_error = error
                if attempt == 0:
                    time.sleep(1)
                    continue
        if isinstance(last_error, RuntimeError):
            raise last_error
        raise RuntimeError(f"OpenAI image request failed: {type(last_error).__name__}: {last_error}") from last_error

    def _request_openai_image_batch(
        self,
        *,
        api_key: str,
        model: str,
        sample: dict[str, Any],
        prompt: str,
        style: str,
        duration_s: int,
        frame_count: int,
        batch_count: int,
        start_index: int,
    ) -> list[str]:
        request_body = {
            "model": model,
            "prompt": self._build_openai_image_prompt(sample, prompt, style, duration_s, frame_count),
            "n": batch_count,
            "size": "1024x1024",
        }
        request = urllib.request.Request(
            self._resolve_openai_image_endpoint(),
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers=self._build_openai_request_headers(api_key),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._openai_image_timeout_s()) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI image request failed with {error.code}: {body[:180]}") from error

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise RuntimeError("OpenAI image response missing data list")

        generated_images: list[str] = []
        for index, item in enumerate(data[:batch_count], start=start_index):
            if not isinstance(item, dict):
                continue
            image_bytes = self._extract_openai_image_bytes(item)
            if not image_bytes:
                continue
            generated_images.append(self._save_aigc_generated_image(image_bytes, index))
        return generated_images

    def _build_openai_image_prompt(
        self,
        sample: dict[str, Any],
        prompt: str,
        style: str,
        duration_s: int,
        frame_count: int,
    ) -> str:
        return (
            "Create a campus guide storyboard still image. "
            f"Scene request: {prompt}. "
            f"Reference sample: {self._aigc_sample_label(sample)}. "
            f"Style: {self._aigc_style_label(style)}. "
            f"Storyboard length: {frame_count} frames across {duration_s} seconds. "
            "Keep it suitable for a campus/scenic-area guide UI, with clear composition, no text overlays, "
            "and consistent visual style across frames."
        )

    @staticmethod
    def _extract_openai_image_bytes(item: dict[str, Any]) -> bytes:
        b64_data = normalize_text(item.get("b64_json"))
        if b64_data:
            return base64.b64decode(b64_data)
        image_url = normalize_text(item.get("url"))
        if image_url:
            request = urllib.request.Request(
                image_url,
                headers={
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "User-Agent": self._openai_user_agent(),
                },
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=DemoUIService._openai_image_timeout_s()) as response:
                return response.read()
        return b""

    @staticmethod
    def _build_openai_request_headers(api_key: str) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": DemoUIService._openai_user_agent(),
        }
        referer = normalize_text(os.environ.get("OPENAI_HTTP_REFERER"))
        app_title = normalize_text(os.environ.get("OPENAI_APP_TITLE"))
        if referer:
            headers["HTTP-Referer"] = referer
        if app_title:
            headers["X-Title"] = app_title
        return headers

    @staticmethod
    def _openai_user_agent() -> str:
        return normalize_text(os.environ.get("OPENAI_USER_AGENT")) or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )

    @staticmethod
    def _openai_image_timeout_s() -> int:
        try:
            timeout_s = int(float(os.environ.get("OPENAI_IMAGE_TIMEOUT_S", "")))
        except (TypeError, ValueError):
            timeout_s = AIGC_OPENAI_IMAGE_TIMEOUT_S
        return max(10, min(300, timeout_s))

    def _save_aigc_generated_image(self, image_bytes: bytes, frame_index: int) -> str:
        AIGC_GENERATED_STATIC_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"aigc_{int(time.time() * 1000)}_{frame_index:02d}.png"
        file_path = AIGC_GENERATED_STATIC_DIR / file_name
        file_path.write_bytes(image_bytes)
        return f"{AIGC_GENERATED_URL_PREFIX}/{file_name}"

    @staticmethod
    def _resolve_openai_image_endpoint() -> str:
        explicit_endpoint = normalize_text(os.environ.get("OPENAI_IMAGE_API_URL"))
        if explicit_endpoint:
            return explicit_endpoint

        base_url = normalize_text(os.environ.get("OPENAI_BASE_URL")).rstrip("/")
        if not base_url:
            return AIGC_OPENAI_IMAGE_ENDPOINT
        if base_url.endswith("/v1"):
            return f"{base_url}/images/generations"
        return f"{base_url}/v1/images/generations"

    def _build_aigc_storyboard(
        self,
        prompt: str,
        style: str,
        duration_s: int,
        *,
        frame_count: int = AIGC_MAX_FRAME_COUNT,
        image_urls: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        style_label = self._aigc_style_label(style)
        normalized_frame_count = max(1, min(AIGC_MAX_FRAME_COUNT, int(frame_count or AIGC_MAX_FRAME_COUNT)))
        step = max(1, round(duration_s / normalized_frame_count))
        summary = self._summarize_prompt(prompt)
        frame_templates = [
            ("开场", f"用{style_label}建立场景氛围：{summary}"),
            ("推进", "突出地点、人物动作和路线线索，形成可跟随的游览节奏。"),
            ("重点", "放大体验亮点，并补充文字贴片说明推荐理由。"),
            ("收束", "以导览提示和下一步路线建议结束预览。"),
        ][:normalized_frame_count]
        image_urls = image_urls or []

        return [
            {
                "frame_index": index,
                "time_s": min(duration_s, (index - 1) * step),
                "title": title,
                "visual": visual,
                "caption": f"{title}镜头：{visual}",
                "image_url": image_urls[index - 1] if index <= len(image_urls) else "",
            }
            for index, (title, visual) in enumerate(frame_templates, start=1)
        ]

    def _build_aigc_metadata(
        self,
        *,
        generation_mode: str = "template_preview",
        provider: str = "local_template",
        real_model_called: bool = False,
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        return {
            "prototype_mode": generation_mode,
            "generation_mode": generation_mode,
            "provider": provider,
            "real_model_called": real_model_called,
            "fallback_used": fallback_used,
            "generated_static_dir": str(AIGC_GENERATED_STATIC_DIR),
            "data_source": {
                "path": str(self._aigc_sample_path()),
                "sample_count": len(self.aigc_samples),
            },
            "input_contract": [
                "sample_id",
                "prompt",
                "style",
                "duration_s",
                "mode",
                "provider",
                "frame_count",
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
                "generation_mode",
                "provider",
                "fallback_used",
                "fallback_reason",
                "generated_images",
            ],
        }

    @staticmethod
    def _normalize_aigc_mode(value: Any) -> str:
        mode = normalize_text(value).casefold()
        return mode if mode in {"template", "live_image"} else "template"

    @staticmethod
    def _normalize_aigc_provider(value: Any) -> str:
        provider = normalize_text(value).casefold()
        return provider or "openai"

    @staticmethod
    def _normalize_aigc_frame_count(value: Any) -> int:
        try:
            frame_count = int(float(value))
        except (TypeError, ValueError):
            frame_count = AIGC_MAX_FRAME_COUNT
        return max(1, min(AIGC_MAX_FRAME_COUNT, frame_count))

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
            display_metadata = self._build_node_display_metadata(category, node.get("type"))
            nodes.append(
                {
                    "id": normalize_text(node.get("id")),
                    "name": normalize_text(node.get("name")) or normalize_text(node.get("id")),
                    "category": category,
                    "category_label": CATEGORY_LABELS.get(category, category),
                    **display_metadata,
                    "graph_type": "outdoor",
                    "lat": float(lat),
                    "lng": float(lng),
                    "is_gate": bool(node.get("is_gate", False)),
                    **self._extract_node_extra_fields(node),
                }
            )

        nodes.sort(
            key=lambda item: (
                TARGET_CATEGORY_PRIORITY.get(item["category"], 99),
                item["name"],
            )
        )
        return nodes

    @classmethod
    def _build_node_display_metadata(cls, category: str, node_type: Any = "") -> dict[str, Any]:
        is_waypoint = cls._is_waypoint_category(category, node_type)
        return {
            "display_role": "waypoint" if is_waypoint else "poi",
            "is_waypoint": is_waypoint,
            "label_priority": 10 if is_waypoint else LABEL_PRIORITY_BY_CATEGORY.get(category, 40),
            "show_label": not is_waypoint,
            "is_searchable": not is_waypoint,
        }

    @staticmethod
    def _is_waypoint_category(category: str, node_type: Any = "") -> bool:
        return category == "road" or normalize_text(node_type).casefold() == "waypoint"

    @staticmethod
    def _extract_node_extra_fields(node: dict[str, Any]) -> dict[str, Any]:
        extra_keys = (
            "network_role",
            "source",
            "source_osm_id",
            "source_osm_ids",
            "source_highway",
            "source_highways",
            "anchor_for",
            "anchor_for_name",
            "projection_distance_m",
            "projection_source",
            "needs_review",
            "route_anchor_node_id",
            "route_anchor_distance_m",
            "route_anchor_source",
            "route_anchor_needs_review",
            "indoor_supported",
            "indoor_graph_id",
            "indoor_entry_node_id",
            "source_sub_graph_id",
            "floor_id",
            "floor_label",
            "layout",
            "description",
            "facilities",
            "tags",
            "is_gate",
        )
        return {key: node[key] for key in extra_keys if key in node}

    def _build_node_extra_properties(self, node: dict[str, Any]) -> dict[str, Any]:
        node_id = normalize_text(node.get("id"))
        return {
            **self._extract_node_extra_fields(node),
            **self._build_indoor_node_context(node_id, node),
        }

    @classmethod
    def _filter_searchable_site_records(cls, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            record
            for record in records
            if not cls._is_waypoint_category(
                normalize_text(record.get("category") or record.get("type")),
                record.get("type"),
            )
        ]

    def _build_map_edges(self, graph_data: dict[str, Any]) -> list[dict[str, Any]]:
        node_ids = {node["id"] for node in self.map_nodes}
        seen_pairs: set[tuple[str, str, str]] = set()
        edges: list[dict[str, Any]] = []

        for edge in graph_data.get("edges", []):
            source = normalize_text(edge.get("from"))
            target = normalize_text(edge.get("to"))
            if source not in node_ids or target not in node_ids:
                continue

            pair_key = tuple(sorted((source, target)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            map_edge = {
                "from": source,
                "to": target,
                "name": normalize_text(edge.get("name")),
                "type": normalize_text(edge.get("type")) or "outdoor_road",
                "distance_m": float(edge.get("distance", 0)),
                "vehicle_access": normalize_text(edge.get("vehicle_access")) or "all",
                "allowed_transports": self._normalize_transport_list(edge.get("allowed_transports")),
                "transport_semantics": normalize_text(edge.get("transport_semantics")),
                "m21_demo_role": normalize_text(edge.get("m21_demo_role")),
                **self._resolve_edge_source_metadata(edge, source, target),
            }
            osm_match, reversed_match = self._resolve_osm_edge_match(source, target)
            if osm_match:
                geometry = list(osm_match["geometry"])
                if reversed_match:
                    geometry = list(reversed(geometry))
                map_edge.update(
                    {
                        "geometry": geometry,
                        "geometry_source": osm_match.get("geometry_source") or "osm_matched",
                        "geometry_confidence": osm_match.get("confidence"),
                        "osm_way_ids": osm_match.get("osm_way_ids", []),
                        "source_osm_id": osm_match.get("source_osm_id") or map_edge.get("source_osm_id"),
                        "source_highway": osm_match.get("source_highway") or map_edge.get("source_highway"),
                        "osm_match_edge_key": osm_match.get("edge_key"),
                        "osm_match_reversed": reversed_match,
                    }
                )
            else:
                geometry = self._normalize_edge_geometry(edge.get("geometry"))
                if geometry:
                    map_edge["geometry"] = geometry
                    map_edge["geometry_source"] = "manual"
            edges.append(map_edge)

        return edges

    def _resolve_edge_source_metadata(
        self,
        edge: dict[str, Any],
        source: str,
        target: str,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {}
        source_osm_id = normalize_text(edge.get("source_osm_id"))
        source_highway = normalize_text(edge.get("source_highway"))
        if source_osm_id:
            metadata["source_osm_id"] = source_osm_id
        if source_highway:
            metadata["source_highway"] = source_highway

        for node_id in (source, target):
            node = self.map_node_index.get(node_id) or {}
            if "source_osm_id" not in metadata:
                node_osm_id = normalize_text(node.get("source_osm_id"))
                if not node_osm_id:
                    source_ids = node.get("source_osm_ids")
                    if isinstance(source_ids, list) and source_ids:
                        node_osm_id = normalize_text(source_ids[0])
                if node_osm_id:
                    metadata["source_osm_id"] = node_osm_id
            if "source_highway" not in metadata:
                node_highway = normalize_text(node.get("source_highway"))
                if not node_highway:
                    source_highways = node.get("source_highways")
                    if isinstance(source_highways, list) and source_highways:
                        node_highway = normalize_text(source_highways[0])
                if node_highway:
                    metadata["source_highway"] = node_highway
            if "source_osm_id" in metadata and "source_highway" in metadata:
                break

        return metadata

    def _build_map_geometry_stats(self) -> dict[str, int | float]:
        edge_count = len(self.map_edges)
        osm_matched_edge_count = sum(
            1 for edge in self.map_edges if edge.get("geometry_source") == "osm_matched"
        )
        manual_geometry_edge_count = sum(
            1 for edge in self.map_edges if edge.get("geometry_source") == "manual"
        )
        geometry_edge_count = osm_matched_edge_count + manual_geometry_edge_count
        fallback_edge_count = edge_count - geometry_edge_count
        geometry_coverage_ratio = (
            round(geometry_edge_count / edge_count, 4)
            if edge_count
            else 0.0
        )
        osm_matched_coverage_ratio = (
            round(osm_matched_edge_count / edge_count, 4)
            if edge_count
            else 0.0
        )
        return {
            "geometry_edge_count": geometry_edge_count,
            "osm_matched_edge_count": osm_matched_edge_count,
            "manual_geometry_edge_count": manual_geometry_edge_count,
            "fallback_edge_count": fallback_edge_count,
            "geometry_coverage_ratio": geometry_coverage_ratio,
            "osm_matched_coverage_ratio": osm_matched_coverage_ratio,
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
    ) -> tuple[list[list[float]], str]:
        geometry = edge.get("geometry")
        if isinstance(geometry, list) and len(geometry) >= 2:
            geometry_source = normalize_text(edge.get("geometry_source")) or "manual"
            return [[point["lng"], point["lat"]] for point in geometry], geometry_source

        source = self.map_node_index.get(edge.get("from"))
        target = self.map_node_index.get(edge.get("to"))
        if not source or not target:
            return [], "fallback_line"
        return [[source["lng"], source["lat"]], [target["lng"], target["lat"]]], "fallback_line"

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
            "route_segment_count": stats["route_segment_count"],
            "fallback_segment_count": stats["fallback_segment_count"],
            "fallback_edge_count": stats["fallback_edge_count"],
            "geometry_segment_count": stats["geometry_segment_count"],
            "osm_matched_segment_count": stats["osm_matched_segment_count"],
            "manual_geometry_segment_count": stats["manual_geometry_segment_count"],
            "reverse_edge_reuse_count": stats["reverse_edge_reuse_count"],
            "missing_edge_count": stats["missing_edge_count"],
            "skipped_unmapped_segment_count": stats["skipped_unmapped_segment_count"],
            "coordinate_count": stats["coordinate_count"],
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

            segment_coordinates, geometry_source, used_reverse, missing_edge = (
                self._resolve_route_segment_coordinates(source, target)
            )
            if len(segment_coordinates) < 2:
                stats["missing_edge_count"] += 1
                continue

            stats["route_segment_count"] += 1
            if geometry_source == "fallback_line":
                stats["fallback_segment_count"] += 1
                stats["fallback_edge_count"] += 1
            elif geometry_source == "osm_matched":
                stats["geometry_segment_count"] += 1
                stats["osm_matched_segment_count"] += 1
            else:
                stats["geometry_segment_count"] += 1
                stats["manual_geometry_segment_count"] += 1
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
    ) -> tuple[list[list[float]], str, bool, bool]:
        edge = self.map_edge_lookup.get((source, target))
        used_reverse = False

        if edge is None:
            edge = self.map_edge_lookup.get((target, source))
            used_reverse = edge is not None

        if edge is not None:
            coordinates, geometry_source = self._build_edge_geojson_coordinates(edge)
            if used_reverse:
                coordinates = list(reversed(coordinates))
            return coordinates, geometry_source, used_reverse, False

        source_node = self.map_node_index.get(source)
        target_node = self.map_node_index.get(target)
        if not source_node or not target_node:
            return [], "fallback_line", False, True
        return (
            [
                [source_node["lng"], source_node["lat"]],
                [target_node["lng"], target_node["lat"]],
            ],
            "fallback_line",
            False,
            True,
        )

    @staticmethod
    def _empty_route_geometry_stats() -> dict[str, int]:
        return {
            "route_segment_count": 0,
            "geometry_segment_count": 0,
            "osm_matched_segment_count": 0,
            "manual_geometry_segment_count": 0,
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
            "osm_matched_segment_count",
            "manual_geometry_segment_count",
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
            if self._is_waypoint_category(category, node_data.get("type")):
                continue

            graph_type = normalize_text(node_data.get("graph_type")) or "indoor"
            location = node_data.get("location") or {}
            has_location = node_id in self.map_node_index
            display_metadata = self._build_node_display_metadata(category, node_data.get("type"))
            targets.append(
                {
                    "id": node_id,
                    "name": normalize_text(node_data.get("name")) or node_id,
                    "category": category,
                    "category_label": CATEGORY_LABELS.get(category, category),
                    "display_role": display_metadata["display_role"],
                    "is_waypoint": display_metadata["is_waypoint"],
                    "label_priority": display_metadata["label_priority"],
                    "graph_type": graph_type,
                    "layer": normalize_text(node_data.get("source_sub_graph_id")) or graph_type,
                    "has_map_location": has_location,
                    "lat": float(location.get("lat")) if location.get("lat") is not None else None,
                    "lng": float(location.get("lng")) if location.get("lng") is not None else None,
                    **self._extract_node_extra_fields(node_data),
                    **self._build_indoor_node_context(node_id, node_data),
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

    def _normalize_radius_m(self, value: Any, *, default: float = 500.0) -> float:
        if value in (None, ""):
            return default
        try:
            radius = float(value)
        except (TypeError, ValueError):
            return default
        if radius <= 0:
            return default
        return min(radius, 3000.0)

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

    @staticmethod
    def _normalize_transport_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [normalize_text(value).casefold()] if normalize_text(value) else []
        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                normalized = normalize_text(item).casefold()
                if normalized:
                    result.append(normalized)
            return result
        return []

    @staticmethod
    def _transport_mode_label(value: str | None) -> str:
        return TRANSPORT_MODE_LABELS.get(value, value or TRANSPORT_MODE_LABELS[None])

    def _normalize_transport_mode(self, value: Any) -> str | None:
        normalized = normalize_text(value).casefold()
        if normalized in {"", "any", "all", "none", "不限交通方式"}:
            return None
        aliases = {
            "pedestrian": "walk",
            "foot": "walk",
            "步行": "walk",
            "bicycle": "bike",
            "cycling": "bike",
            "自行车": "bike",
            "walk+bike": "mixed",
            "walk-bike": "mixed",
            "walk_bike": "mixed",
            "步行+自行车": "mixed",
            "步行 + 自行车": "mixed",
            "混合交通": "mixed",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in {"walk", "bike", "mixed"}:
            return normalized
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
        if source == "place_search":
            return self._decorate_nearby_place_response(decorated)
        return decorated

    def _decorate_nearby_place_response(self, response: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(response.get("metadata") or {})
        nearby = metadata.get("nearby")
        if not isinstance(nearby, dict):
            return response

        filters = response.get("filters") or {}
        center_node_id = normalize_text(filters.get("center_node_id") or nearby.get("center_node_id"))
        if not center_node_id:
            return response

        center_name = self._resolve_node_name(center_node_id) or normalize_text(nearby.get("center_name")) or center_node_id
        decorated_nearby = dict(nearby)
        decorated_nearby["center_name"] = center_name

        calibration_stage = normalize_text(self.outdoor_metadata.get("nearby_calibration_stage"))
        if calibration_stage:
            decorated_nearby["calibration_stage"] = calibration_stage

        profile = self.nearby_profiles.get(center_node_id)
        if profile:
            decorated_nearby["calibration_profile"] = profile

        radius_m = decorated_nearby.get("radius_m")
        decorated_items: list[dict[str, Any]] = []
        for item in response.get("results", response.get("data", [])):
            copied = item.copy()
            if normalize_text(copied.get("nearby_center_node_id")) == center_node_id:
                copied["nearby_center_name"] = center_name
                try:
                    nearby_distance_m = float(copied.get("nearby_distance_m", copied.get("distance_m", 0.0)))
                    nearby_radius_m = float(copied.get("nearby_radius_m", radius_m or 0.0))
                except (TypeError, ValueError):
                    pass
                else:
                    copied["nearby_reason"] = (
                        f"距离{center_name} {nearby_distance_m:.1f} m，在 {nearby_radius_m:.0f} m 范围内。"
                    )
            decorated_items.append(copied)

        decorated = response.copy()
        decorated["metadata"] = metadata
        decorated["metadata"]["nearby"] = decorated_nearby
        decorated["data"] = decorated_items
        decorated["results"] = decorated_items
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

    @staticmethod
    def _indoor_view_id(building_id: str, floor_id: str) -> str:
        return f"indoor:{building_id}:{floor_id}"

    def _build_indoor_route_views(self, route: dict[str, Any]) -> list[dict[str, Any]]:
        building_views: dict[str, dict[str, Any]] = {}
        path = route.get("path", [])

        for node_id in path:
            node_data = self.graph.nodes.get(node_id, {})
            indoor_graph_id = normalize_text(node_data.get("source_sub_graph_id"))
            floor_id = normalize_text(node_data.get("floor_id"))
            if not indoor_graph_id.startswith("indoor_") or not floor_id:
                continue

            building_entry = self.indoor_graph_lookup.get(indoor_graph_id)
            if building_entry is None:
                continue

            building_id = normalize_text(building_entry.get("building_id"))
            available_floors = self._build_available_floor_summaries(
                self.indoor_graph_sources.get(indoor_graph_id, {}),
                default_floor_id=normalize_text(building_entry.get("default_floor_id")) or "F1",
            )
            building_view = building_views.setdefault(
                building_id,
                {
                    "building_id": building_id,
                    "building_name": normalize_text(building_entry.get("building_name")) or building_id,
                    "indoor_graph_id": indoor_graph_id,
                    "entry_node_id": normalize_text(building_entry.get("entry_node_id")),
                    "default_floor_id": normalize_text(building_entry.get("default_floor_id")) or "F1",
                    "available_floors": available_floors,
                    "floors": {},
                },
            )
            floor_view = building_view["floors"].setdefault(
                floor_id,
                {
                    "view_id": self._indoor_view_id(building_id, floor_id),
                    "floor_id": floor_id,
                    "floor_label": normalize_text(node_data.get("floor_label")) or self._floor_label_for_id(floor_id),
                    "path_node_ids": [],
                    "route_node_ids": [],
                    "highlight_node_ids": [],
                    "path_segments": [],
                    "path_step_indices": [],
                    "route_step_indices": [],
                    "contains_entry": False,
                    "contains_target": False,
                },
            )
            if not floor_view["path_node_ids"] or floor_view["path_node_ids"][-1] != node_id:
                floor_view["path_node_ids"].append(node_id)
            if not floor_view["route_node_ids"] or floor_view["route_node_ids"][-1] != node_id:
                floor_view["route_node_ids"].append(node_id)
            if node_id not in floor_view["highlight_node_ids"]:
                floor_view["highlight_node_ids"].append(node_id)
            if node_data.get("is_gate"):
                floor_view["contains_entry"] = True
            if node_id == route.get("target_node_id"):
                floor_view["contains_target"] = True

        for step in route.get("path_steps", []):
            start_data = self.graph.nodes.get(normalize_text(step.get("from_node_id")), {})
            end_data = self.graph.nodes.get(normalize_text(step.get("to_node_id")), {})
            related_floors = []

            for node_data in (start_data, end_data):
                graph_id = normalize_text(node_data.get("source_sub_graph_id"))
                floor_id = normalize_text(node_data.get("floor_id"))
                if not graph_id.startswith("indoor_") or not floor_id:
                    continue
                building_entry = self.indoor_graph_lookup.get(graph_id)
                if building_entry is None:
                    continue
                building_id = normalize_text(building_entry.get("building_id"))
                related_floors.append((building_id, floor_id))

            for building_id, floor_id in dict.fromkeys(related_floors):
                building_view = building_views.get(building_id)
                if building_view is None:
                    continue
                floor_view = building_view["floors"].get(floor_id)
                if floor_view is None:
                    continue
                floor_view["path_step_indices"].append(step.get("step_index"))
                floor_view["route_step_indices"].append(step.get("step_index"))

            same_indoor_floor = (
                normalize_text(start_data.get("source_sub_graph_id")).startswith("indoor_")
                and normalize_text(start_data.get("source_sub_graph_id")) == normalize_text(end_data.get("source_sub_graph_id"))
                and normalize_text(start_data.get("floor_id")) == normalize_text(end_data.get("floor_id"))
                and normalize_text(start_data.get("floor_id"))
            )
            if not same_indoor_floor:
                continue

            building_entry = self.indoor_graph_lookup.get(normalize_text(start_data.get("source_sub_graph_id")))
            if building_entry is None:
                continue
            building_id = normalize_text(building_entry.get("building_id"))
            floor_id = normalize_text(start_data.get("floor_id"))
            floor_view = building_views.get(building_id, {}).get("floors", {}).get(floor_id)
            if floor_view is None:
                continue
            floor_view["path_segments"].append(
                {
                    "from": normalize_text(step.get("from_node_id")),
                    "to": normalize_text(step.get("to_node_id")),
                    "edge_type": normalize_text(step.get("edge_type")),
                }
            )

        result = []
        for building_view in building_views.values():
            ordered_floors = []
            for floor_meta in building_view["available_floors"]:
                floor_view = building_view["floors"].get(floor_meta["floor_id"])
                if floor_view is not None:
                    ordered_floors.append(floor_view)
            if not ordered_floors:
                continue
            result.append({**building_view, "floors": ordered_floors})
        return result

    @staticmethod
    def _build_available_route_views(
        indoor_route_views: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        views = [
            {
                "id": "outdoor",
                "label": "查看室外路线",
                "kind": "outdoor",
            }
        ]
        for building_view in indoor_route_views:
            for floor_view in building_view.get("floors", []):
                views.append(
                    {
                        "id": floor_view["view_id"],
                        "label": f"查看{building_view['building_name']}{floor_view['floor_label']}路线",
                        "kind": "indoor",
                        "building_id": building_view["building_id"],
                        "building_name": building_view["building_name"],
                        "floor_id": floor_view["floor_id"],
                        "floor_label": floor_view["floor_label"],
                    }
                )
        return views

    @staticmethod
    def _resolve_default_route_view(
        indoor_route_views: list[dict[str, Any]],
        route_geometry_stats: dict[str, int],
    ) -> str:
        has_outdoor_route = (route_geometry_stats or {}).get("route_segment_count", 0) > 0
        if has_outdoor_route or not indoor_route_views:
            return "outdoor"

        for building_view in indoor_route_views:
            for floor_view in building_view.get("floors", []):
                if floor_view.get("contains_target"):
                    return floor_view["view_id"]

        first_building = indoor_route_views[0]
        return first_building["floors"][0]["view_id"]

    def _build_route_overlay(self, route: dict[str, Any]) -> dict[str, Any]:
        path = route.get("path", [])
        mappable_path_node_ids = [node_id for node_id in path if node_id in self.map_node_index]
        unmapped_path_node_ids = [node_id for node_id in path if node_id not in self.map_node_index]
        route_geojson, route_line_coordinates, route_geometry_stats = self._build_route_geojson_feature(
            route,
            route_type="single_target",
        )
        indoor_route_views = self._build_indoor_route_views(route)
        available_route_views = self._build_available_route_views(indoor_route_views)
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
            "indoor_route_views": indoor_route_views,
            "available_route_views": available_route_views,
            "default_route_view": self._resolve_default_route_view(
                indoor_route_views,
                route_geometry_stats,
            ),
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
        indoor_route_views = self._build_indoor_route_views(route)
        available_route_views = self._build_available_route_views(indoor_route_views)
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
            "indoor_route_views": indoor_route_views,
            "available_route_views": available_route_views,
            "default_route_view": self._resolve_default_route_view(
                indoor_route_views,
                route_geometry_stats,
            ),
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
            return f"{base} 各段室外路线已沿真实道路高亮。"

        indoor_names = [
            self._resolve_node_name(node_id)
            for node_id in unmapped_path_node_ids
        ]
        return (
            f"{base} 室外段已沿真实道路高亮；室内段请看右侧步骤卡片。"
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
            return f"{base} 的室外路线已沿真实道路高亮。"

        indoor_names = [
            self._resolve_node_name(node_id)
            for node_id in unmapped_path_node_ids
        ]
        return (
            f"{base} 的室外段已沿真实道路高亮；室内段请看右侧步骤卡片。"
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

