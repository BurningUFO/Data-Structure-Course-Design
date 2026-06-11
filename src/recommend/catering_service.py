"""
成员 B：第九周餐饮推荐业务入口

本模块在通用 `search_and_recommend(...)` 之上补一层餐饮业务封装，
用于“食堂 / 咖啡厅 / 轻食”等 `category="catering"` 的推荐场景。
"""

from __future__ import annotations

import re
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

QUERY_SEPARATOR_PATTERN = re.compile(r"[\s,，。.;；:：、/\\|_\-+()（）\[\]【】{}<>《》\"'`~!！?？@#$%^&*=]+")

CUISINE_KEYWORD_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("咖啡", ("咖啡", "cafe", "coffee", "拿铁")),
    ("轻食", ("轻食", "三明治", "沙拉", "简餐")),
    ("清真", ("清真",)),
    ("食堂", ("食堂", "canteen")),
    ("餐厅", ("餐厅", "餐馆", "餐吧", "restaurant")),
    ("快餐", ("快餐", "套餐")),
    ("包子", ("包子",)),
    ("自助", ("自助", "取餐")),
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def flatten_field_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, dict):
        values: list[Any] = []
        for key, nested_value in value.items():
            values.append(key)
            values.extend(flatten_field_values(nested_value))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(flatten_field_values(item))
        return values
    return [value]


def normalize_cuisine_values(value: Any) -> list[str]:
    values: list[str] = []
    for item in flatten_field_values(value):
        normalized = normalize_text(item)
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def collect_cuisine_candidates(record: Record) -> list[str]:
    values: list[Any] = []
    for key in ("cuisine", "cuisine_labels", "tags", "keywords", "facilities"):
        values.extend(flatten_field_values(record.get(key)))
    for key in ("name", "open_hours", "building_name", "indoor_building"):
        value = record.get(key)
        if value:
            values.append(value)
    return [normalize_text(value) for value in values if normalize_text(value)]


def split_direct_query_terms(keyword: str) -> list[str]:
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return []

    compact_keyword = QUERY_SEPARATOR_PATTERN.sub("", normalized_keyword)
    parts = [
        QUERY_SEPARATOR_PATTERN.sub("", part)
        for part in QUERY_SEPARATOR_PATTERN.split(normalized_keyword)
        if QUERY_SEPARATOR_PATTERN.sub("", part)
    ]
    if compact_keyword and len(parts) < 2:
        parts.insert(0, compact_keyword)

    terms: list[str] = []
    for part in parts:
        if len(part) <= 1 or part in terms:
            continue
        terms.append(part)
    return terms


def collect_keyword_candidates(record: Record) -> list[str]:
    values: list[Any] = []
    for key in (
        "name",
        "cuisine",
        "cuisine_labels",
        "tags",
        "keywords",
        "facilities",
        "building_name",
        "indoor_building",
        "restaurant_name",
        "window_name",
    ):
        values.extend(flatten_field_values(record.get(key)))
    return [normalize_text(value) for value in values if normalize_text(value)]


def matches_direct_keyword(record: Record, keyword: str) -> bool:
    terms = split_direct_query_terms(keyword)
    if not terms:
        return True

    candidates = collect_keyword_candidates(record)
    if not candidates:
        return False
    return any(
        term in candidate
        for term in terms
        for candidate in candidates
    )


def infer_cuisine_labels(record: Record) -> list[str]:
    """从结构化字段和文本字段中推断可展示、可筛选的菜系标签。"""
    labels = normalize_cuisine_values(record.get("cuisine"))
    candidate_text = " ".join(collect_cuisine_candidates(record))

    for label, keywords in CUISINE_KEYWORD_GROUPS:
        if any(normalize_text(keyword) in candidate_text for keyword in keywords):
            if label not in labels:
                labels.append(label)

    if not labels and canonicalize_category(record.get("category")) == "catering":
        labels.append("餐饮")
    return labels


def decorate_catering_record(record: Record) -> Record:
    copied = record.copy()
    cuisine_labels = infer_cuisine_labels(copied)
    copied["cuisine_labels"] = cuisine_labels
    if "cuisine" not in copied or not normalize_cuisine_values(copied.get("cuisine")):
        copied["cuisine"] = cuisine_labels
    return copied


def matches_cuisine(record: Record, cuisine: str) -> bool:
    """兼容标准字段缺失时的菜系筛选。"""
    normalized_cuisine = normalize_text(cuisine)
    if not normalized_cuisine:
        return True

    candidates = collect_cuisine_candidates(record)
    candidates.extend(infer_cuisine_labels(record))

    return any(normalized_cuisine in normalize_text(candidate) for candidate in candidates)


def filter_catering_records(
    records: list[Record],
    *,
    cuisine: str = "",
    keyword: str = "",
) -> list[Record]:
    """筛选餐饮记录，并可选按菜系/关键词做最小兼容过滤。"""
    catering_records = [
        decorate_catering_record(record)
        for record in records
        if canonicalize_category(record.get("category")) == "catering"
        and matches_cuisine(record, cuisine)
    ]

    direct_keyword_records = [
        record
        for record in catering_records
        if matches_direct_keyword(record, keyword)
    ]
    return direct_keyword_records or catering_records


def recommend_catering(
    *,
    keyword: str = "",
    cuisine: str = "",
    site_id: str | None = None,
    start_node_id: str = "",
    center_node_id: str = "",
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
    normalized_center_node_id = normalize_text(center_node_id)
    distance_origin_node_id = normalized_center_node_id or start_node_id
    effective_sort_field = resolve_business_sort_field(
        sort_field,
        default="distance_m" if distance_origin_node_id else "heat",
    )
    source_records = records[:] if records is not None else load_site_records(site_id)
    catering_records = filter_catering_records(source_records, cuisine=cuisine, keyword=keyword)

    response = search_and_recommend(
        keyword=keyword,
        category="catering",
        start_node_id=distance_origin_node_id,
        match_mode=match_mode,
        sort_field=effective_sort_field,
        sort_order=sort_order,
        limit=limit,
        records=catering_records,
        distance_provider=distance_provider,
        use_default_distance_provider=use_default_distance_provider,
        distance_strategy=distance_strategy,
        match_score_primary=False,
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
            "center_node_id": normalized_center_node_id,
            "distance_origin_node_id": distance_origin_node_id,
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
                "center_filter_active": bool(normalized_center_node_id),
                "distance_basis": "selected_center" if normalized_center_node_id else "current_start",
                "supported_cuisine_labels": [label for label, _ in CUISINE_KEYWORD_GROUPS],
            }
        },
    )
