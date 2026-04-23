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
    """返回默认景点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "scenic_spots.json"


def get_member_c_scenic_data_path() -> Path:
    """返回成员 C 第七周提交的真实景点数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "成员Cdata" / "scenic_spots.json"


def resolve_scenic_data_path(
    data_path: str | Path | None = None,
    *,
    prefer_member_c: bool = False,
) -> Path:
    """解析本次查询应使用的景点数据文件。"""
    if data_path is not None:
        return Path(data_path)

    member_c_path = get_member_c_scenic_data_path()
    if prefer_member_c and member_c_path.exists():
        return member_c_path

    return get_default_scenic_data_path()


def load_scenic_spots(
    data_path: str | Path | None = None,
    *,
    prefer_member_c: bool = False,
) -> list[Record]:
    """加载景点数据。"""
    target_path = resolve_scenic_data_path(data_path, prefer_member_c=prefer_member_c)
    with target_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"scenic spots data must be a list: {target_path}")

    return data


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
