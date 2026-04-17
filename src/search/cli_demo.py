"""
成员 B：第七周 CLI 演示脚本

演示目标：
- 用户输入关键字
- 系统查询景点 / 学校数据
- 调用排序与 Top-K
- 返回统一格式的 Top-10 结果

当前演示数据使用：
- data/scenic_spots.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.recommend.sorter import sort_records
from src.recommend.topk import top_k
from src.search.exact_search import search_records
from src.search.fuzzy_search import fuzzy_search
from src.search.response import build_error_response, build_success_response


def load_scenic_spots() -> list[dict[str, Any]]:
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "..", "data", "scenic_spots.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_and_recommend(
    *,
    keyword: str,
    category: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    limit: int = 10,
) -> dict[str, Any]:
    records = load_scenic_spots()

    if not keyword and not category:
        return build_error_response(
            "keyword and category cannot both be empty",
            query_type="scenic_search",
            filters={
                "keyword": keyword,
                "category": category,
                "match_mode": match_mode,
                "sort_field": sort_field,
                "limit": limit,
            },
        )

    if match_mode == "fuzzy":
        filtered = fuzzy_search(records, keyword) if keyword else records[:]
        if category:
            filtered = [item for item in filtered if item.get("category") == category]
    else:
        filtered = search_records(records, keyword=keyword, category=category)

    if not filtered:
        return build_success_response(
            data=[],
            message="no matched records",
            query_type="scenic_search",
            filters={
                "keyword": keyword,
                "category": category,
                "match_mode": match_mode,
                "sort_field": sort_field,
                "limit": limit,
            },
        )

    # 先按指定字段排序，保证结果组织清晰
    sorted_records = sort_records(
        filtered,
        [{"field": sort_field, "order": "desc"}],
    )

    # 若结果规模较大，则使用 Top-K 缩减结果
    if len(sorted_records) > limit:
        top_records = top_k(sorted_records, field=sort_field, k=limit, order="desc")
    else:
        top_records = sorted_records[:limit]

    return build_success_response(
        data=top_records,
        message="query success",
        query_type="scenic_search",
        filters={
            "keyword": keyword,
            "category": category,
            "match_mode": match_mode,
            "sort_field": sort_field,
            "limit": limit,
        },
    )


def print_response(response: dict[str, Any]) -> None:
    print("=" * 60)
    print(f"success: {response['success']}")
    print(f"message: {response['message']}")
    print(f"query_type: {response['query_type']}")
    print(f"total: {response['total']}")
    print(f"filters: {response['filters']}")
    print("-" * 60)

    for index, item in enumerate(response["data"], start=1):
        print(
            f"{index}. {item.get('name')} | "
            f"category={item.get('category')} | "
            f"heat={item.get('heat')} | "
            f"rating={item.get('rating')}"
        )
    print("=" * 60)


def main() -> None:
    print("景点 / 学校查询 CLI 演示")
    keyword = input("请输入关键字：").strip()
    category = input("请输入类别（可留空）：").strip()

    response = query_and_recommend(
        keyword=keyword,
        category=category,
        match_mode="fuzzy",
        sort_field="heat",
        limit=10,
    )
    print_response(response)


if __name__ == "__main__":
    main()
