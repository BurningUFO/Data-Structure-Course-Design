"""
成员 C：第十周倒排索引全文检索基础版

当前实现目标：
1. 基于标准日记记录构建最小可运行倒排索引
2. 在不依赖复杂中文分词的前提下，支持中文关键词与多关键词检索
3. 与成员 B 已约定的最小结果字段契约保持一致

当前限制：
- 不支持布尔查询、短语查询、TF-IDF
- 中文采用轻量 CJK n-gram，而非完整分词
- 默认采用 OR 检索 + 覆盖度加权排序
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


Record = dict[str, Any]

TERM_EQUIVALENT_GROUPS = (
    ("图书馆", "tsg", "library"),
    ("未名湖", "wml"),
    ("北京大学", "北大", "pku", "bjd"),
    ("洗手间", "卫生间", "厕所", "wc", "restroom", "xsj"),
    ("食堂", "餐厅", "餐饮", "catering", "st"),
    ("便利店", "超市", "商店", "shopping", "bld"),
)

FIELD_WEIGHTS: dict[str, float] = {
    "title": 18.0,
    "tags": 14.0,
    "destination": 10.0,
    "content": 6.0,
}

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+")
MAX_CJK_TOKEN_LENGTH = 8


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


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


def build_term_aliases() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for group in TERM_EQUIVALENT_GROUPS:
        normalized_group = [normalize_text(term) for term in group if normalize_text(term)]
        for term in normalized_group:
            aliases[term] = [candidate for candidate in normalized_group if candidate != term]
    return aliases


TERM_ALIASES = build_term_aliases()


def expand_query_term(term: str) -> list[str]:
    normalized_term = normalize_text(term)
    if not normalized_term:
        return []
    return unique_strings([normalized_term, *TERM_ALIASES.get(normalized_term, [])])


def split_query_terms(query: str) -> list[str]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    raw_parts = [part for part in normalized_query.split() if part]
    if not raw_parts:
        raw_parts = [normalized_query]

    terms: list[str] = []
    for part in raw_parts:
        fragments = TOKEN_PATTERN.findall(part)
        if fragments:
            terms.extend(fragments)
        else:
            terms.append(part)

    if not terms:
        terms = [normalized_query]

    return unique_strings(terms)


def generate_index_tokens(value: Any) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []

    tokens: list[str] = []
    for fragment in TOKEN_PATTERN.findall(normalized):
        if not fragment:
            continue
        if fragment.isascii():
            tokens.append(fragment)
            continue

        fragment_length = len(fragment)
        if fragment_length == 1:
            tokens.append(fragment)
            continue

        max_length = min(MAX_CJK_TOKEN_LENGTH, fragment_length)
        for token_length in range(2, max_length + 1):
            for start in range(fragment_length - token_length + 1):
                tokens.append(fragment[start : start + token_length])

    return tokens


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


@dataclass
class DiaryFullTextIndex:
    records: list[Record]
    index: dict[str, dict[str, dict[str, int]]] = field(init=False, default_factory=dict)
    records_by_id: dict[str, Record] = field(init=False, default_factory=dict)
    document_count: int = field(init=False, default=0)
    token_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.records_by_id = {}
        for record in self.records:
            diary_id = str(record.get("id", "")).strip()
            if not diary_id:
                continue
            self.records_by_id[diary_id] = record

        self.index = self._build_index(list(self.records_by_id.values()))
        self.document_count = len(self.records_by_id)
        self.token_count = len(self.index)

    def _build_index(self, records: list[Record]) -> dict[str, dict[str, dict[str, int]]]:
        postings: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)

        for record in records:
            diary_id = str(record.get("id", "")).strip()
            if not diary_id:
                continue

            field_values: dict[str, list[Any]] = {
                "title": [record.get("title")],
                "content": [record.get("content")],
                "destination": [record.get("destination")],
                "tags": list(record.get("tags", [])),
            }

            for field_name, values in field_values.items():
                for value in values:
                    for token in generate_index_tokens(value):
                        field_counts = postings[token].setdefault(diary_id, {})
                        field_counts[field_name] = field_counts.get(field_name, 0) + 1

        return dict(postings)

    def manifest(self) -> dict[str, Any]:
        return {
            "document_count": self.document_count,
            "token_count": self.token_count,
            "tokenizer": "lightweight_cjk_ngram",
            "max_cjk_token_length": MAX_CJK_TOKEN_LENGTH,
        }

    def search(self, query: str, *, limit: int = 10) -> dict[str, Any]:
        safe_limit = limit if limit > 0 else 10
        query_terms = split_query_terms(query)
        if not query_terms:
            return {
                "results": [],
                "total": 0,
                "query_terms": [],
                "index_manifest": self.manifest(),
            }

        doc_scores: dict[str, float] = defaultdict(float)
        doc_matched_terms: dict[str, list[str]] = defaultdict(list)

        for query_term in query_terms:
            best_candidate = ""
            best_candidate_mass = 0
            best_postings: dict[str, dict[str, int]] | None = None

            for candidate in expand_query_term(query_term):
                postings = self.index.get(candidate)
                if not postings:
                    continue

                candidate_mass = sum(sum(field_counts.values()) for field_counts in postings.values())
                if candidate_mass > best_candidate_mass:
                    best_candidate = candidate
                    best_candidate_mass = candidate_mass
                    best_postings = postings

            if not best_postings or not best_candidate:
                continue

            for diary_id, field_counts in best_postings.items():
                contribution = sum(
                    float(count) * FIELD_WEIGHTS.get(field_name, 1.0)
                    for field_name, count in field_counts.items()
                )
                doc_scores[diary_id] += contribution
                if best_candidate not in doc_matched_terms[diary_id]:
                    doc_matched_terms[diary_id].append(best_candidate)

        ranked_results: list[Record] = []
        for diary_id, base_score in doc_scores.items():
            record = self.records_by_id.get(diary_id)
            if not record:
                continue

            matched_terms = doc_matched_terms.get(diary_id, [])
            coverage = len(matched_terms)
            score = base_score + coverage * 8
            if len(query_terms) > 1 and coverage == len(query_terms):
                score += 20

            score += int(record.get("heat", 0)) * 0.05
            score += float(record.get("rating", 0.0)) * 2

            destination_node_id = record.get("destination_node_id")
            if destination_node_id is not None:
                destination_node_id = str(destination_node_id).strip() or None

            ranked_results.append(
                {
                    "id": diary_id,
                    "diary_id": diary_id,
                    "title": str(record.get("title", "")).strip(),
                    "matched_terms": matched_terms,
                    "score": round(score, 2),
                    "destination": str(record.get("destination", "")).strip(),
                    "destination_node_id": destination_node_id,
                    "snippet": build_snippet(str(record.get("content", "")), matched_terms),
                }
            )

        ranked_results.sort(
            key=lambda item: (
                -float(item.get("score", 0.0)),
                -int(self.records_by_id.get(item["diary_id"], {}).get("heat", 0)),
                -float(self.records_by_id.get(item["diary_id"], {}).get("rating", 0.0)),
                str(item.get("title", "")),
            )
        )

        return {
            "results": ranked_results[:safe_limit],
            "total": len(ranked_results),
            "query_terms": query_terms,
            "index_manifest": self.manifest(),
        }


def build_fulltext_index(records: list[Record]) -> DiaryFullTextIndex:
    return DiaryFullTextIndex(records)


def search_diary_fulltext(
    query: str,
    records: list[Record] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    index = DiaryFullTextIndex(records or [])
    return index.search(query, limit=limit)


def search_fulltext(
    *,
    query: str,
    records: list[Record] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    return search_diary_fulltext(query=query, records=records, limit=limit)


def search_diaries_fulltext(
    *,
    query: str,
    records: list[Record] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    return search_diary_fulltext(query=query, records=records, limit=limit)


__all__ = [
    "DiaryFullTextIndex",
    "build_fulltext_index",
    "search_diary_fulltext",
    "search_fulltext",
    "search_diaries_fulltext",
    "split_query_terms",
]
