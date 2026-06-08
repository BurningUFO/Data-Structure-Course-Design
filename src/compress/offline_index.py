"""
成员 C：第十周离线索引预留接口

本周先提供内存级草稿：
1. 对日记正文执行哈夫曼压缩，保留解压能力
2. 同时构建全文检索倒排索引
3. 为第11周的持久化缓存格式预留统一入口

当前版本不负责把离线包写入磁盘，只提供可演示、可测试的运行时结构。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.compress.fulltext import DiaryFullTextIndex
from src.compress.huffman import compress_text, decompress_text


Record = dict[str, Any]
OFFLINE_PACKAGE_VERSION = "offline-sync-v1"
OFFLINE_SCHEMA_VERSION = "diary-offline-package-v1"
DEFAULT_PRIORITY_RECORD_LIMIT = 50


def stable_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: Any) -> str:
    return hashlib.sha256(stable_json_dumps(value).encode("utf-8")).hexdigest()


def record_sync_payload(record: Record) -> dict[str, Any]:
    return {
        "id": str(record.get("id", "")).strip(),
        "title": str(record.get("title", "")).strip(),
        "content": str(record.get("content", "")),
        "destination": str(record.get("destination", "")).strip(),
        "destination_node_id": record.get("destination_node_id"),
        "tags": record.get("tags", []),
        "heat": record.get("heat", 0),
        "rating": record.get("rating", 0),
        "views": record.get("views", 0),
        "created_at": str(record.get("created_at", "")).strip(),
    }


def build_record_fingerprints(records: list[Record]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for record in records:
        diary_id = str(record.get("id", "")).strip()
        if not diary_id:
            continue
        fingerprints[diary_id] = sha256_text(record_sync_payload(record))
    return dict(sorted(fingerprints.items()))


def select_priority_record_ids(records: list[Record], *, limit: int) -> list[str]:
    def priority_key(record: Record) -> tuple[float, float, int, str, str]:
        try:
            rating = float(record.get("rating", 0.0))
        except (TypeError, ValueError):
            rating = 0.0
        try:
            heat = float(record.get("heat", 0.0))
        except (TypeError, ValueError):
            heat = 0.0
        try:
            views = int(record.get("views", 0))
        except (TypeError, ValueError):
            views = 0
        return (
            -heat,
            -rating,
            -views,
            str(record.get("created_at", "")),
            str(record.get("id", "")),
        )

    prioritized = sorted(
        [record for record in records if str(record.get("id", "")).strip()],
        key=priority_key,
    )
    return [
        str(record.get("id", "")).strip()
        for record in prioritized[: max(0, limit)]
    ]


def estimate_payload_sizes(
    records: list[Record],
    compressed_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    original_size_bytes = sum(
        len(str(record.get("content", "")).encode("utf-8"))
        for record in records
        if str(record.get("id", "")).strip()
    )
    bitstream_size_bytes = sum(
        int(payload.get("bitstream_size_bytes", 0))
        for payload in compressed_payloads.values()
    )
    estimated_package_size_bytes = sum(
        int(payload.get("estimated_package_size_bytes", 0))
        for payload in compressed_payloads.values()
    )
    return {
        "original_content_size_bytes": original_size_bytes,
        "bitstream_size_bytes": bitstream_size_bytes,
        "estimated_package_size_bytes": estimated_package_size_bytes,
        "estimated_compression_ratio": round(
            (estimated_package_size_bytes / original_size_bytes)
            if original_size_bytes
            else 0.0,
            4,
        ),
    }


def build_offline_manifest(
    *,
    records: list[Record],
    index: DiaryFullTextIndex,
    compressed_payloads: dict[str, dict[str, Any]],
    priority_record_ids: list[str],
    package_id: str,
) -> dict[str, Any]:
    record_fingerprints = build_record_fingerprints(records)
    source_watermark = max(
        [str(record.get("created_at", "")).strip() for record in records]
        or [""]
    )
    package_fingerprint = sha256_text(
        {
            "schema_version": OFFLINE_SCHEMA_VERSION,
            "record_fingerprints": record_fingerprints,
            "priority_record_ids": priority_record_ids,
        }
    )
    size_estimates = estimate_payload_sizes(records, compressed_payloads)
    remaining_count = max(0, len(record_fingerprints) - len(priority_record_ids))

    return {
        "package_id": package_id,
        "version": OFFLINE_PACKAGE_VERSION,
        "schema_version": OFFLINE_SCHEMA_VERSION,
        "storage_mode": "in_memory",
        "document_count": len(record_fingerprints),
        "source_watermark": source_watermark,
        "package_fingerprint": package_fingerprint,
        "record_fingerprints": record_fingerprints,
        "priority_record_ids": priority_record_ids,
        "priority_policy": {
            "name": "heat_rating_views_top_k",
            "limit": len(priority_record_ids),
            "description": "records with higher heat, rating and views are synced first",
        },
        "segments": [
            {
                "id": "priority_diaries",
                "priority": "high",
                "record_count": len(priority_record_ids),
                "record_ids": priority_record_ids,
            },
            {
                "id": "remaining_diaries",
                "priority": "normal",
                "record_count": remaining_count,
            },
        ],
        "capabilities": {
            "offline_fulltext": True,
            "huffman_compression": True,
            "incremental_sync_check": True,
            "priority_sync": True,
            "persistent_cache": False,
        },
        "index_manifest": index.manifest(),
        "size_estimates": size_estimates,
    }


def build_offline_diary_index(
    records: list[Record],
    *,
    priority_limit: int = DEFAULT_PRIORITY_RECORD_LIMIT,
    package_id: str = "diary_fulltext_offline",
) -> dict[str, Any]:
    compressed_payloads: dict[str, dict[str, Any]] = {}
    normalized_records: list[Record] = []

    for record in records:
        diary_id = str(record.get("id", "")).strip()
        if not diary_id:
            continue

        normalized_records.append(record)
        compressed_payloads[diary_id] = compress_text(str(record.get("content", "")))

    index = DiaryFullTextIndex(normalized_records)
    priority_record_ids = select_priority_record_ids(
        normalized_records,
        limit=priority_limit,
    )
    manifest = build_offline_manifest(
        records=normalized_records,
        index=index,
        compressed_payloads=compressed_payloads,
        priority_record_ids=priority_record_ids,
        package_id=package_id,
    )
    return {
        "version": OFFLINE_PACKAGE_VERSION,
        "legacy_version": "week10-draft",
        "storage_mode": "in_memory",
        "document_count": len(normalized_records),
        "index": index,
        "compressed_payloads": compressed_payloads,
        "manifest": manifest,
        "sync": {
            "state": "ready",
            "mode": "manifest_compare",
            "package_fingerprint": manifest["package_fingerprint"],
            "source_watermark": manifest["source_watermark"],
            "priority_record_ids": priority_record_ids,
        },
        "record_fingerprints": manifest["record_fingerprints"],
        "priority_record_ids": priority_record_ids,
        "notes": [
            "offline-sync-v1 keeps compressed payloads in memory",
            "manifest supports priority sync and stale package detection",
            "persistent on-disk format is intentionally not written by this module",
        ],
    }


def normalize_client_manifest(client_manifest: Any) -> dict[str, Any]:
    if not isinstance(client_manifest, dict):
        return {}
    nested_manifest = client_manifest.get("manifest")
    if isinstance(nested_manifest, dict):
        return nested_manifest
    return client_manifest


def evaluate_offline_sync_state(
    offline_package: dict[str, Any],
    client_manifest: Any | None = None,
) -> dict[str, Any]:
    manifest = offline_package.get("manifest")
    if not isinstance(manifest, dict):
        return {
            "offline_ready": False,
            "needs_sync": True,
            "sync_required": True,
            "reason": "missing_server_manifest",
            "compatible": False,
            "missing_record_ids": [],
            "changed_record_ids": [],
            "removed_record_ids": [],
            "priority_refresh_ids": [],
        }

    client = normalize_client_manifest(client_manifest)
    server_fingerprint = str(manifest.get("package_fingerprint", ""))
    client_fingerprint = str(client.get("package_fingerprint", ""))
    if not client:
        return {
            "offline_ready": True,
            "needs_sync": True,
            "sync_required": True,
            "reason": "missing_client_manifest",
            "compatible": True,
            "server_package_fingerprint": server_fingerprint,
            "client_package_fingerprint": "",
            "missing_record_ids": sorted(manifest.get("record_fingerprints", {}).keys()),
            "changed_record_ids": [],
            "removed_record_ids": [],
            "priority_refresh_ids": manifest.get("priority_record_ids", []),
        }

    if client.get("schema_version") != manifest.get("schema_version"):
        return {
            "offline_ready": True,
            "needs_sync": True,
            "sync_required": True,
            "reason": "schema_mismatch",
            "compatible": False,
            "server_package_fingerprint": server_fingerprint,
            "client_package_fingerprint": client_fingerprint,
            "missing_record_ids": sorted(manifest.get("record_fingerprints", {}).keys()),
            "changed_record_ids": [],
            "removed_record_ids": [],
            "priority_refresh_ids": manifest.get("priority_record_ids", []),
        }

    if client_fingerprint and client_fingerprint == server_fingerprint:
        return {
            "offline_ready": True,
            "needs_sync": False,
            "sync_required": False,
            "reason": "up_to_date",
            "compatible": True,
            "server_package_fingerprint": server_fingerprint,
            "client_package_fingerprint": client_fingerprint,
            "missing_record_ids": [],
            "changed_record_ids": [],
            "removed_record_ids": [],
            "priority_refresh_ids": [],
        }

    server_records = manifest.get("record_fingerprints", {})
    client_records = client.get("record_fingerprints", {})
    if not isinstance(server_records, dict):
        server_records = {}
    if not isinstance(client_records, dict):
        client_records = {}

    server_ids = set(server_records)
    client_ids = set(client_records)
    missing_record_ids = sorted(server_ids - client_ids)
    removed_record_ids = sorted(client_ids - server_ids)
    changed_record_ids = sorted(
        record_id
        for record_id in server_ids & client_ids
        if server_records.get(record_id) != client_records.get(record_id)
    )
    priority_record_ids = list(manifest.get("priority_record_ids", []))
    priority_refresh_ids = [
        record_id
        for record_id in priority_record_ids
        if record_id in missing_record_ids or record_id in changed_record_ids
    ]
    needs_sync = bool(missing_record_ids or changed_record_ids or removed_record_ids)

    return {
        "offline_ready": True,
        "needs_sync": needs_sync,
        "sync_required": needs_sync,
        "reason": "manifest_diff" if needs_sync else "fingerprint_mismatch_without_record_diff",
        "compatible": True,
        "server_package_fingerprint": server_fingerprint,
        "client_package_fingerprint": client_fingerprint,
        "missing_record_ids": missing_record_ids,
        "changed_record_ids": changed_record_ids,
        "removed_record_ids": removed_record_ids,
        "priority_refresh_ids": priority_refresh_ids,
    }


def search_offline_diaries(
    offline_package: dict[str, Any],
    query: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    index = offline_package.get("index")
    if not isinstance(index, DiaryFullTextIndex):
        return {
            "results": [],
            "total": 0,
            "query_terms": [],
            "offline_ready": False,
        }

    result = index.search(query, limit=limit)
    result["offline_ready"] = True
    result["storage_mode"] = str(offline_package.get("storage_mode", "unknown"))
    if isinstance(offline_package.get("manifest"), dict):
        result["offline_manifest"] = offline_package["manifest"]
    if isinstance(offline_package.get("sync"), dict):
        result["sync"] = offline_package["sync"]
    return result


def restore_diary_content(offline_package: dict[str, Any], diary_id: str) -> str:
    payloads = offline_package.get("compressed_payloads", {})
    if not isinstance(payloads, dict):
        return ""

    payload = payloads.get(diary_id)
    if not isinstance(payload, dict):
        return ""

    return decompress_text(payload)


__all__ = [
    "OFFLINE_PACKAGE_VERSION",
    "OFFLINE_SCHEMA_VERSION",
    "build_offline_diary_index",
    "build_record_fingerprints",
    "evaluate_offline_sync_state",
    "search_offline_diaries",
    "restore_diary_content",
]
