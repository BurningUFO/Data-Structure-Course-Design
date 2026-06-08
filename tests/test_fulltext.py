import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.compress.fulltext import DiaryFullTextIndex, search_diary_fulltext
from src.compress.offline_index import (
    build_offline_diary_index,
    evaluate_offline_sync_state,
    restore_diary_content,
    search_offline_diaries,
)
from src.diary.diary_service import load_diary_records


def test_build_index_manifest():
    records = load_diary_records()
    index = DiaryFullTextIndex(records)

    assert index.document_count == len(records)
    assert index.document_count >= 132
    assert index.token_count > 0
    assert "图书馆" in index.index
    print("test_build_index_manifest passed.")


def test_search_single_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="北大图书馆", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "北大图书馆" in result["results"][0]["matched_terms"]
    assert result["results"][0]["destination_node_id"] == "library"
    print("test_search_single_keyword passed.")


def test_search_multi_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="北大图书馆 自习", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "北大图书馆" in result["results"][0]["matched_terms"]
    assert "自习" in result["results"][0]["matched_terms"]
    assert result["results"][0]["score"] > 0
    print("test_search_multi_keyword passed.")


def test_search_alias_keyword():
    records = load_diary_records()
    result = search_diary_fulltext(query="北大图书馆", records=records, limit=5)

    assert result["total"] >= 1
    assert result["results"][0]["diary_id"] == "diary_003"
    assert "北大图书馆" in result["results"][0]["matched_terms"]
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
    result = search_offline_diaries(package, "北大图书馆 自习", limit=3)

    assert package["version"] == "offline-sync-v1"
    assert package["legacy_version"] == "week10-draft"
    assert package["manifest"]["schema_version"] == "diary-offline-package-v1"
    assert package["manifest"]["document_count"] == len(records)
    assert package["manifest"]["priority_policy"]["limit"] == 50
    assert package["manifest"]["capabilities"]["priority_sync"] is True
    assert package["manifest"]["capabilities"]["incremental_sync_check"] is True
    assert package["manifest"]["size_estimates"]["estimated_package_size_bytes"] > 0
    assert len(package["priority_record_ids"]) == 50
    assert result["offline_ready"] is True
    assert result["offline_manifest"]["package_fingerprint"] == package["manifest"]["package_fingerprint"]
    assert result["sync"]["state"] == "ready"
    assert result["results"][0]["diary_id"] == "diary_003"
    assert restore_diary_content(package, "diary_003") == records[2]["content"]
    print("test_offline_index_roundtrip passed.")


def test_offline_sync_state_detects_missing_changed_and_current_manifest():
    records = load_diary_records()[:5]
    package = build_offline_diary_index(records, priority_limit=3)
    manifest = package["manifest"]

    missing_client = evaluate_offline_sync_state(package)
    current_client = evaluate_offline_sync_state(package, manifest)

    stale_manifest = {
        **manifest,
        "package_fingerprint": "stale",
        "record_fingerprints": {
            record_id: fingerprint
            for index, (record_id, fingerprint) in enumerate(manifest["record_fingerprints"].items())
            if index > 0
        },
    }
    changed_record_id = next(iter(stale_manifest["record_fingerprints"]))
    stale_manifest["record_fingerprints"][changed_record_id] = "changed"
    stale_client = evaluate_offline_sync_state(package, stale_manifest)

    assert missing_client["needs_sync"] is True
    assert missing_client["reason"] == "missing_client_manifest"
    assert current_client["needs_sync"] is False
    assert current_client["reason"] == "up_to_date"
    assert stale_client["needs_sync"] is True
    assert stale_client["reason"] == "manifest_diff"
    assert stale_client["missing_record_ids"]
    assert changed_record_id in stale_client["changed_record_ids"]
    assert set(stale_client["priority_refresh_ids"]).issubset(set(manifest["priority_record_ids"]))
    print("test_offline_sync_state_detects_missing_changed_and_current_manifest passed.")


def run_all_tests():
    print("Running fulltext module tests...")
    test_build_index_manifest()
    test_search_single_keyword()
    test_search_multi_keyword()
    test_search_alias_keyword()
    test_search_no_match()
    test_offline_index_roundtrip()
    test_offline_sync_state_detects_missing_changed_and_current_manifest()
    print("All fulltext tests passed.")


if __name__ == "__main__":
    run_all_tests()
