"""
成员 B：CLI 演示脚本

演示目标：
- 用户输入关键字
- 系统查询景点 / 学校数据
- 调用排序与 Top-K
- 返回统一格式的 Top-10 结果

当前演示数据使用：
- data/scenic_spots.json
- 可选 data/成员Cdata/scenic_spots.json
"""

from __future__ import annotations

import os
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.search.search_service import search_and_recommend


SUPPORTED_SORT_FIELDS = {"heat", "rating", "distance_m"}


def query_and_recommend(
    *,
    keyword: str,
    category: str = "",
    start_node_id: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 10,
    prefer_member_c_data: bool = False,
    use_default_distance_provider: bool = True,
    distance_strategy: str = "shortest_distance",
    records: list[dict[str, Any]] | None = None,
    data_path: str | None = None,
) -> dict[str, Any]:
    """兼容第七周测试入口，实际业务逻辑已迁移到 search_service。"""
    return search_and_recommend(
        keyword=keyword,
        category=category,
        start_node_id=start_node_id,
        match_mode=match_mode,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
        records=records,
        data_path=data_path,
        prefer_member_c_data=prefer_member_c_data,
        use_default_distance_provider=use_default_distance_provider,
        distance_strategy=distance_strategy,
    )


def print_response(response: dict[str, Any]) -> None:
    """打印统一响应结构和 Top-N 推荐结果。"""
    print("=" * 72)
    print("Unified Response")
    print("-" * 72)
    print(f"success    : {response['success']}")
    print(f"message    : {response['message']}")
    print(f"query_type : {response['query_type']}")
    print(f"total      : {response['total']}")
    print(f"filters    : {response['filters']}")
    print_metadata(response.get("metadata", {}))
    print("-" * 72)
    print("Top Results")

    for index, item in enumerate(response["data"], start=1):
        print(
            f"{index:02d}. {item.get('name')} | "
            f"category={item.get('category')} | "
            f"heat={item.get('heat')} | "
            f"rating={item.get('rating')} | "
            f"target_node={item.get('target_node_id', '')} | "
            f"distance={_format_distance(item)}"
        )

    if not response["data"]:
        print("(empty)")

    print("=" * 72)


def print_metadata(metadata: dict[str, Any]) -> None:
    """打印统一 Response 中的 metadata 摘要。"""
    ranking = metadata.get("ranking", {})
    distance = metadata.get("distance", {})
    print("metadata:")
    print(
        "  ranking  : "
        f"field={ranking.get('sort_field')}, "
        f"order={ranking.get('sort_order')}, "
        f"limit={ranking.get('limit')}, "
        f"distance_rank={ranking.get('distance_used_for_ranking')}"
    )
    print(
        "  distance : "
        f"requested={distance.get('requested')}, "
        f"provider_active={distance.get('provider_active')}, "
        f"start_node={distance.get('start_node_id')}, "
        f"strategy={distance.get('strategy')}, "
        f"unit={distance.get('unit')}"
    )
    print(f"  status   : {distance.get('status_counts')}")


def _format_distance(item: dict[str, Any]) -> str:
    if "distance_status" not in item:
        return "not_requested"
    if item.get("distance_status") != "available":
        return str(item.get("distance_status"))
    distance = item.get("distance_m")
    if distance is None:
        return str(item.get("distance_value"))
    return f"{distance}m"


def _parse_limit(value: str, default: int = 10) -> int:
    try:
        limit = int(value)
    except ValueError:
        return default
    return limit if limit > 0 else default


def _parse_sort_field(value: str) -> str:
    sort_field = value.strip()
    if not sort_field:
        return "heat"
    if sort_field not in SUPPORTED_SORT_FIELDS:
        return "heat"
    return sort_field


def _parse_yes_no(value: str, default: bool = True) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"y", "yes", "1", "true", "是", "使用"}


def main() -> None:
    print("成员 B 第八周：查询 -> 推荐 -> 距离 -> 统一 Response CLI 演示")
    print("提示：当前 A 默认地图起点示例为 node_001；C 的真实景点数据暂缺 node_id，会显示 missing_node_id。")
    keyword = input("请输入关键字：").strip()
    category = input("请输入类别（可留空）：").strip()
    start_node_id = input("请输入起点节点 ID（可留空，例如 node_001）：").strip()
    sort_field = _parse_sort_field(input("排序字段 heat/rating/distance_m（默认 heat）："))
    limit = _parse_limit(input("返回数量（默认 10）："), default=10)
    prefer_member_c_data = _parse_yes_no(
        input("是否使用成员C真实景点数据？Y/n（默认 Y）："),
        default=True,
    )

    response = query_and_recommend(
        keyword=keyword,
        category=category,
        start_node_id=start_node_id,
        match_mode="fuzzy",
        sort_field=sort_field,
        limit=limit,
        prefer_member_c_data=prefer_member_c_data,
    )
    print_response(response)


if __name__ == "__main__":
    main()
