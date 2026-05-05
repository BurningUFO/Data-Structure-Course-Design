"""
成员 C：第十周离线索引预留接口

本周先提供内存级草稿：
1. 对日记正文执行哈夫曼压缩，保留解压能力
2. 同时构建全文检索倒排索引
3. 为第11周的持久化缓存格式预留统一入口

当前版本不负责把离线包写入磁盘，只提供可演示、可测试的运行时结构。
"""

from __future__ import annotations

from typing import Any

from src.compress.fulltext import DiaryFullTextIndex
from src.compress.huffman import compress_text, decompress_text


Record = dict[str, Any]


def build_offline_diary_index(records: list[Record]) -> dict[str, Any]:
    compressed_payloads: dict[str, dict[str, Any]] = {}
    normalized_records: list[Record] = []

    for record in records:
        diary_id = str(record.get("id", "")).strip()
        if not diary_id:
            continue

        normalized_records.append(record)
        compressed_payloads[diary_id] = compress_text(str(record.get("content", "")))

    index = DiaryFullTextIndex(normalized_records)
    return {
        "version": "week10-draft",
        "storage_mode": "in_memory",
        "document_count": len(normalized_records),
        "index": index,
        "compressed_payloads": compressed_payloads,
        "notes": [
            "week10 draft keeps compressed payloads in memory",
            "persistent on-disk format will be finalized in week11",
        ],
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
    "build_offline_diary_index",
    "search_offline_diaries",
    "restore_diary_content",
]
