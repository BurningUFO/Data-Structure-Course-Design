"""
成员 B：基础精确查询与条件过滤模块

本模块负责成员 B 第七周第一条业务链路中的“查”这一环，
主要提供：

- 按名称精确查询
- 按类别过滤
- 按关键字匹配
- 组合条件查询

说明：
- 当前实现面向字典列表数据，便于直接对接 JSON 数据
- 本模块先解决“基础查询”，后续模糊查询逻辑放在 `fuzzy_search.py`
"""

from __future__ import annotations

from typing import Any


Record = dict[str, Any]

CATEGORY_ALIASES = {
    "restroom": "restroom",
    "washroom": "restroom",
    "toilet": "restroom",
    "wc": "restroom",
    "洗手间": "restroom",
    "卫生间": "restroom",
    "厕所": "restroom",
    "公厕": "restroom",
    "catering": "catering",
    "food": "catering",
    "餐饮": "catering",
    "食堂": "catering",
    "美食": "catering",
    "咖啡": "catering",
    "咖啡厅": "catering",
    "shopping": "shopping",
    "store": "shopping",
    "retail": "shopping",
    "购物": "shopping",
    "商店": "shopping",
    "便利店": "shopping",
    "parking": "parking",
    "停车": "parking",
    "停车场": "parking",
    "education": "education",
    "教育": "education",
    "教学": "education",
    "教学楼": "education",
}


def normalize_text(value: Any) -> str:
    """将输入统一转为便于比较的字符串格式。"""
    if value is None:
        return ""
    return str(value).strip().casefold()


def canonicalize_category(value: Any) -> str:
    """将常见中英文类别别名归一化为统一业务类别。"""
    normalized = normalize_text(value)
    return CATEGORY_ALIASES.get(normalized, normalized)


def filter_by_name(records: list[Record], name: str) -> list[Record]:
    """
    按名称精确查询。

    这里采用大小写无关、去首尾空白的精确比较。
    """
    normalized_name = normalize_text(name)
    if not normalized_name:
        return records[:]

    result: list[Record] = []
    for record in records:
        if normalize_text(record.get("name")) == normalized_name:
            result.append(record)
    return result


def filter_by_category(records: list[Record], category: str) -> list[Record]:
    """按类别过滤。"""
    normalized_category = canonicalize_category(category)
    if not normalized_category:
        return records[:]

    result: list[Record] = []
    for record in records:
        if canonicalize_category(record.get("category")) == normalized_category:
            result.append(record)
    return result


def filter_by_keyword(records: list[Record], keyword: str) -> list[Record]:
    """
    按关键字做基础匹配。

    匹配范围包括：
    - name
    - description
    - keywords 数组
    - tags 数组
    """
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return records[:]

    result: list[Record] = []
    for record in records:
        name = normalize_text(record.get("name"))
        description = normalize_text(record.get("description"))
        keywords = [normalize_text(item) for item in record.get("keywords", [])]
        tags = [normalize_text(item) for item in record.get("tags", [])]

        if normalized_keyword in name:
            result.append(record)
            continue
        if normalized_keyword in description:
            result.append(record)
            continue
        if any(normalized_keyword in item for item in keywords):
            result.append(record)
            continue
        if any(normalized_keyword in item for item in tags):
            result.append(record)

    return result


def filter_by_site(records: list[Record], site_id: str) -> list[Record]:
    """按景区 / 校园范围过滤。当前字段不存在时不报错。"""
    normalized_site_id = normalize_text(site_id)
    if not normalized_site_id:
        return records[:]

    result: list[Record] = []
    for record in records:
        if normalize_text(record.get("site_id")) == normalized_site_id:
            result.append(record)
    return result


def search_records(
    records: list[Record],
    *,
    name: str = "",
    category: str = "",
    keyword: str = "",
    site_id: str = "",
) -> list[Record]:
    """
    组合条件查询入口。

    建议使用顺序：
    1. 若给出 name，则先按精确名称过滤
    2. 再按 category 过滤
    3. 再按 keyword 匹配
    4. 最后按 site_id 限定范围

    返回新列表，不修改原始 records。
    """
    result = records[:]

    if name:
        result = filter_by_name(result, name)
    if category:
        result = filter_by_category(result, category)
    if keyword:
        result = filter_by_keyword(result, keyword)
    if site_id:
        result = filter_by_site(result, site_id)

    return result
