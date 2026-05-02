"""
成员 B：第九周餐饮推荐业务入口

本模块在通用 `search_and_recommend(...)` 之上补一层餐饮业务封装，
用于“食堂 / 咖啡厅 / 轻食”等 `category="catering"` 的推荐场景。
"""

from __future__ import annotations

from typing import Any

from src.search.exact_search import canonicalize_category
from src.search.search_service import (
    decorate_business_response,
    get_default_site_id,
    load_site_records,
    resolve_business_sort_field,
    search_and_recommend,
)


Record = dict[str, Any]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def matches_cuisine(record: Record, cuisine: str) -> bool:
    """兼容标准字段缺失时的菜系筛选。"""
    normalized_cuisine = normalize_text(cuisine)
    if not normalized_cuisine:
        return True

    candidates: list[str] = []
    raw_cuisine = record.get("cuisine")
    if isinstance(raw_cuisine, list):
        candidates.extend(str(item) for item in raw_cuisine)
    elif raw_cuisine:
        candidates.append(str(raw_cuisine))

    for key in ("tags", "keywords"):
        candidates.extend(str(item) for item in record.get(key, []))

    for key in ("name", "description", "open_hours"):
        value = record.get(key)
        if value:
            candidates.append(str(value))

    return any(normalized_cuisine in normalize_text(candidate) for candidate in candidates)


def filter_catering_records(
    records: list[Record],
    *,
    cuisine: str = "",
) -> list[Record]:
    """筛选餐饮记录，并可选按菜系/关键词做最小兼容过滤。"""
    return [
        record
        for record in records
        if canonicalize_category(record.get("category")) == "catering"
        and matches_cuisine(record, cuisine)
    ]


def recommend_catering(
    *,
    keyword: str = "",
    cuisine: str = "",
    site_id: str | None = None,
    start_node_id: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 5,
    records: list[Record] | None = None,
    distance_provider: Any | None = None,
    use_default_distance_provider: bool = True,
    distance_strategy: str = "shortest_distance",
) -> dict[str, Any]:
    """第九周新增：餐饮推荐业务入口。"""
    effective_sort_field = resolve_business_sort_field(
        sort_field,
        default="distance_m" if start_node_id else "heat",
    )
    source_records = records[:] if records is not None else load_site_records(site_id)
    catering_records = filter_catering_records(source_records, cuisine=cuisine)

    response = search_and_recommend(
        keyword=keyword,
        category="catering",
        start_node_id=start_node_id,
        match_mode=match_mode,
        sort_field=effective_sort_field,
        sort_order=sort_order,
        limit=limit,
        records=catering_records,
        distance_provider=distance_provider,
        use_default_distance_provider=use_default_distance_provider,
        distance_strategy=distance_strategy,
    )
    resolved_sort_order = str(response.get("filters", {}).get("sort_order", sort_order))

    return decorate_business_response(
        response,
        query_type="catering_recommend",
        extra_filters={
            "keyword": keyword,
            "category": "catering",
            "cuisine": cuisine,
            "site_id": site_id or get_default_site_id(),
            "start_node_id": start_node_id,
            "match_mode": match_mode,
            "sort_field": effective_sort_field,
            "sort_order": resolved_sort_order,
            "limit": limit,
            "distance_strategy": distance_strategy,
        },
        extra_metadata={
            "business": {
                "scope": "catering",
                "cuisine_filter_active": bool(cuisine),
            }
        },
    )
