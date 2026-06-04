"""
成员 B：模糊查询模块

本模块用于处理：

- 名称片段匹配
- 标签匹配
- 关键字匹配
- 描述补充召回
- 错字容忍和跳字缩写召回
- 多关键词覆盖排序

当前实现继续保持轻量，但补强了名称、标签、关键词、描述的权重，
并补充了同义词归一化、拼音首字母、编辑距离、标点归一化和跳字缩写支持，
便于第九至第十周场所查询和美食推荐直接复用。

后续如有需要，可继续扩展：
- Trie 前缀匹配
- 更完整的拼音字典
- 更完整的同义词词典
"""

from __future__ import annotations

import re
from typing import Any


Record = dict[str, Any]
MatchDetail = dict[str, Any]

DIRECT_QUERY_TERM_BONUS = 6

TERM_EQUIVALENT_GROUPS = (
    ("洗手间", "卫生间", "厕所", "公厕", "wc", "restroom", "toilet", "washroom", "lavatory", "xsj"),
    ("食堂", "餐厅", "餐饮", "catering", "st"),
    ("便利店", "超市", "商店", "shopping", "bld"),
    ("图书馆", "tsg", "library"),
    ("阅览室", "自习室", "自习", "yls", "zxs"),
    ("教学楼", "教室楼", "教室", "上课", "jxl"),
    ("宿舍", "寝室", "公寓", "学生公寓", "ss"),
    ("体育场", "操场", "运动场", "体育馆", "tyc"),
    ("校门", "大门", "入口", "xm"),
    ("广场", "中心广场", "square", "gc"),
    ("停车", "停车场", "车库", "parking", "tc"),
    ("咖啡", "coffee", "kf"),
    ("未名湖", "湖", "wml"),
)

SEPARATOR_PATTERN = re.compile(r"[\s,，。.;；:：、/\\|_\-+()（）\[\]【】{}<>《》\"'`~!！?？@#$%^&*=]+")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def normalize_match_text(value: Any) -> str:
    """归一化参与匹配的文本，忽略空白和常见标点。"""
    return SEPARATOR_PATTERN.sub("", normalize_text(value))


def build_term_aliases() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for group in TERM_EQUIVALENT_GROUPS:
        normalized_group = [normalize_match_text(term) for term in group if normalize_match_text(term)]
        for term in normalized_group:
            aliases[term] = [candidate for candidate in normalized_group if candidate != term]
    return aliases


TERM_ALIASES = build_term_aliases()


def expand_query_term(term: str) -> list[str]:
    normalized_term = normalize_match_text(term)
    if not normalized_term:
        return []

    ordered_terms: list[str] = [normalized_term]
    for candidate in TERM_ALIASES.get(normalized_term, []):
        if candidate not in ordered_terms:
            ordered_terms.append(candidate)
    return ordered_terms


def split_search_term_groups(keyword: str) -> list[list[str]]:
    """提取查询词组；每组内是同一用户词项的同义表达。"""
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return []

    compact_keyword = normalize_match_text(normalized_keyword)
    raw_parts = [
        normalize_match_text(part)
        for part in SEPARATOR_PATTERN.split(normalized_keyword)
        if normalize_match_text(part)
    ]
    meaningful_parts = [
        part
        for part in raw_parts
        if len(part) > 1
    ]

    base_terms: list[str] = []
    if compact_keyword and len(meaningful_parts) < 2:
        base_terms.append(compact_keyword)
    if meaningful_parts:
        base_terms.extend(part for part in meaningful_parts if part != compact_keyword)
    elif not compact_keyword:
        base_terms.extend(raw_parts)

    seen_groups: set[tuple[str, ...]] = set()
    term_groups: list[list[str]] = []
    for term in base_terms:
        expanded_terms = unique_ordered(expand_query_term(term))
        if not expanded_terms:
            continue
        group_key = tuple(expanded_terms)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        term_groups.append(expanded_terms)

    return term_groups


def split_search_terms(keyword: str) -> list[str]:
    """兼容旧调用方：返回扁平化后的匹配词项。"""
    seen: set[str] = set()
    ordered_terms: list[str] = []
    for group in split_search_term_groups(keyword):
        for candidate in group:
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered_terms.append(candidate)

    return ordered_terms


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def flatten_field_values(value: Any) -> list[Any]:
    """把列表、字典和字符串字段统一摊平成可匹配值。"""
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


def score_collection(
    values: list[Any],
    term_groups: list[list[str]],
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> int:
    return score_collection_with_details(
        values,
        term_groups,
        exact_score=exact_score,
        prefix_score=prefix_score,
        contains_score=contains_score,
        subsequence_score=subsequence_score,
        approximate_score=approximate_score,
    )[0]


def score_collection_with_details(
    values: list[Any],
    term_groups: list[list[str]],
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> tuple[int, list[MatchDetail]]:
    """对一组字段值计算匹配得分。"""
    if not values or not term_groups:
        return 0, []

    normalized_values = [
        normalize_match_text(value)
        for value in values
        if normalize_match_text(value)
    ]
    if not normalized_values:
        return 0, []

    total_score = 0
    matched_group_count = 0
    details: list[MatchDetail] = []

    for group in term_groups:
        best_group_score = 0
        best_detail: MatchDetail | None = None
        direct_term = group[0] if group else ""
        for term_index, term in enumerate(group):
            for text in normalized_values:
                score, match_type = score_text_match(
                    term,
                    text,
                    exact_score=exact_score,
                    prefix_score=prefix_score,
                    contains_score=contains_score,
                    subsequence_score=subsequence_score,
                    approximate_score=approximate_score,
                )
                if score > 0 and term_index == 0 and term == direct_term:
                    score += DIRECT_QUERY_TERM_BONUS
                if score > best_group_score:
                    best_group_score = score
                    best_detail = {
                        "term": term,
                        "matched_text": text,
                        "match_type": match_type,
                        "score": score,
                    }

        if best_group_score > 0:
            matched_group_count += 1
            total_score += best_group_score
            if best_detail is not None:
                details.append(best_detail)

    if total_score and matched_group_count > 1:
        total_score += matched_group_count * 8

    return total_score, details


def score_text_match(
    term: str,
    text: str,
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> tuple[int, str]:
    """计算单个查询词与单个字段文本的匹配分。"""
    if not term or not text:
        return 0, ""
    if text == term:
        return exact_score, "exact"
    if text.startswith(term):
        return prefix_score, "prefix"
    if term in text:
        return contains_score, "contains"
    if is_ascii_word(term):
        return 0, ""
    if is_ordered_subsequence(term, text):
        return subsequence_score, "subsequence"
    approximate = approximate_match_score(term, text, approximate_score)
    return (approximate, "typo") if approximate > 0 else (0, "")


def is_ascii_word(value: str) -> bool:
    """英文查询词只做可靠匹配，避免 washroom 误召回 classroom。"""
    return value.isascii() and any(char.isalpha() for char in value)


def is_ordered_subsequence(term: str, text: str) -> bool:
    """支持“图馆”命中“图书馆”这类跳字缩写，短词保持保守。"""
    if len(term) < 2 or len(text) < len(term):
        return False
    if len(term) == 2 and len(text) > 4:
        return False

    position = 0
    for char in text:
        if position < len(term) and term[position] == char:
            position += 1
    if position != len(term):
        return False

    density = len(term) / len(text)
    return density >= 0.4 or len(term) >= 3


def approximate_match_score(term: str, text: str, base_score: int) -> int:
    """计算保守编辑距离近似匹配分，整字段命中优先于长文本窗口命中。"""
    if not term or not text:
        return 0

    max_distance = allowed_edit_distance(term)
    if max_distance <= 0:
        return 0

    if _bounded_levenshtein_distance(term, text, max_distance) <= max_distance:
        return base_score + 18

    term_length = len(term)
    min_window = max(1, term_length - max_distance)
    max_window = min(len(text), term_length + max_distance)
    for window_length in range(min_window, max_window + 1):
        for start in range(0, len(text) - window_length + 1):
            window = text[start : start + window_length]
            if _bounded_levenshtein_distance(term, window, max_distance) <= max_distance:
                return max(1, base_score - 10)

    return 0


def allowed_edit_distance(term: str) -> int:
    """按查询词长度给出最大允许编辑距离，避免短词误召回。"""
    length = len(term)
    if length <= 2:
        return 0
    if length <= 4:
        return 1
    if length <= 8:
        return 2
    return 3


def _bounded_levenshtein_distance(left: str, right: str, max_distance: int) -> int:
    """计算带上限的 Levenshtein 距离，超过上限时提前返回。"""
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        row_min = current[0]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current[right_index - 1] + 1
            delete_cost = previous[right_index] + 1
            replace_cost = previous[right_index - 1] + (0 if left_char == right_char else 1)
            value = min(insert_cost, delete_cost, replace_cost)
            current.append(value)
            row_min = min(row_min, value)

        if row_min > max_distance:
            return max_distance + 1
        previous = current

    return previous[-1]


def calculate_match_score(record: Record, keyword: str) -> int:
    """
    计算单条记录对关键字的匹配分数。

    当前评分规则：
    - 名称：精确/前缀/包含匹配权重最高
    - keywords：强调业务关键词和设施词
    - tags：次高权重，适合“洗手间/便利店/轻食”类查询
    - description：补充召回，不抢占名称优先级

    当前额外支持：
    - 忽略常见空白和标点
    - 多关键词覆盖加权
    - 保守编辑距离错字召回
    - 有序跳字缩写召回
    """
    term_groups = split_search_term_groups(keyword)
    if not term_groups:
        return 0

    return calculate_match(record, keyword)["score"]


def calculate_match(record: Record, keyword: str) -> dict[str, Any]:
    """计算匹配总分和用于 UI 展示的解释信息。"""
    term_groups = split_search_term_groups(keyword)
    if not term_groups:
        return {"score": 0, "details": []}

    name_score, name_details = score_collection_with_details(
        flatten_field_values(record.get("name")),
        term_groups,
        exact_score=160,
        prefix_score=120,
        contains_score=90,
        subsequence_score=72,
        approximate_score=64,
    )
    keyword_score, keyword_details = score_collection_with_details(
        flatten_field_values(record.get("keywords")),
        term_groups,
        exact_score=85,
        prefix_score=68,
        contains_score=52,
        subsequence_score=42,
        approximate_score=36,
    )
    tag_score, tag_details = score_collection_with_details(
        flatten_field_values(record.get("tags")),
        term_groups,
        exact_score=70,
        prefix_score=56,
        contains_score=42,
        subsequence_score=34,
        approximate_score=30,
    )
    description_score, description_details = score_collection_with_details(
        flatten_field_values(record.get("description")),
        term_groups,
        exact_score=36,
        prefix_score=30,
        contains_score=24,
        subsequence_score=16,
        approximate_score=12,
    )

    total_score = name_score + keyword_score + tag_score + description_score

    matched_field_count = sum(
        1
        for score in (name_score, keyword_score, tag_score, description_score)
        if score > 0
    )
    if matched_field_count > 1:
        total_score += matched_field_count * 4

    details = []
    for field_name, field_label, field_details in (
        ("name", "名称", name_details),
        ("keywords", "关键词", keyword_details),
        ("tags", "标签", tag_details),
        ("description", "描述", description_details),
    ):
        for detail in field_details:
            details.append({
                **detail,
                "field": field_name,
                "field_label": field_label,
            })

    return {
        "score": total_score,
        "details": sorted(
            details,
            key=lambda item: int(item.get("score", 0)),
            reverse=True,
        )[:4],
    }


def fuzzy_search(records: list[Record], keyword: str) -> list[Record]:
    """
    对记录做模糊查询。

    返回结果会附加字段：
    - `_match_score`

    输出按匹配分数从高到低排序；
    如果分数相同，则按热度从高到低排序。
    """
    if not split_search_terms(keyword):
        return records[:]

    matched: list[Record] = []
    for record in records:
        match = calculate_match(record, keyword)
        score = int(match.get("score", 0))
        if score <= 0:
            continue

        copied = record.copy()
        copied["_match_score"] = score
        copied["_match_detail"] = match.get("details", [])
        matched.append(copied)

    # 当前结果规模通常不大，先用简单插入排序整理模糊匹配结果
    return sort_fuzzy_results(matched)


def sort_fuzzy_results(records: list[Record]) -> list[Record]:
    """
    对模糊查询结果做排序：
    1. 先按 _match_score 降序
    2. 再按 heat 降序
    3. 再按 rating 降序
    4. 最后按名称字典序升序，确保结果稳定
    """
    result = records[:]

    for i in range(1, len(result)):
        current = result[i]
        current_score = int(current.get("_match_score", 0))
        current_heat = float(current.get("heat", 0))
        current_rating = float(current.get("rating", 0))
        current_name = normalize_text(current.get("name"))
        j = i - 1

        while j >= 0:
            left_score = int(result[j].get("_match_score", 0))
            left_heat = float(result[j].get("heat", 0))
            left_rating = float(result[j].get("rating", 0))
            left_name = normalize_text(result[j].get("name"))

            should_move = False
            if left_score < current_score:
                should_move = True
            elif left_score == current_score and left_heat < current_heat:
                should_move = True
            elif left_score == current_score and left_heat == current_heat and left_rating < current_rating:
                should_move = True
            elif (
                left_score == current_score
                and left_heat == current_heat
                and left_rating == current_rating
                and left_name > current_name
            ):
                should_move = True

            if not should_move:
                break

            result[j + 1] = result[j]
            j -= 1

        result[j + 1] = current

    return result
