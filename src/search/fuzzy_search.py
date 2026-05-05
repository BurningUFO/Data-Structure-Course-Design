"""
成员 B：模糊查询模块

本模块用于处理：

- 名称片段匹配
- 标签匹配
- 关键字匹配
- 简单相似度排序

当前实现继续保持轻量，但补强了名称、标签、关键词、描述的权重，
并补充了最小同义词归一化、拼音首字母支持，
便于第九至第十周场所查询和美食推荐直接复用。

后续如有需要，可继续扩展：
- 编辑距离
- Trie 前缀匹配
- 更完整的拼音字典
- 更完整的同义词词典
"""

from __future__ import annotations

from typing import Any


Record = dict[str, Any]

TERM_EQUIVALENT_GROUPS = (
    ("洗手间", "卫生间", "厕所", "wc", "restroom", "xsj"),
    ("食堂", "餐厅", "餐饮", "catering", "st"),
    ("便利店", "超市", "商店", "shopping", "bld"),
    ("图书馆", "tsg", "library"),
    ("未名湖", "wml"),
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def build_term_aliases() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for group in TERM_EQUIVALENT_GROUPS:
        normalized_group = [normalize_text(term) for term in group if normalize_text(term)]
        for term in normalized_group:
            aliases[term] = [candidate for candidate in normalized_group if candidate != term]
    return aliases


TERM_ALIASES = build_term_aliases()


def expand_query_term(term: str) -> list[str]:
    normalized_term = normalize_text(term)
    if not normalized_term:
        return []

    ordered_terms: list[str] = [normalized_term]
    for candidate in TERM_ALIASES.get(normalized_term, []):
        if candidate not in ordered_terms:
            ordered_terms.append(candidate)
    return ordered_terms


def split_search_terms(keyword: str) -> list[str]:
    """提取模糊查询中需要参与匹配的词项。"""
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return []

    terms = [normalized_keyword]
    terms.extend(
        part
        for part in normalized_keyword.split()
        if part and part != normalized_keyword
    )

    seen: set[str] = set()
    ordered_terms: list[str] = []
    for term in terms:
        for candidate in expand_query_term(term):
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered_terms.append(candidate)

    return ordered_terms


def score_collection(
    values: list[Any],
    terms: list[str],
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
) -> int:
    """对一组字段值计算匹配得分。"""
    if not values or not terms:
        return 0

    best_score = 0
    matched_terms: set[str] = set()

    for value in values:
        text = normalize_text(value)
        if not text:
            continue

        for term in terms:
            if text == term:
                best_score = max(best_score, exact_score)
                matched_terms.add(term)
            elif text.startswith(term):
                best_score = max(best_score, prefix_score)
                matched_terms.add(term)
            elif term in text:
                best_score = max(best_score, contains_score)
                matched_terms.add(term)

    if best_score and len(terms) > 1:
        best_score += min(len(matched_terms), len(terms)) * 5

    return best_score


def calculate_match_score(record: Record, keyword: str) -> int:
    """
    计算单条记录对关键字的匹配分数。

    当前评分规则：
    - 名称：精确/前缀/包含匹配权重最高
    - keywords：强调业务关键词和设施词
    - tags：次高权重，适合“洗手间/便利店/轻食”类查询
    - description：补充召回，不抢占名称优先级

    当前仍不支持：
    - 编辑距离阈值
    """
    terms = split_search_terms(keyword)
    if not terms:
        return 0

    name_score = score_collection(
        [record.get("name")],
        terms,
        exact_score=160,
        prefix_score=120,
        contains_score=90,
    )
    keyword_score = score_collection(
        list(record.get("keywords", [])),
        terms,
        exact_score=85,
        prefix_score=68,
        contains_score=52,
    )
    tag_score = score_collection(
        list(record.get("tags", [])),
        terms,
        exact_score=70,
        prefix_score=56,
        contains_score=42,
    )
    description_score = score_collection(
        [record.get("description")],
        terms,
        exact_score=36,
        prefix_score=30,
        contains_score=24,
    )

    total_score = name_score + keyword_score + tag_score + description_score

    matched_field_count = sum(
        1
        for score in (name_score, keyword_score, tag_score, description_score)
        if score > 0
    )
    if matched_field_count > 1:
        total_score += matched_field_count * 4

    return total_score


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
        score = calculate_match_score(record, keyword)
        if score <= 0:
            continue

        copied = record.copy()
        copied["_match_score"] = score
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
