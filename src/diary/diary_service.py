"""
成员C：日记基础查询服务

本模块提供日记的基础查询功能：
1. 按标题精确查询
2. 按目的地查询
3. 按热度 / 评分排序
4. 输出风格复用成员B的统一 Response 结构

后续扩展方向（第10-11周）：
- 日记内容全文检索（倒排索引 / Trie）
- 哈夫曼无损压缩 / 解压
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 复用成员B的统一响应结构
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.search.response import build_success_response, build_error_response  # noqa: E402


Record = dict[str, Any]


def get_default_diary_data_path() -> Path:
    """返回日记测试数据文件路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "diary_data.json"


def load_diary_records(data_path: str | Path | None = None) -> list[Record]:
    """加载日记记录列表。"""
    target_path = Path(data_path) if data_path else get_default_diary_data_path()
    if not target_path.exists():
        return []

    with target_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return []
    return data


class DiaryService:
    """
    日记业务服务类。

    提供日记的标题查询、目的地查询和通用搜索入口。
    """

    def __init__(self, records: list[Record] | None = None):
        """
        :param records: 日记记录注入，不传则从默认路径加载
        """
        self.records = records[:] if records is not None else load_diary_records()

    def reload(self, data_path: str | Path | None = None) -> None:
        """重新加载日记数据。"""
        self.records = load_diary_records(data_path)

    # ──────────────────────── 按标题精确查询 ────────────────────────

    def search_by_title(
        self,
        title: str,
        *,
        match_mode: str = "exact",
    ) -> list[Record]:
        """
        按日记标题查询。

        :param title: 查询的标题关键词
        :param match_mode: 匹配模式
            - "exact": 精确匹配
            - "fuzzy": 模糊匹配（包含关键词）
        :return: 匹配的日记记录列表
        """
        if not title:
            return []

        normalized_title = str(title).strip().lower()

        if match_mode == "exact":
            return [
                record
                for record in self.records
                if str(record.get("title", "")).strip().lower() == normalized_title
            ]

        # fuzzy: 标题包含关键词
        return [
            record
            for record in self.records
            if normalized_title in str(record.get("title", "")).strip().lower()
        ]

    def search_by_title_exact(self, title: str) -> list[Record]:
        """按标题精确匹配查询（简写入口）。"""
        return self.search_by_title(title, match_mode="exact")

    # ──────────────────────── 按目的地查询 ────────────────────────

    def search_by_destination(
        self,
        destination: str,
        *,
        match_mode: str = "fuzzy",
    ) -> list[Record]:
        """
        按目的地查询日记。

        :param destination: 目的地名称
        :param match_mode: "exact" 精确匹配 / "fuzzy" 模糊包含
        :return: 匹配的日记记录列表
        """
        if not destination:
            return []

        normalized_dest = str(destination).strip().lower()

        if match_mode == "exact":
            return [
                record
                for record in self.records
                if str(record.get("destination", "")).strip().lower() == normalized_dest
            ]

        return [
            record
            for record in self.records
            if normalized_dest in str(record.get("destination", "")).strip().lower()
        ]

    # ──────────────────────── 通用查询入口 ────────────────────────

    def search(
        self,
        *,
        keyword: str = "",
        destination: str = "",
        match_mode: str = "fuzzy",
        sort_field: str = "heat",
        sort_order: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        通用日记查询入口，统一返回风格与成员B的查询接口保持一致。

        :param keyword: 日记标题关键词（为空时不过滤标题）
        :param destination: 目的地关键词（为空时不过滤目的地）
        :param match_mode: "exact" / "fuzzy"
        :param sort_field: 排序字段（"heat" 热度 / "rating" 评分）
        :param sort_order: 排序方向（"desc" / "asc"）
        :param limit: 返回记录上限
        :return: 统一响应字典
        """
        # 如果没有指定任何查询条件，返回所有日记
        if not keyword and not destination:
            result_records = self.records[:]
        else:
            # 先按目的地过滤，再按标题过滤
            if destination:
                dest_records = self.search_by_destination(destination, match_mode=match_mode)
            else:
                dest_records = self.records[:]

            if keyword:
                title_records = self.search_by_title(keyword, match_mode=match_mode)
                # 取交集：同时匹配目的地和标题
                matched_ids = {r["id"] for r in title_records}
                result_records = [r for r in dest_records if r["id"] in matched_ids]
            else:
                result_records = dest_records

        if not result_records:
            return build_success_response(
                data=[],
                message="no matched diaries",
                query_type="diary_search",
                filters={
                    "keyword": keyword,
                    "destination": destination,
                    "match_mode": match_mode,
                    "sort_field": sort_field,
                    "sort_order": sort_order,
                    "limit": limit,
                },
            )

        sorted_records = self._sort_records(result_records, sort_field, sort_order)
        top_records = sorted_records[:limit]

        metadata = {
            "total_matched": len(result_records),
            "sort_field": sort_field,
            "sort_order": self._resolve_sort_order(sort_field, sort_order),
            "limit": limit,
            "result_fields": [
                "id", "title", "destination", "heat", "rating",
                "author_name", "tags", "views", "created_at",
            ],
        }

        return build_success_response(
            data=top_records,
            message="diary query success",
            query_type="diary_search",
            filters={
                "keyword": keyword,
                "destination": destination,
                "match_mode": match_mode,
                "sort_field": sort_field,
                "sort_order": sort_order,
                "limit": limit,
            },
            metadata=metadata,
        )

    # ──────────────────────── 内部辅助方法 ────────────────────────

    def _sort_records(
        self,
        records: list[Record],
        sort_field: str = "heat",
        sort_order: str = "",
    ) -> list[Record]:
        """按指定字段排序。"""
        order = self._resolve_sort_order(sort_field, sort_order)
        reverse = order == "desc"

        if sort_field == "heat":
            return sorted(records, key=lambda r: int(r.get("heat", 0)), reverse=reverse)
        if sort_field == "rating":
            return sorted(records, key=lambda r: float(r.get("rating", 0)), reverse=reverse)
        if sort_field == "views":
            return sorted(records, key=lambda r: int(r.get("views", 0)), reverse=reverse)
        if sort_field == "created_at":
            return sorted(
                records,
                key=lambda r: str(r.get("created_at", "")),
                reverse=reverse,
            )

        # 默认按热度降序
        return sorted(records, key=lambda r: int(r.get("heat", 0)), reverse=True)

    @staticmethod
    def _resolve_sort_order(sort_field: str, sort_order: str) -> str:
        """解析排序方向。"""
        normalized_order = sort_order.strip().lower()
        if normalized_order in {"asc", "desc"}:
            return normalized_order
        # 热度 / 评分默认降序
        if sort_field in {"heat", "rating", "views", "created_at"}:
            return "desc"
        return "desc"


def search_diaries(
    *,
    keyword: str = "",
    destination: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 10,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    日记查询快速调用入口。

    用法示例：
        result = search_diaries(keyword="黄山")
        result = search_diaries(destination="北京大学", sort_field="rating")
    """
    service = DiaryService(records)
    if data_path:
        service.reload(data_path)

    return service.search(
        keyword=keyword,
        destination=destination,
        match_mode=match_mode,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
    )
