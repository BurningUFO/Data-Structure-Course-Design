"""
成员 B：通用排序模块

本模块提供基于归并排序（Merge Sort）的稳定多字段动态排序能力，
用于景点/学校推荐、美食推荐、日记推荐等场景。

说明：
- 不直接调用 `sorted()` 或列表 `.sort()` 完成核心排序逻辑
- 支持字典对象列表
- 支持多字段优先级排序
- 支持升序 / 降序

时间复杂度：
- 归并排序整体复杂度为 O(n log n)
- 空间复杂度为 O(n)
"""

from __future__ import annotations

from typing import Any


SortRule = dict[str, str]


def normalize_sort_rules(sort_rules: list[SortRule] | None) -> list[SortRule]:
    """
    将输入的排序规则标准化。

    输入示例：
    [
        {"field": "heat", "order": "desc"},
        {"field": "rating", "order": "desc"}
    ]
    """
    if not sort_rules:
        return [{"field": "heat", "order": "desc"}]

    normalized: list[SortRule] = []
    for rule in sort_rules:
        field = str(rule.get("field", "")).strip()
        if not field:
            continue
        order = str(rule.get("order", "desc")).strip().lower()
        if order not in {"asc", "desc"}:
            order = "desc"
        normalized.append({"field": field, "order": order})

    return normalized or [{"field": "heat", "order": "desc"}]


def get_record_value(record: dict[str, Any], field: str) -> Any:
    """读取记录中的排序字段，不存在时返回 None。"""
    return record.get(field)


def compare_records(
    left: dict[str, Any],
    right: dict[str, Any],
    sort_rules: list[SortRule],
) -> int:
    """
    比较两条记录的先后顺序。

    返回值：
    -1: left 应排在 right 前面
     0: 两者相等
     1: left 应排在 right 后面
    """
    for rule in sort_rules:
        field = rule["field"]
        order = rule["order"]

        left_value = get_record_value(left, field)
        right_value = get_record_value(right, field)

        # 缺失字段统一放在后面，避免影响有效数据排序
        if left_value is None and right_value is None:
            continue
        if left_value is None:
            return 1
        if right_value is None:
            return -1

        if left_value == right_value:
            continue

        if order == "desc":
            return -1 if left_value > right_value else 1
        return -1 if left_value < right_value else 1

    return 0


def merge(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    sort_rules: list[SortRule],
) -> list[dict[str, Any]]:
    """
    合并两个有序子序列。

    当比较结果相等时优先取 left，保证整体排序稳定。
    """
    merged: list[dict[str, Any]] = []
    i = 0
    j = 0

    while i < len(left) and j < len(right):
        result = compare_records(left[i], right[j], sort_rules)
        if result <= 0:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    while i < len(left):
        merged.append(left[i])
        i += 1

    while j < len(right):
        merged.append(right[j])
        j += 1

    return merged


def merge_sort(
    records: list[dict[str, Any]],
    sort_rules: list[SortRule],
) -> list[dict[str, Any]]:
    """基于归并排序实现稳定排序。"""
    if len(records) <= 1:
        return records[:]

    mid = len(records) // 2
    left_sorted = merge_sort(records[:mid], sort_rules)
    right_sorted = merge_sort(records[mid:], sort_rules)
    return merge(left_sorted, right_sorted, sort_rules)


def sort_records(
    records: list[dict[str, Any]],
    sort_rules: list[SortRule] | None = None,
) -> list[dict[str, Any]]:
    """
    对记录列表进行多字段动态排序。

    参数：
    - records: 记录列表，每项为字典
    - sort_rules: 排序规则列表，按优先级从高到低排列

    返回：
    - 排序后的新列表，不修改原列表
    """
    normalized_rules = normalize_sort_rules(sort_rules)
    return merge_sort(records, normalized_rules)
