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
WEIGHTED_SORT_FIELD = "weighted"
RECOMMENDATION_SCORE_FIELD = "recommendation_score"
DEFAULT_WEIGHTED_RANKING_WEIGHTS = {
    "heat": 0.4,
    "rating": 0.3,
    DISTANCE_FIELD: 0.3,
}
WEIGHTED_RANKING_FIELDS = tuple(DEFAULT_WEIGHTED_RANKING_WEIGHTS)
WEIGHTED_DISTANCE_LIMIT_M = 1500.0


def recommend_top_k(
    records: list[Record],
    *,
    sort_field: str = "heat",
    limit: int = 10,
    sort_order: str = "",
    match_score_primary: bool = True,
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

    if has_match_scores(prepared_records) and match_score_primary:
        sorted_selected = sort_records(
            prepared_records,
            build_match_score_first_sort_rules(sort_field, ranking_field, effective_order),
        )
        return strip_internal_ranking_fields(sorted_selected[:limit])

    selected = select_top_k_records(
        prepared_records,
        field=ranking_field,
        limit=limit,
        order=effective_order,
    )

    sorted_selected = sort_records(
        selected,
        (
            build_match_first_sort_rules(sort_field, ranking_field, effective_order)
            if has_match_scores(prepared_records)
            else build_recommend_sort_rules(sort_field, ranking_field, effective_order)
        ),
    )
    return strip_internal_ranking_fields(sorted_selected)


def normalize_weighted_ranking_weights(value: Any) -> dict[str, float]:
    """Normalize percentage-like user weights for heat, rating, and distance."""
    if not isinstance(value, dict):
        return dict(DEFAULT_WEIGHTED_RANKING_WEIGHTS)

    weights: dict[str, float] = {}
    total = 0.0
    for field in WEIGHTED_RANKING_FIELDS:
        try:
            weight = float(value.get(field, 0))
        except (TypeError, ValueError):
            weight = 0.0
        if math.isinf(weight) or math.isnan(weight) or weight < 0:
            weight = 0.0
        weights[field] = weight
        total += weight

    if total <= 0:
        return dict(DEFAULT_WEIGHTED_RANKING_WEIGHTS)
    return {field: round(weight / total, 6) for field, weight in weights.items()}


def weighted_ranking_metadata(
    *,
    active: bool,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Describe the weighted ranking contract in API metadata."""
    normalized_weights = weights or dict(DEFAULT_WEIGHTED_RANKING_WEIGHTS)
    return {
        "active": active,
        "weights": normalized_weights,
        "score_field": RECOMMENDATION_SCORE_FIELD,
        "component_field": "recommendation_components",
        "reason_field": "recommendation_reason",
        "distance_limit_m": WEIGHTED_DISTANCE_LIMIT_M,
    }


def rank_weighted_records(
    records: list[Record],
    *,
    weights: dict[str, float] | None = None,
    limit: int = 10,
) -> list[Record]:
    """Rank records by a user-configurable heat/rating/distance weighted score."""
    if limit <= 0 or not records:
        return []

    active_weights = weights or dict(DEFAULT_WEIGHTED_RANKING_WEIGHTS)
    scored_records = [enrich_weighted_record(record, active_weights) for record in records]
    selected = select_top_k_records(
        scored_records,
        field=RECOMMENDATION_SCORE_FIELD,
        limit=limit,
        order="desc",
    )
    ranked = sort_records(
        selected,
        [
            {"field": RECOMMENDATION_SCORE_FIELD, "order": "desc"},
            {"field": "heat", "order": "desc"},
            {"field": "rating", "order": "desc"},
            {"field": DISTANCE_RANK_FIELD, "order": "asc"},
            {"field": "id", "order": "asc"},
        ],
    )
    return strip_internal_ranking_fields(ranked)


def enrich_weighted_record(record: Record, weights: dict[str, float]) -> Record:
    copied = record.copy()
    components = build_weighted_components(copied)
    score = round(
        sum(components[field] * weights.get(field, 0.0) for field in WEIGHTED_RANKING_FIELDS) * 100,
        2,
    )
    copied[RECOMMENDATION_SCORE_FIELD] = score
    copied["recommendation_components"] = {
        "weights": weights,
        "normalized": components,
    }
    copied["recommendation_reason"] = build_weighted_reason(weights)
    copied[DISTANCE_RANK_FIELD] = get_distance_rank_value(copied)
    return copied


def build_weighted_components(record: Record) -> dict[str, float]:
    return {
        "heat": clamp(coerce_float(record.get("heat")) / 100.0),
        "rating": clamp(coerce_float(record.get("rating")) / 5.0),
        DISTANCE_FIELD: distance_component(record),
    }


def distance_component(record: Record) -> float:
    distance = coerce_float(record.get(DISTANCE_FIELD), default=math.inf)
    if math.isinf(distance) or math.isnan(distance) or distance < 0:
        return 0.0
    return clamp(1.0 - min(distance, WEIGHTED_DISTANCE_LIMIT_M) / WEIGHTED_DISTANCE_LIMIT_M)


def build_weighted_reason(weights: dict[str, float]) -> str:
    return (
        f"综合权重：热度 {weights.get('heat', 0.0) * 100:.0f}%、"
        f"评分 {weights.get('rating', 0.0) * 100:.0f}%、"
        f"距离 {weights.get(DISTANCE_FIELD, 0.0) * 100:.0f}%。"
    )


def coerce_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    if math.isnan(value):
        return lower
    return max(lower, min(upper, value))


def select_top_k_records(
    records: list[Record],
    *,
    field: str,
    limit: int,
    order: str,
) -> list[Record]:
    """先用堆选出前 K 条，避免为展示前 K 对全量候选做完整排序。"""
    if len(records) > limit:
        return top_k(
            records,
            field=field,
            k=limit,
            order=order,
        )
    return records[:]


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
    """构造“先按用户选择字段，再按匹配分兜底”的规则。"""
    rules = build_recommend_sort_rules(sort_field, ranking_field, sort_order)
    rules.insert(1, {"field": MATCH_SCORE_FIELD, "order": "desc"})
    return rules


def build_match_score_first_sort_rules(
    sort_field: str,
    ranking_field: str,
    sort_order: str,
) -> list[SortRule]:
    """构造旧版综合查询使用的“匹配分优先”排序规则。"""
    rules: list[SortRule] = [{"field": MATCH_SCORE_FIELD, "order": "desc"}]
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
