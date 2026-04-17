"""
成员 B：模糊查询模块

本模块用于处理：

- 名称片段匹配
- 标签匹配
- 关键字匹配
- 简单相似度排序

当前实现先采用“包含匹配 + 匹配得分”的轻量方案，
便于尽快接入第七周的查询主链路。

后续如有需要，可继续扩展：
- 编辑距离
- Trie 前缀匹配
- 拼音首字母
- 同义词词典
"""

from __future__ import annotations

from typing import Any


Record = dict[str, Any]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def calculate_match_score(record: Record, keyword: str) -> int:
    """
    计算单条记录对关键字的匹配分数。

    当前评分规则：
    - 名称完全匹配：100
    - 名称包含关键字：60
    - keywords 中包含：30
    - tags 中包含：20
    - description 中包含：10
    """
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return 0

    name = normalize_text(record.get("name"))
    description = normalize_text(record.get("description"))
    keywords = [normalize_text(item) for item in record.get("keywords", [])]
    tags = [normalize_text(item) for item in record.get("tags", [])]

    score = 0

    if name == normalized_keyword:
        score += 100
    elif normalized_keyword in name:
        score += 60

    if any(normalized_keyword in item for item in keywords):
        score += 30

    if any(normalized_keyword in item for item in tags):
        score += 20

    if normalized_keyword in description:
        score += 10

    return score


def fuzzy_search(records: list[Record], keyword: str) -> list[Record]:
    """
    对记录做模糊查询。

    返回结果会附加字段：
    - `_match_score`

    输出按匹配分数从高到低排序；
    如果分数相同，则按热度从高到低排序。
    """
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return records[:]

    matched: list[Record] = []
    for record in records:
        score = calculate_match_score(record, normalized_keyword)
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
    """
    result = records[:]

    for i in range(1, len(result)):
        current = result[i]
        current_score = int(current.get("_match_score", 0))
        current_heat = float(current.get("heat", 0))
        j = i - 1

        while j >= 0:
            left_score = int(result[j].get("_match_score", 0))
            left_heat = float(result[j].get("heat", 0))

            should_move = False
            if left_score < current_score:
                should_move = True
            elif left_score == current_score and left_heat < current_heat:
                should_move = True

            if not should_move:
                break

            result[j + 1] = result[j]
            j -= 1

        result[j + 1] = current

    return result
