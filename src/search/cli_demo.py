"""
成员 B：CLI 演示脚本

演示目标：
- 用户输入关键字
- 系统查询景点 / 学校数据
- 调用排序与 Top-K
- 返回统一格式的 Top-10 结果

当前演示数据使用：
- 默认标准数据：data/sites/PKU/*.json
- 兼容旧参考数据：data/成员Cdata/scenic_spots.json
"""

from __future__ import annotations

import os
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.diary.diary_service import search_diaries
from src.diary.diary_service import search_diaries_fulltext
from src.diary.diary_service import load_diary_records
from src.compress.huffman import compress_text, decompress_text
from src.recommend.catering_service import recommend_catering
from src.search.search_service import search_and_recommend
from src.search.search_service import search_places


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
    results = response.get("results", response.get("data", []))
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

    for index, item in enumerate(results, start=1):
        print(f"{index:02d}. {_format_result_item(item)}")

    if not results:
        print("(empty)")

    print("=" * 72)


def print_metadata(metadata: dict[str, Any]) -> None:
    """打印统一 Response 中的 metadata 摘要。"""
    ranking = metadata.get("ranking", {})
    distance = metadata.get("distance")
    print("metadata:")
    print(
        "  ranking  : "
        f"field={ranking.get('sort_field')}, "
        f"order={ranking.get('sort_order')}, "
        f"limit={ranking.get('limit')}, "
        f"distance_rank={ranking.get('distance_used_for_ranking')}"
    )
    if isinstance(distance, dict) and distance:
        print(
            "  distance : "
            f"requested={distance.get('requested')}, "
            f"provider_active={distance.get('provider_active')}, "
            f"start_node={distance.get('start_node_id')}, "
            f"strategy={distance.get('strategy')}, "
            f"unit={distance.get('unit')}"
        )
        print(f"  status   : {distance.get('status_counts')}")
    else:
        print("  distance : not_applicable")

    business = metadata.get("business")
    if business:
        print(f"  business : {business}")

    fulltext = metadata.get("fulltext")
    if fulltext:
        print(
            "  fulltext : "
            f"backend={fulltext.get('backend')}, "
            f"mode={fulltext.get('backend_mode')}, "
            f"tokens={fulltext.get('query_tokens')}, "
            f"route_hints={fulltext.get('route_hint_available_count')}"
        )
        index_manifest = fulltext.get("index_manifest")
        if isinstance(index_manifest, dict) and index_manifest:
            print(
                "  index    : "
                f"docs={index_manifest.get('document_count')}, "
                f"tokens={index_manifest.get('token_count')}, "
                f"tokenizer={index_manifest.get('tokenizer')}"
            )


def _format_distance(item: dict[str, Any]) -> str:
    if "distance_status" not in item:
        return "not_requested"
    if item.get("distance_status") != "available":
        return str(item.get("distance_status"))
    distance = item.get("distance_m")
    if distance is None:
        return str(item.get("distance_value"))
    return f"{distance}m"


def _format_result_item(item: dict[str, Any]) -> str:
    if "score" in item and "matched_terms" in item:
        return (
            f"{item.get('title')} | "
            f"matched_terms={item.get('matched_terms')} | "
            f"score={item.get('score')} | "
            f"destination={item.get('destination')} | "
            f"destination_node={item.get('destination_node_id')}"
        )

    if "title" in item:
        return (
            f"{item.get('title')} | "
            f"destination={item.get('destination')} | "
            f"heat={item.get('heat')} | "
            f"rating={item.get('rating')} | "
            f"destination_node={item.get('destination_node_id')}"
        )

    return (
        f"{item.get('name')} | "
        f"category={item.get('category')} | "
        f"heat={item.get('heat')} | "
        f"rating={item.get('rating')} | "
        f"target_node={item.get('target_node_id', '')} | "
        f"distance={_format_distance(item)}"
    )


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


def print_route_hint(item: dict[str, Any], *, start_node_id: str = "gate_north") -> None:
    target_node_id = str(
        item.get("target_node_id")
        or item.get("node_id")
        or item.get("destination_node_id")
        or ""
    ).strip()
    if not target_node_id:
        return

    print("Routing Hint")
    print(
        "python -B -c "
        f"\"from src.graph.loader import GraphLoader; "
        f"from src.routing.router import Router; "
        f"g = GraphLoader.load_site_graph('PKU'); "
        f"r = Router(g); "
        f"print(r.query_routing('{start_node_id}', '{target_node_id}'))\""
    )
    print("-" * 72)


def print_compression_demo(text: str, *, label: str) -> None:
    payload = compress_text(text)
    restored = decompress_text(payload)

    print(label)
    print(
        "  compression : "
        f"original={payload['original_size_bytes']}B, "
        f"bitstream={payload['bitstream_size_bytes']}B, "
        f"package_estimate={payload['estimated_package_size_bytes']}B, "
        f"ratio={payload['estimated_compression_ratio']}"
    )
    print(
        "  verify      : "
        f"restored_ok={restored == text}, "
        f"unique_chars={payload['unique_character_count']}, "
        f"bit_length={payload['bit_length']}"
    )
    print("-" * 72)


def run_week9_demo() -> None:
    """第九周统一演示入口。"""
    print("成员 B 第九周业务演示")
    print("=" * 72)

    print("[1] 场所查询：洗手间按真实距离排序")
    place_response = search_places(
        keyword="洗手间",
        category="restroom",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=3,
    )
    print_response(place_response)
    if place_response["data"]:
        print_route_hint(place_response["data"][0], start_node_id="gate_north")

    print("[2] 场所查询：便利店 / 教学楼按真实距离排序")
    for keyword, category in (("便利店", "shopping"), ("教学楼", "education")):
        response = search_places(
            keyword=keyword,
            category=category,
            start_node_id="gate_north",
            sort_field="distance_m",
            limit=3,
        )
        print_response(response)
        if response["data"]:
            print_route_hint(response["data"][0], start_node_id="gate_north")

    print("[3] 美食推荐：餐饮 Top-K")
    catering_response = recommend_catering(
        keyword="",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=2,
    )
    print_response(catering_response)
    if catering_response["data"]:
        print_route_hint(catering_response["data"][0], start_node_id="gate_north")

    print("[4] 日记查询：标题 / 目的地排序展示")
    diary_by_title = search_diaries(keyword="黄山", sort_field="heat", limit=3)
    print_response(diary_by_title)
    if diary_by_title["data"]:
        print_route_hint(diary_by_title["data"][0], start_node_id="gate_north")

    diary_by_destination = search_diaries(destination="北京大学", sort_field="rating", limit=3)
    print_response(diary_by_destination)
    diary_results = diary_by_destination.get("results", diary_by_destination.get("data", []))
    if diary_results:
        print_route_hint(diary_results[0], start_node_id="gate_north")


def run_week10_demo() -> None:
    """第十周统一演示入口。"""
    print("成员 B 第十周业务演示")
    print("=" * 72)

    print("[1] 日记全文检索：图书馆 自习")
    fulltext_response = search_diaries_fulltext(query="图书馆 自习", limit=3)
    print_response(fulltext_response)
    fulltext_results = fulltext_response.get("results", fulltext_response.get("data", []))
    if fulltext_results:
        print_route_hint(fulltext_results[0], start_node_id="gate_north")

    print("[2] 日记全文检索：食堂 美食")
    catering_diary_response = search_diaries_fulltext(query="食堂 美食", limit=3)
    print_response(catering_diary_response)
    catering_diary_results = catering_diary_response.get("results", catering_diary_response.get("data", []))
    if catering_diary_results:
        print_route_hint(catering_diary_results[0], start_node_id="gate_north")

    print("[3] 场所查询主链路回归：洗手间按真实距离排序")
    place_response = search_places(
        keyword="厕所",
        category="restroom",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=3,
    )
    print_response(place_response)

    print("[4] 美食推荐主链路回归：食堂 / 餐饮")
    catering_response = recommend_catering(
        keyword="餐厅",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=3,
    )
    print_response(catering_response)

    print("[5] 压缩演示：图书馆日记正文")
    diary_records = load_diary_records()
    target_diary = next(
        (
            record
            for record in diary_records
            if str(record.get("id", "")).strip() == "diary_003"
        ),
        diary_records[0] if diary_records else {"content": ""},
    )
    print_compression_demo(
        str(target_diary.get("content", "")),
        label="《图书馆自习攻略》正文压缩摘要",
    )


def main() -> None:
    if "--week9" in sys.argv:
        run_week9_demo()
        return
    if "--week10" in sys.argv:
        run_week10_demo()
        return

    print("成员 B 第八/九周：查询 -> 推荐 -> 距离 -> 统一 Response CLI 演示")
    print("提示：当前默认使用标准分层数据 data/sites/PKU/*.json。")
    print("起点节点示例：gate_north、library、lib_entrance。")
    print("如需直接查看第九周预设演示，请执行：python -B src/search/cli_demo.py --week9")
    print("如需直接查看第十周预设演示，请执行：python -B src/search/cli_demo.py --week10")
    keyword = input("请输入关键字：").strip()
    category = input("请输入类别（可留空）：").strip()
    start_node_id = input("请输入起点节点 ID（可留空，例如 gate_north）：").strip()
    sort_field = _parse_sort_field(input("排序字段 heat/rating/distance_m（默认 heat）："))
    limit = _parse_limit(input("返回数量（默认 10）："), default=10)
    prefer_member_c_data = _parse_yes_no(
        input("是否改用旧参考景点数据 data/成员Cdata/scenic_spots.json？y/N（默认 N）："),
        default=False,
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
