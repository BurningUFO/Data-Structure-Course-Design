import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.compress.fulltext import DiaryFullTextIndex, search_diary_fulltext
from src.compress.offline_index import build_offline_diary_index, restore_diary_content, search_offline_diaries
from src.diary.diary_service import load_diary_records


def test_build_index_manifest():
    records = load_diary_records()
    index = DiaryFullTextIndex(records)

    assert index.document_count == 12
    assert index.token_count > 0
    assert "图书馆" in index.index
    print("test_build_index_manifest passed.")


def test_search_single_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="图书馆", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "图书馆" in result["results"][0]["matched_terms"]
    assert result["results"][0]["destination_node_id"] == "library"
    print("test_search_single_keyword passed.")


def test_search_multi_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="图书馆 自习", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "图书馆" in result["results"][0]["matched_terms"]
    assert "自习" in result["results"][0]["matched_terms"]
    assert result["results"][0]["score"] > 0
    print("test_search_multi_keyword passed.")


def test_search_alias_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="library", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "图书馆" in result["results"][0]["matched_terms"]
    print("test_search_alias_keyword passed.")


def test_search_no_match():
    records = load_diary_records()
    result = search_diary_fulltext(query="火星基地", records=records, limit=5)

    assert result["total"] == 0
    assert result["results"] == []
    print("test_search_no_match passed.")


def test_offline_index_roundtrip():
    records = load_diary_records()
    package = build_offline_diary_index(records)
    result = search_offline_diaries(package, "图书馆 自习", limit=3)

    assert result["offline_ready"] is True
    assert result["results"][0]["diary_id"] == "diary_003"
    assert restore_diary_content(package, "diary_003") == records[2]["content"]
    print("test_offline_index_roundtrip passed.")


def run_all_tests():
    print("Running fulltext module tests...")
    test_build_index_manifest()
    test_search_single_keyword()
    test_search_multi_keyword()
    test_search_alias_keyword()
    test_search_no_match()
    test_offline_index_roundtrip()
    print("All fulltext tests passed.")


if __name__ == "__main__":
    run_all_tests()
