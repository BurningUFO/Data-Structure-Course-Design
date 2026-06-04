"""
成员 B / C：第九周日记基础查询服务

本模块提供：
1. 标题精确 / 模糊查询
2. 目的地精确 / 模糊查询
3. 按热度 / 评分等字段排序
4. 统一 Response 风格输出
5. 创建、编辑、删除、评分的内存态管理接口
6. 对历史 `data/成员Cdata/diary_test.json` 的最小兼容
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
from collections.abc import Callable
from typing import Any

from src.diary.fulltext_service import search_diary_fulltext_records
from src.recommend.interest import (
    interest_ranking_weights,
    is_interest_sort_field,
    normalize_interest_list,
    rank_interest_aware_records,
)
from src.search.response import build_error_response, build_success_response


Record = dict[str, Any]
_DIARY_DATA_LOCKS_GUARD = threading.Lock()
_DIARY_DATA_LOCKS: dict[Path, Any] = {}


def get_diary_data_lock(data_path: str | Path) -> Any:
    lock_key = Path(data_path).expanduser().resolve()
    with _DIARY_DATA_LOCKS_GUARD:
        lock = _DIARY_DATA_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.RLock()
            _DIARY_DATA_LOCKS[lock_key] = lock
        return lock


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
        "videos": normalize_string_list(record.get("videos")),
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
        self._records_injected = records is not None
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
        self._records_injected = False
        self.data_path = resolve_diary_data_path(
            data_path,
            prefer_legacy_data=prefer_legacy_data,
        )
        self.records = load_diary_records(self.data_path)

    def create_diary(self, payload: Record | None = None) -> dict[str, Any]:
        """创建日记记录。"""
        request = payload or {}

        created_record: Record | None = None

        def build_update(current_records: list[Record]) -> tuple[list[Record] | None, Callable[[], dict[str, Any]]]:
            nonlocal created_record
            title = str(request.get("title", "")).strip()
            if not title:
                return None, lambda: build_error_response(
                    "diary title cannot be empty",
                    query_type="diary_create",
                    metadata=self._management_metadata("create"),
                )

            rating_default = 0.0 if "rating" not in request else None
            normalized_rating = self._normalize_rating(request.get("rating"), default=rating_default)
            if normalized_rating is None:
                return None, lambda: build_error_response(
                    "diary rating must be a number between 0 and 5",
                    query_type="diary_create",
                    metadata=self._management_metadata("create"),
                )

            record = normalize_diary_record(
                {
                    "id": str(request.get("id", "")).strip() or self._next_diary_id_from(current_records),
                    "title": title,
                    "content": str(request.get("content", "")).strip(),
                    "author_id": str(request.get("author_id", "")).strip() or "user_demo",
                    "author_name": str(request.get("author_name", "")).strip() or "演示用户",
                    "destination": str(request.get("destination", "")).strip(),
                    "destination_node_id": request.get("destination_node_id"),
                    "heat": coerce_int(request.get("heat"), default=0),
                    "rating": normalized_rating,
                    "tags": normalize_string_list(request.get("tags")),
                    "views": coerce_int(request.get("views"), default=0),
                    "created_at": str(request.get("created_at", "")).strip() or "2026-05-11",
                    "images": normalize_string_list(request.get("images")),
                    "videos": normalize_string_list(request.get("videos")),
                },
                len(current_records),
            )

            if self._find_record_index_in(current_records, record["id"]) >= 0:
                return None, lambda: build_error_response(
                    f"diary id already exists: {record['id']}",
                    query_type="diary_create",
                    filters={"id": record["id"]},
                    metadata=self._management_metadata("create"),
                )

            updated_records = [item.copy() for item in current_records]
            updated_records.append(record)
            created_record = record

            return updated_records, lambda: build_success_response(
                data=[record],
                message="diary created",
                query_type="diary_create",
                filters={"id": record["id"]},
                metadata=self._management_metadata(
                    "create",
                    persistence_succeeded=True,
                ),
            )

        def build_persistence_error(persist_error: str) -> dict[str, Any]:
            record_id = str((created_record or {}).get("id", "")).strip()
            return build_error_response(
                persist_error,
                query_type="diary_create",
                filters={"id": record_id},
                metadata=self._management_metadata(
                    "create",
                    persist_error=persist_error,
                ),
            )

        return self._apply_records_update(build_update, build_persistence_error)

    def update_diary(self, diary_id: str, updates: Record | None = None) -> dict[str, Any]:
        """编辑日记记录。仅允许更新业务展示字段。"""
        normalized_id = str(diary_id or "").strip()
        request = updates or {}

        def build_update(current_records: list[Record]) -> tuple[list[Record] | None, Callable[[], dict[str, Any]]]:
            index = self._find_record_index_in(current_records, normalized_id)
            if index < 0:
                return None, lambda: build_error_response(
                    f"diary not found: {normalized_id}",
                    query_type="diary_update",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("update"),
                )

            if "title" in request and not str(request.get("title", "")).strip():
                return None, lambda: build_error_response(
                    "diary title cannot be empty",
                    query_type="diary_update",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("update"),
                )

            current = current_records[index].copy()
            allowed_fields = {
                "title",
                "content",
                "author_id",
                "author_name",
                "destination",
                "destination_node_id",
                "heat",
                "rating",
                "tags",
                "views",
                "created_at",
                "images",
                "videos",
            }
            for field_name in allowed_fields:
                if field_name in request:
                    current[field_name] = request[field_name]

            if "rating" in request:
                normalized_rating = self._normalize_rating(request.get("rating"), default=None)
                if normalized_rating is None:
                    return None, lambda: build_error_response(
                        "diary rating must be a number between 0 and 5",
                        query_type="diary_update",
                        filters={"id": normalized_id},
                        metadata=self._management_metadata("update"),
                    )
                current["rating"] = normalized_rating

            normalized = normalize_diary_record(current, index)
            if not str(normalized["title"]).strip():
                return None, lambda: build_error_response(
                    "diary title cannot be empty",
                    query_type="diary_update",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("update"),
                )

            updated_records = [item.copy() for item in current_records]
            updated_records[index] = normalized
            return updated_records, lambda: build_success_response(
                data=[normalized],
                message="diary updated",
                query_type="diary_update",
                filters={"id": normalized_id},
                metadata=self._management_metadata(
                    "update",
                    persistence_succeeded=True,
                ),
            )

        def build_persistence_error(persist_error: str) -> dict[str, Any]:
            return build_error_response(
                persist_error,
                query_type="diary_update",
                filters={"id": normalized_id},
                metadata=self._management_metadata(
                    "update",
                    persist_error=persist_error,
                ),
            )

        return self._apply_records_update(build_update, build_persistence_error)

    def delete_diary(self, diary_id: str) -> dict[str, Any]:
        """删除日记记录。"""
        normalized_id = str(diary_id or "").strip()

        def build_update(current_records: list[Record]) -> tuple[list[Record] | None, Callable[[], dict[str, Any]]]:
            index = self._find_record_index_in(current_records, normalized_id)
            if index < 0:
                return None, lambda: build_error_response(
                    f"diary not found: {normalized_id}",
                    query_type="diary_delete",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("delete"),
                )

            deleted = current_records[index].copy()
            updated_records = [item.copy() for item in current_records]
            del updated_records[index]
            return updated_records, lambda: build_success_response(
                data=[deleted],
                message="diary deleted",
                query_type="diary_delete",
                filters={"id": normalized_id},
                metadata=self._management_metadata(
                    "delete",
                    persistence_succeeded=True,
                ),
            )

        def build_persistence_error(persist_error: str) -> dict[str, Any]:
            return build_error_response(
                persist_error,
                query_type="diary_delete",
                filters={"id": normalized_id},
                metadata=self._management_metadata(
                    "delete",
                    persist_error=persist_error,
                ),
            )

        return self._apply_records_update(build_update, build_persistence_error)

    def rate_diary(self, diary_id: str, rating: Any) -> dict[str, Any]:
        """更新日记评分。评分范围统一限制在 0 到 5。"""
        normalized_id = str(diary_id or "").strip()

        normalized_rating: float | None = None

        def build_update(current_records: list[Record]) -> tuple[list[Record] | None, Callable[[], dict[str, Any]]]:
            nonlocal normalized_rating
            index = self._find_record_index_in(current_records, normalized_id)
            if index < 0:
                return None, lambda: build_error_response(
                    f"diary not found: {normalized_id}",
                    query_type="diary_rate",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("rate"),
                )

            normalized_rating = self._normalize_rating(rating, default=None)
            if normalized_rating is None:
                return None, lambda: build_error_response(
                    "diary rating must be a number between 0 and 5",
                    query_type="diary_rate",
                    filters={"id": normalized_id},
                    metadata=self._management_metadata("rate"),
                )

            updated_record = current_records[index].copy()
            updated_record["rating"] = normalized_rating
            updated_record = normalize_diary_record(updated_record, index)
            updated_records = [item.copy() for item in current_records]
            updated_records[index] = updated_record
            return updated_records, lambda: build_success_response(
                data=[updated_record],
                message="diary rated",
                query_type="diary_rate",
                filters={"id": normalized_id, "rating": normalized_rating},
                metadata=self._management_metadata(
                    "rate",
                    persistence_succeeded=True,
                ),
            )

        def build_persistence_error(persist_error: str) -> dict[str, Any]:
            return build_error_response(
                persist_error,
                query_type="diary_rate",
                filters={"id": normalized_id, "rating": normalized_rating},
                metadata=self._management_metadata(
                    "rate",
                    persist_error=persist_error,
                ),
            )

        return self._apply_records_update(build_update, build_persistence_error)

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
        interests: list[str] | str | None = None,
    ) -> dict[str, Any]:
        """日记统一查询入口。"""
        normalized_interests = normalize_interest_list(interests)
        interest_ranking_active = bool(normalized_interests) and is_interest_sort_field(sort_field)
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

        safe_limit = limit if limit > 0 else 10
        if interest_ranking_active:
            ordered_records = rank_interest_aware_records(
                matched_records,
                interests=normalized_interests,
                include_distance=False,
                limit=max(safe_limit, len(matched_records)),
            )
        else:
            ordered_records = self._sort_records(
                matched_records,
                sort_field=sort_field,
                sort_order=sort_order,
            )
        top_records = ordered_records[:safe_limit]

        result_fields = [
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
        ]
        if normalized_interests:
            result_fields.extend(
                [
                    "interest_match_score",
                    "recommendation_score",
                    "interest_reason",
                ]
            )

        metadata = {
            "total_matched": len(matched_records),
            "ranking": {
                "sort_field": sort_field if sort_field else "heat",
                "sort_order": self._resolve_sort_order(sort_field, sort_order),
                "limit": safe_limit,
                "distance_used_for_ranking": False,
                "interest_used_for_ranking": interest_ranking_active,
            },
            "interest": {
                "requested": bool(normalized_interests),
                "active_for_ranking": interest_ranking_active,
                "interests": normalized_interests,
                "score_field": "interest_match_score",
                "recommendation_score_field": "recommendation_score",
                "weights": interest_ranking_weights(include_distance=False),
            },
            "data_source": {
                "path": str(self.data_path),
                "legacy_compatible": self.data_path == get_legacy_diary_data_path(),
            },
            "result_fields": result_fields,
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
                "interests": normalized_interests,
            },
            metadata=metadata,
        )

    def search_fulltext(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> dict[str, Any]:
        """第十周新增：按日记正文做全文检索业务封装。"""
        safe_limit = limit if limit > 0 else 10
        filters = {
            "query": query,
            "limit": safe_limit,
        }
        metadata = {
            "ranking": {
                "sort_field": "score",
                "sort_order": "desc",
                "limit": safe_limit,
                "distance_used_for_ranking": False,
            },
            "data_source": {
                "path": str(self.data_path),
                "legacy_compatible": self.data_path == get_legacy_diary_data_path(),
            },
            "result_fields": [
                "id",
                "diary_id",
                "title",
                "destination",
                "destination_node_id",
                "matched_terms",
                "score",
                "snippet",
                "heat",
                "rating",
            ],
        }

        if not normalize_text(query):
            metadata["fulltext"] = {
                "backend": "fallback_contains",
                "query_tokens": [],
                "multi_keyword_mode": "or_ranked",
                "supports_phrase_query": False,
                "route_hint_available_count": 0,
            }
            return build_error_response(
                "fulltext query cannot be empty",
                query_type="diary_fulltext_search",
                filters=filters,
                metadata=metadata,
            )

        fulltext_result = search_diary_fulltext_records(
            self.records,
            query=query,
            limit=safe_limit,
        )
        metadata["total_matched"] = fulltext_result["total_matched"]
        metadata["fulltext"] = {
            "backend": fulltext_result["backend"],
            "backend_mode": fulltext_result["backend_mode"],
            "backend_error": fulltext_result["backend_error"],
            "query_tokens": fulltext_result["query_tokens"],
            "multi_keyword_mode": "or_ranked",
            "supports_phrase_query": False,
            "route_hint_available_count": fulltext_result["route_hint_available_count"],
            "index_manifest": fulltext_result["payload_metadata"].get("index_manifest"),
        }

        results = fulltext_result["results"]
        return build_success_response(
            data=results,
            message="diary fulltext search success" if results else "no matched diary contents",
            query_type="diary_fulltext_search",
            filters=filters,
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

    def _find_record_index(self, diary_id: str) -> int:
        return self._find_record_index_in(self.records, diary_id)

    @staticmethod
    def _find_record_index_in(records: list[Record], diary_id: str) -> int:
        for index, record in enumerate(records):
            if str(record.get("id", "")).strip() == diary_id:
                return index
        return -1

    def _next_diary_id(self) -> str:
        return self._next_diary_id_from(self.records)

    @staticmethod
    def _next_diary_id_from(records: list[Record]) -> str:
        max_number = 0
        for record in records:
            record_id = str(record.get("id", "")).strip()
            if not record_id.startswith("diary_"):
                continue
            suffix = record_id.removeprefix("diary_")
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
        return f"diary_{max_number + 1:03d}"

    def _management_metadata(
        self,
        operation: str,
        *,
        persist_error: str | None = None,
        persistence_succeeded: bool = False,
    ) -> dict[str, Any]:
        storage_mode = "file_backed" if self._should_write_back() else "memory_only"
        metadata = {
            "operation": operation,
            "storage_mode": storage_mode,
            "record_count": len(self.records),
            "data_source": {
                "path": str(self.data_path),
                "write_back": self._should_write_back(),
                "legacy_compatible": self.data_path == get_legacy_diary_data_path(),
            },
            "result_fields": [
                "id",
                "title",
                "content",
                "destination",
                "destination_node_id",
                "heat",
                "rating",
                "author_name",
                "tags",
                "views",
                "created_at",
                "images",
                "videos",
            ],
        }
        if persist_error is not None:
            metadata["persistence"] = {
                "attempted": self._should_write_back(),
                "succeeded": False,
                "error": persist_error,
            }
        elif self._should_write_back() and persistence_succeeded:
            metadata["persistence"] = {
                "attempted": True,
                "succeeded": True,
            }
        return metadata

    def _should_write_back(self) -> bool:
        return not self._records_injected

    def _apply_records_update(
        self,
        build_update: Callable[[list[Record]], tuple[list[Record] | None, Callable[[], dict[str, Any]]]],
        build_persistence_error: Callable[[str], dict[str, Any]],
    ) -> dict[str, Any]:
        if self._should_write_back():
            with get_diary_data_lock(self.data_path):
                try:
                    current_records = load_diary_records(self.data_path)
                except OSError as error:
                    return build_persistence_error(f"failed to load diary data: {error}")
                updated_records, build_response = build_update(current_records)
                if updated_records is None:
                    return build_response()
                persist_error = self._commit_records_update(updated_records)
                if persist_error is not None:
                    return build_persistence_error(persist_error)
                return build_response()

        current_records = [item.copy() for item in self.records]
        updated_records, build_response = build_update(current_records)
        if updated_records is not None:
            self.records = updated_records
        return build_response()

    def _commit_records_update(self, updated_records: list[Record]) -> str | None:
        if self._should_write_back():
            try:
                self._persist_records(updated_records)
            except OSError as error:
                return f"failed to persist diary data: {error}"
        self.records = updated_records
        return None

    def _persist_records(self, records: list[Record]) -> None:
        target_path = self.data_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        serialized_records = self._serialize_records(records)
        payload = json.dumps(
            serialized_records,
            ensure_ascii=False,
            indent=2,
        ) + "\n"

        file_descriptor: int | None = None
        temp_path: str | None = None
        try:
            file_descriptor, temp_path = tempfile.mkstemp(
                prefix=f"{target_path.stem}.",
                suffix=".tmp",
                dir=str(target_path.parent),
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                file_descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target_path)
        except OSError:
            raise
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _serialize_records(self, records: list[Record]) -> list[Record]:
        return [self._serialize_record(record) for record in records]

    def _serialize_record(self, record: Record) -> Record:
        serialized: Record = {
            "id": str(record.get("id", "")).strip(),
            "title": str(record.get("title", "")).strip(),
            "content": str(record.get("content", "")).strip(),
            "author_id": str(record.get("author_id", "")).strip(),
            "author_name": str(record.get("author_name", "")).strip(),
            "destination": str(record.get("destination", "")).strip(),
            "destination_node_id": record.get("destination_node_id"),
            "heat": coerce_int(record.get("heat"), default=0),
            "rating": self._normalize_rating(record.get("rating"), default=0.0),
            "tags": normalize_string_list(record.get("tags")),
            "views": coerce_int(record.get("views"), default=0),
            "created_at": str(record.get("created_at", "")).strip(),
            "images": normalize_string_list(record.get("images")),
        }

        videos = normalize_string_list(record.get("videos"))
        if videos:
            serialized["videos"] = videos
        return serialized

    @staticmethod
    def _normalize_rating(value: Any, default: float | None = 0.0) -> float | None:
        try:
            rating = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(5.0, rating))


def search_diaries(
    *,
    keyword: str = "",
    destination: str = "",
    match_mode: str = "fuzzy",
    sort_field: str = "heat",
    sort_order: str = "",
    limit: int = 10,
    interests: list[str] | str | None = None,
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
        interests=interests,
    )


def search_diaries_fulltext(
    *,
    query: str,
    limit: int = 10,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记全文检索快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.search_fulltext(
        query,
        limit=limit,
    )


def create_diary(
    payload: Record | None = None,
    *,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记创建快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.create_diary(payload)


def update_diary(
    diary_id: str,
    updates: Record | None = None,
    *,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记编辑快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.update_diary(diary_id, updates)


def delete_diary(
    diary_id: str,
    *,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记删除快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.delete_diary(diary_id)


def rate_diary(
    diary_id: str,
    rating: Any,
    *,
    records: list[Record] | None = None,
    data_path: str | Path | None = None,
    prefer_legacy_data: bool = False,
) -> dict[str, Any]:
    """日记评分快速调用入口。"""
    service = DiaryService(
        records,
        data_path=data_path,
        prefer_legacy_data=prefer_legacy_data,
    )
    return service.rate_diary(diary_id, rating)
