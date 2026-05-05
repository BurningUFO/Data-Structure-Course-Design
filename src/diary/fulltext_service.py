"""
成员 B：第十周日记全文检索业务适配层

优先对接成员 C 后续提供的全文检索实现；在正式倒排索引尚未接入前，
提供一个基于标题 / 正文 / 标签的最小可运行回退方案，确保：

- 业务层可以先统一 Response
- CLI 可以先演示“日记全文检索 -> 路径提示”
- 测试可以先覆盖第十周主链路
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


Record = dict[str, Any]
BackendSearch = Callable[..., Any]

TERM_EQUIVALENT_GROUPS = (
    ("图书馆", "tsg", "library"),
    ("未名湖", "wml"),
    ("北京大学", "北大", "pku", "bjd"),
    ("洗手间", "卫生间", "厕所", "wc", "restroom", "xsj"),
    ("食堂", "餐厅", "餐饮", "catering", "st"),
    ("便利店", "超市", "商店", "shopping", "bld"),
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


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(str(value).strip())
    return result


def split_query_tokens(query: str) -> list[str]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    raw_tokens = [part for part in normalized_query.split() if part]
    if not raw_tokens:
        raw_tokens = [normalized_query]

    return unique_strings(raw_tokens)


def expand_query_token(token: str) -> list[str]:
    normalized_token = normalize_text(token)
    if not normalized_token:
        return []
    return unique_strings([normalized_token, *TERM_ALIASES.get(normalized_token, [])])


def count_occurrences(text: Any, term: str) -> int:
    normalized_text = normalize_text(text)
    normalized_term = normalize_text(term)
    if not normalized_text or not normalized_term:
        return 0
    return normalized_text.count(normalized_term)


def build_snippet(content: str, matched_terms: list[str], *, radius: int = 18) -> str:
    stripped_content = str(content).strip()
    if not stripped_content:
        return ""

    normalized_content = normalize_text(stripped_content)
    best_index = -1
    best_term = ""

    for term in matched_terms:
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        index = normalized_content.find(normalized_term)
        if index >= 0 and (best_index < 0 or index < best_index):
            best_index = index
            best_term = normalized_term

    if best_index < 0:
        snippet = stripped_content[: max(radius * 2, 40)]
        if len(stripped_content) > len(snippet):
            return f"{snippet}..."
        return snippet

    start = max(best_index - radius, 0)
    end = min(best_index + len(best_term) + radius, len(stripped_content))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(stripped_content) else ""
    snippet = stripped_content[start:end].strip()
    return f"{prefix}{snippet}{suffix}"


def resolve_backend_search() -> tuple[BackendSearch | None, str]:
    try:
        module = importlib.import_module("src.compress.fulltext")
    except ModuleNotFoundError:
        return None, "fallback_contains"

    for function_name in ("search_diary_fulltext", "search_fulltext", "search_diaries_fulltext"):
        candidate = getattr(module, function_name, None)
        if callable(candidate):
            return candidate, f"src.compress.fulltext.{function_name}"

    return None, "fallback_contains"


def call_backend_search(
    backend_search: BackendSearch,
    records: list[Record],
    query: str,
    limit: int,
) -> Any:
    call_patterns = (
        lambda: backend_search(query=query, records=records, limit=limit),
        lambda: backend_search(records=records, query=query, limit=limit),
        lambda: backend_search(query, records, limit),
        lambda: backend_search(query=query, limit=limit),
        lambda: backend_search(query, limit),
        lambda: backend_search(query),
    )

    last_error: TypeError | None = None
    for pattern in call_patterns:
        try:
            return pattern()
        except TypeError as error:
            last_error = error

    if last_error is not None:
        raise last_error
    return []


def normalize_backend_result(raw_result: Record, records_by_id: dict[str, Record]) -> Record | None:
    raw_id = str(raw_result.get("diary_id") or raw_result.get("id") or "").strip()
    if not raw_id:
        return None

    source_record = records_by_id.get(raw_id, {})
    matched_terms = unique_strings(
        [str(term).strip() for term in raw_result.get("matched_terms", []) if str(term).strip()]
    )
    title = str(raw_result.get("title") or source_record.get("title") or "").strip()
    content = str(source_record.get("content", "")).strip()
    destination_node_id = raw_result.get("destination_node_id", source_record.get("destination_node_id"))
    if destination_node_id is not None:
        destination_node_id = str(destination_node_id).strip() or None

    try:
        score = float(raw_result.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0

    return {
        "id": raw_id,
        "diary_id": raw_id,
        "title": title or raw_id,
        "destination": str(raw_result.get("destination") or source_record.get("destination") or "").strip(),
        "destination_node_id": destination_node_id,
        "matched_terms": matched_terms,
        "score": round(score, 2),
        "snippet": str(raw_result.get("snippet") or build_snippet(content, matched_terms)),
        "heat": int(source_record.get("heat", 0)),
        "rating": float(source_record.get("rating", 0.0)),
        "author_name": str(source_record.get("author_name", "")).strip(),
        "tags": list(source_record.get("tags", [])),
        "created_at": str(source_record.get("created_at", "")).strip(),
    }


def normalize_backend_payload(
    payload: Any,
    records_by_id: dict[str, Record],
) -> tuple[list[Record], int, dict[str, Any]]:
    payload_metadata: dict[str, Any] = {}
    if isinstance(payload, dict):
        raw_items = payload.get("results") or payload.get("data") or payload.get("items") or []
        total_matched = int(payload.get("total", len(raw_items)))
        query_terms = payload.get("query_terms")
        if isinstance(query_terms, list):
            payload_metadata["query_terms"] = unique_strings(
                [str(term).strip() for term in query_terms if str(term).strip()]
            )
        index_manifest = payload.get("index_manifest")
        if isinstance(index_manifest, dict):
            payload_metadata["index_manifest"] = index_manifest
        if "offline_ready" in payload:
            payload_metadata["offline_ready"] = bool(payload.get("offline_ready"))
        storage_mode = payload.get("storage_mode")
        if storage_mode is not None:
            payload_metadata["storage_mode"] = str(storage_mode)
    elif isinstance(payload, list):
        raw_items = payload
        total_matched = len(raw_items)
    else:
        raw_items = []
        total_matched = 0

    normalized_results: list[Record] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized = normalize_backend_result(item, records_by_id)
        if normalized is not None:
            normalized_results.append(normalized)

    return normalized_results, total_matched, payload_metadata


def build_fallback_result(record: Record, query_tokens: list[str]) -> Record | None:
    title = str(record.get("title", "")).strip()
    content = str(record.get("content", "")).strip()
    tags = [str(tag).strip() for tag in record.get("tags", []) if str(tag).strip()]

    matched_terms: list[str] = []
    score = 0.0

    for token in query_tokens:
        best_term = ""
        best_score = 0

        for candidate in expand_query_token(token):
            title_hits = count_occurrences(title, candidate)
            content_hits = count_occurrences(content, candidate)
            tag_hits = sum(count_occurrences(tag, candidate) for tag in tags)
            candidate_score = title_hits * 12 + content_hits * 8 + tag_hits * 6

            if candidate_score > best_score:
                best_score = candidate_score
                best_term = candidate

        if best_score <= 0:
            continue

        matched_terms.append(best_term or token)
        score += best_score

    if not matched_terms:
        return None

    unique_matched_terms = unique_strings(matched_terms)
    if len(query_tokens) > 1 and len(unique_matched_terms) >= len(query_tokens):
        score += 18
    score += len(unique_matched_terms) * 4
    score += int(record.get("heat", 0)) * 0.05
    score += float(record.get("rating", 0.0)) * 2

    destination_node_id = record.get("destination_node_id")
    if destination_node_id is not None:
        destination_node_id = str(destination_node_id).strip() or None

    return {
        "id": str(record.get("id", "")).strip(),
        "diary_id": str(record.get("id", "")).strip(),
        "title": title,
        "destination": str(record.get("destination", "")).strip(),
        "destination_node_id": destination_node_id,
        "matched_terms": unique_matched_terms,
        "score": round(score, 2),
        "snippet": build_snippet(content, unique_matched_terms),
        "heat": int(record.get("heat", 0)),
        "rating": float(record.get("rating", 0.0)),
        "author_name": str(record.get("author_name", "")).strip(),
        "tags": list(record.get("tags", [])),
        "created_at": str(record.get("created_at", "")).strip(),
    }


def fallback_search(records: list[Record], query: str, limit: int) -> tuple[list[Record], int]:
    query_tokens = split_query_tokens(query)
    if not query_tokens:
        return [], 0

    matched_results: list[Record] = []
    for record in records:
        matched_result = build_fallback_result(record, query_tokens)
        if matched_result is not None:
            matched_results.append(matched_result)

    matched_results.sort(
        key=lambda item: (
            -float(item.get("score", 0.0)),
            -int(item.get("heat", 0)),
            -float(item.get("rating", 0.0)),
            str(item.get("created_at", "")),
            str(item.get("title", "")),
        )
    )
    return matched_results[:limit], len(matched_results)


def search_diary_fulltext_records(
    records: list[Record],
    *,
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    safe_limit = limit if limit > 0 else 10
    query_tokens = split_query_tokens(query)
    records_by_id = {
        str(record.get("id", "")).strip(): record
        for record in records
        if str(record.get("id", "")).strip()
    }

    backend_search, backend_name = resolve_backend_search()
    backend_mode = "fallback_missing_backend"
    backend_error = ""
    payload_metadata: dict[str, Any] = {}
    if backend_search is not None:
        backend_mode = "primary"
        try:
            payload = call_backend_search(backend_search, records, query, safe_limit)
            normalized_results, total_matched, payload_metadata = normalize_backend_payload(
                payload,
                records_by_id,
            )
        except Exception as error:
            normalized_results, total_matched = fallback_search(records, query, safe_limit)
            backend_name = "fallback_contains"
            backend_mode = "fallback_after_backend_error"
            backend_error = f"{type(error).__name__}: {error}"
    else:
        normalized_results, total_matched = fallback_search(records, query, safe_limit)

    route_hint_available_count = sum(
        1 for item in normalized_results if item.get("destination_node_id")
    )
    effective_query_terms = payload_metadata.get("query_terms", query_tokens)
    return {
        "results": normalized_results,
        "total_matched": total_matched,
        "query_tokens": effective_query_terms,
        "backend": backend_name,
        "backend_mode": backend_mode,
        "backend_error": backend_error,
        "payload_metadata": payload_metadata,
        "route_hint_available_count": route_hint_available_count,
    }
