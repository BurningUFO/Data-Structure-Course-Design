"""Interest-aware recommendation helpers for PKU demo data.

The scoring model is intentionally small and explainable:
- category aliases capture coarse intent such as food, study, sports, or dorm life
- tags capture explicit curated matches
- keywords capture names, descriptions, destination text, and content snippets
- final ranking blends interest match, heat, rating, and optional distance
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.recommend.sorter import sort_records


Record = dict[str, Any]

INTEREST_SORT_FIELDS = {
    "interest",
    "interest_recommendation",
    "personalized",
    "personalized_recommendation",
}

SCENIC_INTEREST_WEIGHTS = {
    "interest_match_score": 0.45,
    "heat": 0.25,
    "rating": 0.20,
    "distance_m": 0.10,
}

DIARY_INTEREST_WEIGHTS = {
    "interest_match_score": 0.55,
    "heat": 0.25,
    "rating": 0.20,
}

CATEGORY_INTEREST_TERMS = {
    "education": ["学习", "自习", "阅览", "图书馆", "教学楼", "教室", "校园学习"],
    "reading_room": ["学习", "自习", "阅览", "图书馆"],
    "hall": ["讲堂", "活动", "文化", "校园活动"],
    "landmark": ["地标", "广场", "摄影", "历史文化", "文化", "未名湖", "湖泊"],
    "catering": ["美食", "食堂", "餐饮", "家常美食", "城市美食", "校园生活"],
    "shopping": ["购物", "便利店", "生活用品", "校园生活"],
    "dormitory": ["宿舍", "住宿", "校园生活", "校园心情", "日常"],
    "sports": ["运动", "跑步", "体育场", "体育", "挑战"],
    "service": ["服务", "校园生活"],
    "entrance": ["校门", "入口", "校园"],
    "building": ["建筑", "教学楼", "历史文化", "摄影"],
    "building_entrance": ["楼门", "入口", "建筑"],
    "restroom": ["洗手间", "卫生间", "服务"],
    "parking": ["停车", "车辆", "服务"],
}

INTEREST_SOURCE_WEIGHTS = {
    "category": 45.0,
    "tag": 35.0,
    "keyword": 20.0,
}


def get_default_users_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "users.json"


def load_users(
    data_path: str | Path | None = None,
    *,
    site_id: str | None = None,
) -> list[Record]:
    """Load sample users and optionally scope them to one home site."""
    path = Path(data_path) if data_path is not None else get_default_users_path()
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    users = [user for user in data if isinstance(user, dict)]
    normalized_site_id = normalize_text(site_id).upper()
    if normalized_site_id:
        users = [
            user
            for user in users
            if normalize_text(user.get("home_site_id")).upper() == normalized_site_id
        ]
    return users


def build_user_options(users: list[Record]) -> list[Record]:
    """Return UI-safe user summaries."""
    options: list[Record] = []
    for index, user in enumerate(users):
        user_id = normalize_display_text(user.get("id"))
        if not user_id:
            continue
        interests = normalize_interest_list(user.get("interests"))
        options.append(
            {
                "id": user_id,
                "name": normalize_display_text(user.get("name")) or user_id,
                "role": normalize_display_text(user.get("role")),
                "interests": interests,
                "interest_text": "，".join(interests),
                "home_site_id": normalize_display_text(user.get("home_site_id")),
                "is_default": index == 0,
            }
        )
    return options


def collect_interest_options(users: list[Record]) -> list[Record]:
    """Collect unique interests from sample users for lightweight UI chips/options."""
    counts: dict[str, int] = {}
    for user in users:
        for interest in normalize_interest_list(user.get("interests")):
            counts[interest] = counts.get(interest, 0) + 1

    return [
        {
            "value": interest,
            "label": interest,
            "user_count": counts[interest],
        }
        for interest in sorted(counts, key=lambda item: (-counts[item], item))
    ]


def resolve_user_by_id(users: list[Record], user_id: Any) -> Record | None:
    normalized_user_id = normalize_text(user_id)
    if not normalized_user_id:
        return None
    for user in users:
        if normalize_text(user.get("id")) == normalized_user_id:
            return user
    return None


def resolve_user_interests(users: list[Record], user_id: Any) -> list[str]:
    user = resolve_user_by_id(users, user_id)
    return normalize_interest_list(user.get("interests")) if user else []


def normalize_interest_list(value: Any) -> list[str]:
    """Normalize a list or comma-like text of user interests."""
    if value is None:
        return []

    if isinstance(value, str):
        candidates = split_interest_text(value)
    elif isinstance(value, (list, tuple, set)):
        candidates = []
        for item in value:
            candidates.extend(split_interest_text(item))
    else:
        candidates = split_interest_text(value)

    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text = normalize_display_text(item)
        key = normalize_text(text)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def split_interest_text(value: Any) -> list[str]:
    normalized = normalize_display_text(value)
    for separator in ("，", "、", ";", "；", "|", "\n", "\t"):
        normalized = normalized.replace(separator, ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def is_interest_sort_field(value: Any) -> bool:
    return normalize_text(value) in INTEREST_SORT_FIELDS


def interest_ranking_weights(*, include_distance: bool) -> dict[str, float]:
    return dict(SCENIC_INTEREST_WEIGHTS if include_distance else DIARY_INTEREST_WEIGHTS)


def enrich_interest_scores(
    records: list[Record],
    *,
    interests: Any,
    include_distance: bool = True,
    weights: dict[str, float] | None = None,
) -> list[Record]:
    """Return copied records with interest and composite recommendation fields."""
    normalized_interests = normalize_interest_list(interests)
    active_weights = weights or interest_ranking_weights(include_distance=include_distance)
    enriched: list[Record] = []

    for record in records:
        copied = record.copy()
        interest_match = build_interest_match(copied, normalized_interests)
        interest_score = interest_match["score"]
        components = build_recommendation_components(
            copied,
            interest_score=interest_score,
            include_distance=include_distance,
        )
        recommendation_score = round(
            sum(
                components.get(field, 0.0) * weight
                for field, weight in active_weights.items()
            )
            * 100,
            2,
        )

        copied["interest_match_score"] = interest_score
        copied["interest_match"] = interest_match
        copied["interest_reason"] = build_interest_reason(interest_match)
        copied["interest_recommendation_score"] = recommendation_score
        copied["recommendation_score"] = recommendation_score
        copied["recommendation_components"] = {
            "weights": active_weights,
            "normalized": components,
        }
        copied["_interest_distance_rank"] = distance_rank_value(copied)
        enriched.append(copied)

    return enriched


def rank_interest_aware_records(
    records: list[Record],
    *,
    interests: Any,
    limit: int = 10,
    include_distance: bool = True,
    weights: dict[str, float] | None = None,
) -> list[Record]:
    """Rank by interest-aware composite score and keep explanations on results."""
    if limit <= 0 or not records:
        return []

    enriched = enrich_interest_scores(
        records,
        interests=interests,
        include_distance=include_distance,
        weights=weights,
    )
    ranked = sort_records(
        enriched,
        [
            {"field": "recommendation_score", "order": "desc"},
            {"field": "interest_match_score", "order": "desc"},
            {"field": "heat", "order": "desc"},
            {"field": "rating", "order": "desc"},
            {"field": "_interest_distance_rank", "order": "asc"},
        ],
    )

    cleaned: list[Record] = []
    for record in ranked[:limit]:
        copied = record.copy()
        copied.pop("_interest_distance_rank", None)
        cleaned.append(copied)
    return cleaned


def build_interest_match(record: Record, interests: list[str]) -> Record:
    normalized_interests = normalize_interest_list(interests)
    if not normalized_interests:
        return {
            "score": 0.0,
            "interests": [],
            "matched_categories": [],
            "matched_tags": [],
            "matched_keywords": [],
            "source_scores": {
                "category": 0.0,
                "tag": 0.0,
                "keyword": 0.0,
            },
        }

    category_terms = category_terms_for_record(record)
    tag_terms = list_terms(record.get("tags")) + list_terms(record.get("facilities"))
    keyword_terms = keyword_terms_for_record(record)

    matched_categories = find_matching_terms(normalized_interests, category_terms)
    matched_tags = find_matching_terms(normalized_interests, tag_terms)
    matched_keywords = find_matching_terms(normalized_interests, keyword_terms)

    source_scores = {
        "category": INTEREST_SOURCE_WEIGHTS["category"] if matched_categories else 0.0,
        "tag": scaled_source_score(matched_tags, normalized_interests, INTEREST_SOURCE_WEIGHTS["tag"]),
        "keyword": scaled_source_score(
            matched_keywords,
            normalized_interests,
            INTEREST_SOURCE_WEIGHTS["keyword"],
        ),
    }
    score = round(min(100.0, sum(source_scores.values())), 2)

    return {
        "score": score,
        "interests": normalized_interests,
        "matched_categories": matched_categories,
        "matched_tags": matched_tags,
        "matched_keywords": matched_keywords,
        "source_scores": source_scores,
    }


def category_terms_for_record(record: Record) -> list[str]:
    category = normalize_display_text(record.get("category"))
    terms = [category]
    terms.extend(CATEGORY_INTEREST_TERMS.get(normalize_text(category), []))
    return unique_display_terms(terms)


def keyword_terms_for_record(record: Record) -> list[str]:
    terms: list[str] = []
    for field_name in (
        "name",
        "title",
        "destination",
        "description",
        "content",
        "type",
        "building_name",
        "indoor_building",
    ):
        value = record.get(field_name)
        if value:
            terms.append(str(value))
    terms.extend(list_terms(record.get("keywords")))
    return unique_display_terms(terms)


def find_matching_terms(interests: list[str], candidates: list[str]) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_text = normalize_display_text(candidate)
        candidate_key = normalize_text(candidate_text)
        if not candidate_key:
            continue
        for interest in interests:
            if text_matches(interest, candidate_text):
                if candidate_key not in seen:
                    seen.add(candidate_key)
                    matches.append(candidate_text)
                break
    return matches


def text_matches(interest: Any, candidate: Any) -> bool:
    left = normalize_text(interest)
    right = normalize_text(candidate)
    if not left or not right:
        return False
    return left in right or right in left


def scaled_source_score(matches: list[str], interests: list[str], max_score: float) -> float:
    if not matches:
        return 0.0
    expected_hits = max(1, min(2, len(interests)))
    return round(max_score * min(1.0, len(matches) / expected_hits), 2)


def build_recommendation_components(
    record: Record,
    *,
    interest_score: float,
    include_distance: bool,
) -> dict[str, float]:
    components = {
        "interest_match_score": clamp(float(interest_score) / 100.0),
        "heat": clamp(coerce_float(record.get("heat")) / 100.0),
        "rating": clamp(coerce_float(record.get("rating")) / 5.0),
    }
    if include_distance:
        components["distance_m"] = distance_component(record)
    return components


def distance_component(record: Record) -> float:
    distance = coerce_float(record.get("distance_m"), default=math.inf)
    if math.isinf(distance) or math.isnan(distance) or distance < 0:
        return 0.0
    return clamp(1.0 - min(distance, 1500.0) / 1500.0)


def distance_rank_value(record: Record) -> float:
    distance = coerce_float(record.get("distance_m"), default=math.inf)
    if math.isinf(distance) or math.isnan(distance):
        return math.inf
    return distance


def build_interest_reason(interest_match: Record) -> str:
    if not interest_match.get("interests"):
        return "未选择兴趣偏好，结果按基础排序展示。"

    pieces: list[str] = []
    if interest_match.get("matched_categories"):
        pieces.append(f"类别 {join_limited(interest_match['matched_categories'])}")
    if interest_match.get("matched_tags"):
        pieces.append(f"标签 {join_limited(interest_match['matched_tags'])}")
    if interest_match.get("matched_keywords"):
        pieces.append(f"关键词 {join_limited(interest_match['matched_keywords'])}")

    if not pieces:
        return "未命中当前兴趣，使用热度、评分和距离作为补位排序。"
    return f"兴趣命中：{'；'.join(pieces)}。"


def list_terms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_display_text(item) for item in value if normalize_display_text(item)]
    if value is None:
        return []
    text = normalize_display_text(value)
    return [text] if text else []


def unique_display_terms(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_display_text(value)
        key = normalize_text(text)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def join_limited(values: list[str], *, limit: int = 3) -> str:
    visible = values[:limit]
    suffix = "等" if len(values) > limit else ""
    return "、".join(visible) + suffix


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if math.isnan(value):
        return minimum
    return min(max(value, minimum), maximum)


def normalize_text(value: Any) -> str:
    return normalize_display_text(value).casefold()


def normalize_display_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
