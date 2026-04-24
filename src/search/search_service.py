"""
成员 B：查询推荐业务服务层

本模块负责组织第八周主业务链路：

- 读取景点数据
- 执行精确查询或模糊查询
- 可选补充距离字段
- 调用 Top-K 推荐
- 返回统一 Response

CLI、测试脚本和后续联调入口都应优先调用本模块，避免业务逻辑散落在
命令行演示代码中。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.recommend.ranking import recommend_top_k
from src.search.exact_search import filter_by_category, search_records
from src.search.distance_adapter import DistanceProvider, build_distance_provider
from src.search.fuzzy_search import fuzzy_search
from src.search.response import build_error_response, build_success_response


Record = dict[str, Any]


def get_default_scenic_data_path() -> Path:
    """返回历史兼容景点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "scenic_spots.json"


def get_member_c_scenic_data_path() -> Path:
    """返回成员 C 第七周提交的旧景点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "成员Cdata" / "scenic_spots.json"


def resolve_scenic_data_path(
    data_path: str | Path | None = None,
    *,
    prefer_member_c: bool = False,
) -> Path | None:
    """解析本次查询应使用的旧版景点数据文件。"""
    if data_path is not None:
        return Path(data_path)

    member_c_path = get_member_c_scenic_data_path()
    if prefer_member_c and member_c_path.exists():
        return member_c_path

    default_path = get_default_scenic_data_path()
    if default_path.exists():
        return default_path

    return None


def get_global_sites_path() -> Path:
    """返回全局景区注册表路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "global_sites.json"


def load_global_sites() -> list[Record]:
    """加载全局景区注册信息。"""
    path = get_global_sites_path()
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    return sites if isinstance(sites, list) else []


def get_default_site_id() -> str:
    """返回默认景区 ID。"""
    sites = load_global_sites()
    if sites:
        return str(sites[0].get("id", "PKU")).strip() or "PKU"
    return "PKU"


def get_site_dir(site_id: str | None = None) -> Path:
    """返回景区分层数据目录。"""
    target_site_id = site_id or get_default_site_id()
    return Path(__file__).resolve().parents[2] / "data" / "sites" / target_site_id


def get_site_graph_paths(site_id: str | None = None) -> list[Path]:
    """返回景区分层图文件列表。"""
    target_site_id = site_id or get_default_site_id()
    site_dir = get_site_dir(target_site_id)
    if not site_dir.exists():
        return []

    target_names: list[str] = []
    for site in load_global_sites():
        if str(site.get("id", "")).strip() == target_site_id:
            target_names = [str(name).strip() for name in site.get("sub_graphs", []) if str(name).strip()]
            break

    if target_names:
        paths = [site_dir / f"{name}.json" for name in target_names]
        return [path for path in paths if path.exists()]

    outdoor_path = site_dir / "outdoor.json"
    if outdoor_path.exists():
        return [outdoor_path]

    return sorted(site_dir.glob("*.json"))


def load_json_records(path: Path) -> list[Record]:
    """从 JSON 列表文件中加载记录。"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"records data must be a list: {path}")

    return data


def load_site_records(site_id: str | None = None) -> list[Record]:
    """加载标准分层目录中的站点节点记录。"""
    target_site_id = site_id or get_default_site_id()
    records: list[Record] = []

    for graph_path in get_site_graph_paths(target_site_id):
        records.extend(normalize_site_graph_records(target_site_id, graph_path))

    return records


def normalize_site_graph_records(site_id: str, graph_path: Path) -> list[Record]:
    """将分层图 JSON 中的节点标准化为成员 B 可搜索/可推荐记录。"""
    with graph_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    graph_type = str(data.get("graph_type", "")).strip().lower() or "outdoor"
    building_name = str(data.get("building_name", "")).strip()
    source_graph_id = str(data.get("graph_id", graph_path.stem)).strip()
    normalized_records: list[Record] = []

    for node in data.get("nodes", []):
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            continue

        category = str(node.get("category", node.get("type", ""))).strip()
        record: Record = {
            "id": node_id,
            "node_id": node_id,
            "map_node_id": node_id,
            "site_id": site_id,
            "name": node.get("name", node_id),
            "category": category,
            "heat": int(node.get("heat", estimate_heat(node, graph_type))),
            "rating": float(node.get("rating", estimate_rating(node, graph_type))),
            "tags": list(node.get("tags", [])),
            "keywords": build_keywords(node, graph_type, building_name),
            "description": node.get("description", ""),
            "type": node.get("type", ""),
            "graph_type": graph_type,
            "source_graph_id": source_graph_id,
            "source_graph_file": graph_path.name,
            "sub_graph_id": node.get("sub_graph_id"),
            "is_gate": bool(node.get("is_gate", False)),
            "is_indoor": bool(node.get("is_indoor", graph_type == "indoor")),
            "indoor_building": node.get(
                "indoor_building",
                building_name if graph_type == "indoor" else "",
            ),
            "building_name": building_name,
            "facilities": list(node.get("facilities", [])),
            "open_hours": node.get("open_hours"),
        }
        normalized_records.append(record)

    return normalized_records


def build_keywords(node: Record, graph_type: str, building_name: str) -> list[str]:
    """为标准节点构造关键词列表。"""
    keywords: list[str] = []
    for value in (
        node.get("name"),
        node.get("category"),
        node.get("type"),
        building_name,
        node.get("indoor_building"),
    ):
        if value:
            keywords.append(str(value))

    for key in ("tags", "facilities"):
        for item in node.get(key, []):
            if item:
                keywords.append(str(item))

    if graph_type == "indoor":
        keywords.append("室内")
    else:
        keywords.append("室外")

    return unique_strings(keywords)


def unique_strings(values: list[str]) -> list[str]:
    """按输入顺序去重字符串列表。"""
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    return result


def estimate_heat(node: Record, graph_type: str) -> int:
    """为标准节点生成默认热度。"""
    category = str(node.get("category", node.get("type", ""))).strip()
    base_values = {
        "landmark": 92,
        "education": 88,
        "reading_room": 86,
        "hall": 80,
        "entrance": 78,
        "dormitory": 75,
        "catering": 74,
        "shopping": 70,
        "sports": 72,
        "service": 68,
        "restroom": 62,
        "parking": 58,
        "passage": 54,
        "road": 50,
    }
    base = base_values.get(category, 65)
    if graph_type == "indoor":
        base += 2
    return base


def estimate_rating(node: Record, graph_type: str) -> float:
    """为标准节点生成默认评分。"""
    category = str(node.get("category", node.get("type", ""))).strip()
    base_values = {
        "landmark": 4.8,
        "education": 4.7,
        "reading_room": 4.8,
        "hall": 4.6,
        "entrance": 4.5,
        "dormitory": 4.4,
        "catering": 4.5,
        "shopping": 4.3,
        "sports": 4.5,
        "service": 4.4,
        "restroom": 4.2,
        "parking": 4.1,
        "passage": 4.0,
        "road": 4.0,
    }
    base = base_values.get(category, 4.3)
    if graph_type == "indoor":
        base += 0.1
    return round(min(base, 5.0), 1)


def load_scenic_spots(
    data_path: str | Path | None = None,
    *,
    prefer_member_c: bool = False,
) -> list[Record]:
    """加载成员 B 查询所需记录，优先兼容标准分层目录。"""
    target_path = resolve_scenic_data_path(data_path, prefer_member_c=prefer_member_c)
    if target_path is not None:
        return load_json_records(target_path)

    return load_site_records()


def search_and_recommend(
    *,
    keyword: str,
    category: str = "",
    start_node_id: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 10,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_member_c_data: bool = False,
    distance_provider: DistanceProvider | None = None,
    use_default_distance_provider: bool = True,
    distance_strategy: str = "shortest_distance",
) -> dict[str, Any]:
    """
    查询推荐主入口。

    参数说明：
    - keyword/category: 查询与过滤条件。
    - start_node_id: 用户所在起点节点；为空时不计算距离。
    - distance_provider: 距离接口适配器，预期兼容
      `query_distance(start_node_id, target_node_id, strategy)`。
    - use_default_distance_provider: 为 True 时，如果传入了 start_node_id 且
      没有手动注入 distance_provider，则自动接入成员 A 的默认距离接口。
    - sort_field/sort_order: 推荐排序字段与方向；距离排序建议使用
      `sort_field="distance_m"`。
    - records/data_path: 允许测试或联调时注入数据。
    """
    filters = {
        "keyword": keyword,
        "category": category,
        "start_node_id": start_node_id,
        "match_mode": match_mode,
        "sort_field": sort_field,
        "sort_order": _resolve_sort_order(sort_field, sort_order),
        "limit": limit,
        "distance_strategy": distance_strategy,
        "prefer_member_c_data": prefer_member_c_data,
        "use_default_distance_provider": use_default_distance_provider,
    }
    base_metadata = build_response_metadata(
        records=[],
        sort_field=sort_field,
        sort_order=filters["sort_order"],
        limit=limit,
        start_node_id=start_node_id,
        distance_strategy=distance_strategy,
        distance_provider_active=False,
    )

    if not keyword and not category:
        return build_error_response(
            "keyword and category cannot both be empty",
            query_type="scenic_search",
            filters=filters,
            metadata=base_metadata,
        )

    source_records = (
        records[:]
        if records is not None
        else load_scenic_spots(data_path, prefer_member_c=prefer_member_c_data)
    )
    filtered_records = filter_records(
        source_records,
        keyword=keyword,
        category=category,
        match_mode=match_mode,
    )

    if not filtered_records:
        return build_success_response(
            data=[],
            message="no matched records",
            query_type="scenic_search",
            filters=filters,
            metadata=base_metadata,
        )

    active_distance_provider = resolve_distance_provider(
        start_node_id=start_node_id,
        distance_provider=distance_provider,
        use_default_distance_provider=use_default_distance_provider,
    )

    enriched_records = attach_distance_fields(
        filtered_records,
        start_node_id=start_node_id,
        distance_provider=active_distance_provider,
        distance_strategy=distance_strategy,
    )
    top_records = rank_records(
        enriched_records,
        sort_field=sort_field,
        sort_order=filters["sort_order"],
        limit=limit,
    )
    metadata = build_response_metadata(
        records=top_records,
        sort_field=sort_field,
        sort_order=filters["sort_order"],
        limit=limit,
        start_node_id=start_node_id,
        distance_strategy=distance_strategy,
        distance_provider_active=active_distance_provider is not None,
    )

    return build_success_response(
        data=top_records,
        message="query success",
        query_type="scenic_search",
        filters=filters,
        metadata=metadata,
    )


def filter_records(
    records: list[Record],
    *,
    keyword: str = "",
    category: str = "",
    match_mode: str = "fuzzy",
) -> list[Record]:
    """执行查询与类别过滤。"""
    normalized_mode = match_mode.strip().lower()

    if normalized_mode == "fuzzy":
        result = fuzzy_search(records, keyword) if keyword else records[:]
        return filter_by_category(result, category) if category else result

    return search_records(records, keyword=keyword, category=category)


def attach_distance_fields(
    records: list[Record],
    *,
    start_node_id: str = "",
    distance_provider: DistanceProvider | None = None,
    distance_strategy: str = "shortest_distance",
) -> list[Record]:
    """
    给推荐结果补充距离字段。

    当前 C 的景点数据还没有稳定的 `node_id`，因此本函数会兼容缺字段情况，
    不会因为无法计算距离而丢弃推荐结果。
    """
    if not start_node_id:
        return [record.copy() for record in records]

    enriched: list[Record] = []
    for record in records:
        copied = record.copy()
        target_node_id = resolve_target_node_id(copied)

        copied["target_node_id"] = target_node_id
        copied["distance_strategy"] = distance_strategy

        if not target_node_id:
            _mark_distance_unavailable(copied, "missing_node_id")
        elif distance_provider is None:
            _mark_distance_unavailable(copied, "distance_provider_missing")
        else:
            _fill_distance(copied, start_node_id, target_node_id, distance_provider, distance_strategy)

        enriched.append(copied)

    return enriched


def resolve_distance_provider(
    *,
    start_node_id: str,
    distance_provider: DistanceProvider | None = None,
    use_default_distance_provider: bool = True,
) -> DistanceProvider | None:
    """解析本次查询使用的距离 provider。"""
    if not start_node_id:
        return None
    if distance_provider is not None:
        return distance_provider
    if not use_default_distance_provider:
        return None
    return build_distance_provider()


def resolve_target_node_id(record: Record) -> str:
    """从推荐记录中解析图节点 ID。"""
    for field in ("node_id", "map_node_id", "target_node_id"):
        value = str(record.get(field, "")).strip()
        if value:
            return value
    return ""


def rank_records(
    records: list[Record],
    *,
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 10,
) -> list[Record]:
    """按指定字段选出推荐结果。"""
    return recommend_top_k(
        records,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
    )


def build_response_metadata(
    *,
    records: list[Record],
    sort_field: str,
    sort_order: str,
    limit: int,
    start_node_id: str,
    distance_strategy: str,
    distance_provider_active: bool,
) -> dict[str, Any]:
    """构造统一响应的业务元信息。"""
    status_counts = count_distance_status(records)
    return {
        "ranking": {
            "sort_field": sort_field,
            "sort_order": sort_order,
            "limit": limit,
            "distance_used_for_ranking": sort_field == "distance_m",
        },
        "distance": {
            "requested": bool(start_node_id),
            "provider_active": distance_provider_active,
            "start_node_id": start_node_id,
            "strategy": distance_strategy,
            "unit": resolve_distance_unit(distance_strategy),
            "status_counts": status_counts,
            "available_count": status_counts.get("available", 0),
            "unavailable_count": sum(
                count
                for status, count in status_counts.items()
                if status != "available"
            ),
        },
        "result_fields": [
            "id",
            "name",
            "category",
            "heat",
            "rating",
            "target_node_id",
            "distance_m",
            "distance_status",
        ],
    }


def count_distance_status(records: list[Record]) -> dict[str, int]:
    """统计结果中的距离状态。"""
    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("distance_status", "not_requested"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def resolve_distance_unit(distance_strategy: str) -> str:
    """解析距离相关字段的单位说明。"""
    if distance_strategy == "shortest_distance":
        return "meter"
    if distance_strategy == "shortest_time":
        return "time_weight"
    return "unknown"


def _fill_distance(
    record: Record,
    start_node_id: str,
    target_node_id: str,
    distance_provider: DistanceProvider,
    distance_strategy: str,
) -> None:
    try:
        raw_distance = distance_provider(start_node_id, target_node_id, distance_strategy)
        distance = float(raw_distance)
    except (TypeError, ValueError, OverflowError):
        _mark_distance_unavailable(record, "distance_error")
        return

    if math.isinf(distance):
        _mark_distance_unavailable(record, "unreachable")
        return

    record["distance_value"] = distance
    record["distance_status"] = "available"
    record["distance_m"] = distance if distance_strategy == "shortest_distance" else None


def _mark_distance_unavailable(record: Record, status: str) -> None:
    record["distance_value"] = None
    record["distance_m"] = None
    record["distance_status"] = status


def _resolve_sort_order(sort_field: str, sort_order: str) -> str:
    normalized_order = sort_order.strip().lower()
    if normalized_order in {"asc", "desc"}:
        return normalized_order
    if sort_field == "distance_m":
        return "asc"
    return "desc"
