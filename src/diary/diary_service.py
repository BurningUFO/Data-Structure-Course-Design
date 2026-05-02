"""
成员 B / C：第九周日记基础查询服务

本模块提供：
1. 标题精确 / 模糊查询
2. 目的地精确 / 模糊查询
3. 按热度 / 评分等字段排序
4. 统一 Response 风格输出
5. 对历史 `data/成员Cdata/diary_test.json` 的最小兼容
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.search.response import build_success_response


Record = dict[str, Any]


def get_default_diary_data_path() -> Path:
    """返回标准日记数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "diary_data.json"


def get_legacy_diary_data_path() -> Path:
    """返回历史兼容日记数据路径。"""
    return Path(__file__).resolve().parents[2] / "data" / "成员Cdata" / "diary_test.json"


def resolve_diary_data_path(
    data_path: str | Path | None = None,
    *,
    prefer_legacy_data: bool = False,
) -> Path:
    """解析本次查询应读取的日记数据路径。"""
    if data_path is not None:
        return Path(data_path)

    default_path = get_default_diary_data_path()
    legacy_path = get_legacy_diary_data_path()

    if prefer_legacy_data and legacy_path.exists():
        return legacy_path
    if default_path.exists():
        return default_path
    return legacy_path


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def extract_json_list(raw_text: str) -> list[Record]:
    """兼容纯 JSON 和 Markdown 代码块包裹的 JSON 数组。"""
    stripped = raw_text.lstrip("\ufeff").strip()
    if not stripped:
        return []

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        list_start = stripped.find("[")
        if list_start < 0:
            return []

        decoder = json.JSONDecoder()
        try:
            data, _ = decoder.raw_decode(stripped[list_start:])
        except json.JSONDecodeError:
            return []

    return data if isinstance(data, list) else []


def normalize_diary_record(record: Record, index: int) -> Record:
    """将不同来源的日记记录归一化到统一字段集合。"""
    raw_id = str(record.get("id", "")).strip()
    title = str(record.get("title", "")).strip()
    destination_node_id = record.get("destination_node_id")
    if destination_node_id is not None:
        destination_node_id = str(destination_node_id).strip() or None

    return {
        "id": raw_id or f"diary_auto_{index + 1:03d}",
        "title": title or f"未命名日记{index + 1}",
        "content": str(record.get("content", "")).strip(),
        "author_id": str(record.get("author_id", "")).strip(),
        "author_name": str(
            record.get("author_name")
            or record.get("author_id")
            or ""
        ).strip(),
        "destination": str(record.get("destination", "")).strip(),
        "destination_node_id": destination_node_id,
        "heat": coerce_int(record.get("heat"), default=0),
        "rating": coerce_float(record.get("rating"), default=0.0),
        "tags": normalize_string_list(record.get("tags")),
        "views": coerce_int(record.get("views"), default=0),
        "created_at": str(record.get("created_at", "")).strip(),
        "images": normalize_string_list(record.get("images")),
    }


def load_diary_records(
    data_path: str | Path | None = None,
    *,
    prefer_legacy_data: bool = False,
) -> list[Record]:
    """加载并归一化日记记录列表。"""
    target_path = resolve_diary_data_path(
        data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    if not target_path.exists():
        return []

    raw_text = target_path.read_text(encoding="utf-8")
    raw_records = extract_json_list(raw_text)
    return [
        normalize_diary_record(record, index)
        for index, record in enumerate(raw_records)
        if isinstance(record, dict)
    ]


class DiaryService:
    """日记业务服务类。"""

    def __init__(
        self,
        records: list[Record] | None = None,
        *,
        data_path: str | Path | None = None,
        prefer_legacy_data: bool = False,
    ) -> None:
        self.data_path = resolve_diary_data_path(
            data_path,
            prefer_legacy_data=prefer_legacy_data,
        )
        self.records = (
            [normalize_diary_record(record, index) for index, record in enumerate(records)]
            if records is not None
            else load_diary_records(self.data_path)
        )

    def reload(
        self,
        data_path: str | Path | None = None,
        *,
        prefer_legacy_data: bool = False,
    ) -> None:
        """重新加载日记数据。"""
        self.data_path = resolve_diary_data_path(
            data_path,
            prefer_legacy_data=prefer_legacy_data,
        )
        self.records = load_diary_records(self.data_path)

    def search_by_title(
        self,
        title: str,
        *,
        match_mode: str = "exact",
    ) -> list[Record]:
        """按日记标题查询。"""
        normalized_title = normalize_text(title)
        if not normalized_title:
            return []

        if match_mode == "exact":
            return [
                record
                for record in self.records
                if normalize_text(record.get("title")) == normalized_title
            ]

        return [
            record
            for record in self.records
            if normalized_title in normalize_text(record.get("title"))
        ]

    def search_by_title_exact(self, title: str) -> list[Record]:
        return self.search_by_title(title, match_mode="exact")

    def search_by_destination(
        self,
        destination: str,
        *,
        match_mode: str = "fuzzy",
    ) -> list[Record]:
        """按目的地查询日记。"""
        normalized_destination = normalize_text(destination)
        if not normalized_destination:
            return []

        if match_mode == "exact":
            return [
                record
                for record in self.records
                if normalize_text(record.get("destination")) == normalized_destination
            ]

        return [
            record
            for record in self.records
            if normalized_destination in normalize_text(record.get("destination"))
        ]

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
        """日记统一查询入口。"""
        if not keyword and not destination:
            matched_records = self.records[:]
        else:
            matched_records = self.records[:]
            if destination:
                matched_records = self.search_by_destination(
                    destination,
                    match_mode=match_mode,
                )
            if keyword:
                title_records = self.search_by_title(
                    keyword,
                    match_mode=match_mode,
                )
                matched_ids = {record["id"] for record in title_records}
                matched_records = [
                    record
                    for record in matched_records
                    if record["id"] in matched_ids
                ]

        ordered_records = self._sort_records(
            matched_records,
            sort_field=sort_field,
            sort_order=sort_order,
        )
        safe_limit = limit if limit > 0 else 10
        top_records = ordered_records[:safe_limit]

        metadata = {
            "total_matched": len(matched_records),
            "ranking": {
                "sort_field": sort_field if sort_field else "heat",
                "sort_order": self._resolve_sort_order(sort_field, sort_order),
                "limit": safe_limit,
                "distance_used_for_ranking": False,
            },
            "data_source": {
                "path": str(self.data_path),
                "legacy_compatible": self.data_path == get_legacy_diary_data_path(),
            },
            "result_fields": [
                "id",
                "title",
                "destination",
                "destination_node_id",
                "heat",
                "rating",
                "author_name",
                "tags",
                "views",
                "created_at",
            ],
        }

        return build_success_response(
            data=top_records,
            message="diary query success" if top_records else "no matched diaries",
            query_type="diary_search",
            filters={
                "keyword": keyword,
                "destination": destination,
                "match_mode": match_mode,
                "sort_field": sort_field,
                "sort_order": sort_order,
                "limit": safe_limit,
            },
            metadata=metadata,
        )

    def _sort_records(
        self,
        records: list[Record],
        *,
        sort_field: str = "heat",
        sort_order: str = "",
    ) -> list[Record]:
        order = self._resolve_sort_order(sort_field, sort_order)
        reverse = order == "desc"

        if sort_field == "rating":
            return sorted(records, key=lambda item: float(item.get("rating", 0)), reverse=reverse)
        if sort_field == "views":
            return sorted(records, key=lambda item: int(item.get("views", 0)), reverse=reverse)
        if sort_field == "created_at":
            return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=reverse)
        return sorted(records, key=lambda item: int(item.get("heat", 0)), reverse=reverse)

    @staticmethod
    def _resolve_sort_order(sort_field: str, sort_order: str) -> str:
        normalized_order = sort_order.strip().lower()
        if normalized_order in {"asc", "desc"}:
            return normalized_order
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
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记查询快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.search(
        keyword=keyword,
        destination=destination,
        match_mode=match_mode,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
    )
