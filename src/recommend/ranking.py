"""
成员 B：推荐排序策略层

本模块在底层 `top_k` 之上封装业务推荐排序策略，重点解决第八周新增的
距离字段排序问题：

- `distance_m` 默认按升序排序，表示“更近的优先推荐”
- 缺失距离或不可达记录不丢弃，但排序时放在可计算距离记录之后
- 距离相同时继续按热度、评分做稳定展示
"""

from __future__ import annotations

import math
from typing import Any

from src.recommend.sorter import sort_records
from src.recommend.topk import top_k


Record = dict[str, Any]
SortRule = dict[str, str]

DISTANCE_FIELD = "distance_m"
DISTANCE_RANK_FIELD = "_distance_rank"
MATCH_SCORE_FIELD = "_match_score"


def recommend_top_k(
    records: list[Record],
    *,
    sort_field: str = "heat",
    limit: int = 10,
    sort_order: str = "",
) -> list[Record]:
    """
    返回业务推荐场景下的 Top-K 结果。

    与底层 `top_k` 的区别：
    - 识别 `distance_m`，并将缺失距离转换为无穷大，避免缺失距离被误认为 0。
    - 为最终输出补充稳定的多字段展示顺序。
    - 输出前移除内部排序字段，避免污染业务响应。
    """
    if limit <= 0 or not records:
        return []

    effective_order = resolve_recommend_order(sort_field, sort_order)
    prepared_records = prepare_ranking_records(records)
    ranking_field = resolve_ranking_field(sort_field)

    if has_match_scores(prepared_records):
        sorted_selected = sort_records(
            prepared_records,
            build_match_first_sort_rules(sort_field, ranking_field, effective_order),
        )
        return strip_internal_ranking_fields(sorted_selected[:limit])

    if len(prepared_records) > limit:
        selected = top_k(
            prepared_records,
            field=ranking_field,
            k=limit,
            order=effective_order,
        )
    else:
        selected = prepared_records[:]

    sorted_selected = sort_records(
        selected,
        build_recommend_sort_rules(sort_field, ranking_field, effective_order),
    )
    return strip_internal_ranking_fields(sorted_selected)


def prepare_ranking_records(records: list[Record]) -> list[Record]:
    """复制记录并补充距离排序内部字段。"""
    prepared: list[Record] = []
    for record in records:
        copied = record.copy()
        copied[DISTANCE_RANK_FIELD] = get_distance_rank_value(copied)
        prepared.append(copied)
    return prepared


def get_distance_rank_value(record: Record) -> float:
    """将距离字段转换为排序值；缺失、不可达、非数字统一放到最后。"""
    value = record.get(DISTANCE_FIELD)
    try:
        distance = float(value)
    except (TypeError, ValueError):
        return float("inf")

    if math.isinf(distance) or math.isnan(distance):
        return float("inf")
    return distance


def has_match_scores(records: list[Record]) -> bool:
    """判断当前结果是否来自模糊匹配链路。"""
    return any(MATCH_SCORE_FIELD in record for record in records)


def resolve_ranking_field(sort_field: str) -> str:
    """将业务排序字段映射到底层 Top-K 使用的字段。"""
    if sort_field == DISTANCE_FIELD:
        return DISTANCE_RANK_FIELD
    return sort_field


def resolve_recommend_order(sort_field: str, sort_order: str = "") -> str:
    """解析推荐排序方向。"""
    normalized_order = sort_order.strip().lower()
    if normalized_order in {"asc", "desc"}:
        return normalized_order
    if sort_field == DISTANCE_FIELD:
        return "asc"
    return "desc"


def build_recommend_sort_rules(
    sort_field: str,
    ranking_field: str,
    sort_order: str,
) -> list[SortRule]:
    """构造最终展示排序规则。"""
    rules: list[SortRule] = [{"field": ranking_field, "order": sort_order}]

    if sort_field == DISTANCE_FIELD:
        rules.extend(
            [
                {"field": "heat", "order": "desc"},
                {"field": "rating", "order": "desc"},
            ]
        )
    else:
        if sort_field != "rating":
            rules.append({"field": "rating", "order": "desc"})
        if sort_field != "heat":
            rules.append({"field": "heat", "order": "desc"})
        rules.append({"field": DISTANCE_RANK_FIELD, "order": "asc"})

    return rules


def build_match_first_sort_rules(
    sort_field: str,
    ranking_field: str,
    sort_order: str,
) -> list[SortRule]:
    """构造“先按匹配分，再按业务排序”的规则。"""
    rules: list[SortRule] = [{ "field": MATCH_SCORE_FIELD, "order": "desc" }]
    rules.extend(build_recommend_sort_rules(sort_field, ranking_field, sort_order))
    return rules


def strip_internal_ranking_fields(records: list[Record]) -> list[Record]:
    """移除内部排序字段。"""
    cleaned: list[Record] = []
    for record in records:
        copied = record.copy()
        copied.pop(DISTANCE_RANK_FIELD, None)
        cleaned.append(copied)
    return cleaned
