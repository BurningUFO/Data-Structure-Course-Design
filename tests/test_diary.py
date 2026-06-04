import os
import sys
import json
import tempfile
import threading
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.diary.diary_service import DiaryService, load_diary_records, search_diaries, search_diaries_fulltext


LEGACY_DIARY_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "成员Cdata",
    "diary_test.json",
)
DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DEFAULT_DIARY_PATH = DATA_ROOT / "diary_data.json"
GLOBAL_SITES_PATH = DATA_ROOT / "global_sites.json"


def load_global_site_names():
    data = json.loads(GLOBAL_SITES_PATH.read_text(encoding="utf-8"))
    return [site["name"] for site in data["sites"]]


def make_temp_diary_data_path():
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = Path(temp_dir.name) / "diary_data.json"
    temp_path.write_text(DEFAULT_DIARY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return temp_dir, temp_path


def test_load_default_records():
    service = DiaryService()

    assert len(service.records) == len(json.loads(DEFAULT_DIARY_PATH.read_text(encoding="utf-8")))
    assert len(service.records) >= 132
    assert service.records[0]["id"] == "diary_001"
    assert service.records[0]["title"] == "秋日燕园游记"
    print("test_load_default_records passed.")


def test_default_records_cover_formal_campus_sites():
    service = DiaryService()
    site_names = load_global_site_names()

    counts = {
        site_name: sum(1 for record in service.records if record["destination"] == site_name)
        for site_name in site_names
    }

    assert counts["北京大学"] >= 7
    for site_name in site_names:
        if site_name == "北京大学":
            continue
        assert counts[site_name] == 6
    print("test_default_records_cover_formal_campus_sites passed.")


def test_load_legacy_records_markdown_json():
    records = load_diary_records(LEGACY_DIARY_PATH)

    assert len(records) >= 50
    assert records[0]["id"] == "diary_001"
    assert records[0]["title"]
    print("test_load_legacy_records_markdown_json passed.")


def test_search_by_title_exact():
    service = DiaryService()
    result = service.search_by_title_exact("五一黄山行")

    assert len(result) == 1
    assert result[0]["id"] == "diary_004"
    print("test_search_by_title_exact passed.")


def test_search_by_title_fuzzy():
    service = DiaryService()
    result = service.search_by_title("黄山", match_mode="fuzzy")

    assert len(result) == 1
    assert "黄山" in result[0]["title"]
    print("test_search_by_title_fuzzy passed.")


def test_search_by_destination_exact():
    service = DiaryService()
    result = service.search_by_destination("北京大学", match_mode="exact")

    assert len(result) == 7
    print("test_search_by_destination_exact passed.")


def test_search_sort_by_heat():
    result = search_diaries(destination="北京大学", sort_field="heat")
    heats = [item["heat"] for item in result["data"]]

    assert result["success"] is True
    assert result["query_type"] == "diary_search"
    assert heats == sorted(heats, reverse=True)
    assert result["metadata"]["ranking"]["sort_field"] == "heat"
    print("test_search_sort_by_heat passed.")


def test_search_sort_by_rating():
    result = search_diaries(destination="北京大学", sort_field="rating")
    ratings = [item["rating"] for item in result["data"]]

    assert ratings == sorted(ratings, reverse=True)
    assert result["metadata"]["ranking"]["sort_field"] == "rating"
    print("test_search_sort_by_rating passed.")


def test_search_limit_and_total_matched():
    result = search_diaries(destination="北京大学", limit=3)

    assert result["total"] == 3
    assert result["metadata"]["total_matched"] == 7
    print("test_search_limit_and_total_matched passed.")


def test_search_no_match():
    result = search_diaries(keyword="不存在的日记")

    assert result["success"] is True
    assert result["total"] == 0
    assert result["message"] == "no matched diaries"
    print("test_search_no_match passed.")


def test_search_legacy_dataset_support():
    result = search_diaries(
        keyword="黄山",
        data_path=LEGACY_DIARY_PATH,
        sort_field="heat",
        limit=5,
    )

    assert result["success"] is True
    assert result["total"] >= 1
    assert any(
        "黄山" in item["title"] or "黄山" in item["destination"]
        for item in result["data"]
    )
    print("test_search_legacy_dataset_support passed.")


def test_diary_response_shape():
    result = search_diaries(destination="北京大学", sort_field="rating", limit=2)

    assert result["success"] is True
    assert result["results"] == result["data"]
    assert result["metadata"]["data_source"]["path"].endswith("diary_data.json")
    assert "destination_node_id" in result["metadata"]["result_fields"]
    print("test_diary_response_shape passed.")


def test_diary_interest_recommendation_changes_with_user_interests():
    study_result = search_diaries(
        destination="北京大学",
        sort_field="interest",
        interests=["图书馆", "校园", "秋景"],
        limit=10,
    )
    food_result = search_diaries(
        destination="北京大学",
        sort_field="interest",
        interests=["美食", "食堂", "校园生活"],
        limit=10,
    )

    assert study_result["success"] is True
    assert food_result["success"] is True
    assert study_result["metadata"]["interest"]["active_for_ranking"] is True
    assert food_result["metadata"]["interest"]["active_for_ranking"] is True
    assert any(item["id"] in {"diary_001", "diary_003"} for item in study_result["results"])
    assert any(item["id"] == "diary_002" for item in food_result["results"])
    assert study_result["results"][0]["id"] != food_result["results"][0]["id"]
    assert study_result["results"][0]["interest_reason"]
    print("test_diary_interest_recommendation_changes_with_user_interests passed.")


def test_diary_management_create_update_rate_delete_flow():
    service = DiaryService(records=[])
    created = service.create_diary(
        {
            "title": "第十一周日记管理接口联调",
            "content": "用于验证创建、编辑、评分、删除的内存态闭环。",
            "author_id": "user_test",
            "author_name": "测试用户",
            "destination": "北京大学图书馆",
            "destination_node_id": "library",
            "rating": 4.2,
            "tags": ["第十一周", "接口"],
            "images": ["media/placeholders/test_diary.jpg"],
            "videos": ["media/placeholders/test_diary.mp4"],
        }
    )

    assert created["success"] is True
    assert created["query_type"] == "diary_create"
    assert created["metadata"]["storage_mode"] == "memory_only"
    assert created["metadata"]["data_source"]["write_back"] is False
    diary = created["results"][0]
    assert diary["id"] == "diary_001"
    assert diary["destination_node_id"] == "library"
    assert diary["images"] == ["media/placeholders/test_diary.jpg"]
    assert diary["videos"] == ["media/placeholders/test_diary.mp4"]

    updated = service.update_diary(
        diary["id"],
        {
            "title": "第十一周日记管理接口复盘",
            "content": "更新后的日记正文。",
            "rating": 6,
            "tags": "复盘",
        },
    )

    assert updated["success"] is True
    assert updated["query_type"] == "diary_update"
    assert updated["results"][0]["title"] == "第十一周日记管理接口复盘"
    assert updated["results"][0]["rating"] == 5.0
    assert updated["results"][0]["tags"] == ["复盘"]

    rated = service.rate_diary(diary["id"], 4.8)

    assert rated["success"] is True
    assert rated["query_type"] == "diary_rate"
    assert rated["results"][0]["rating"] == 4.8

    deleted = service.delete_diary(diary["id"])

    assert deleted["success"] is True
    assert deleted["query_type"] == "diary_delete"
    assert deleted["results"][0]["id"] == diary["id"]
    assert service.records == []
    print("test_diary_management_create_update_rate_delete_flow passed.")


def test_diary_management_file_backed_persistence_flow():
    temp_dir, temp_path = make_temp_diary_data_path()
    try:
        service = DiaryService(data_path=temp_path)
        baseline_count = len(service.records)
        created = service.create_diary(
            {
                "title": "真实写回创建验证",
                "content": "用于验证日记文件写回、重载和全文检索链路。",
                "author_id": "user_test",
                "author_name": "测试用户",
                "destination": "北京大学图书馆",
                "destination_node_id": "library",
                "rating": 4.6,
                "tags": ["真实写回", "测试"],
                "images": ["media/placeholders/test_diary.jpg"],
                "videos": ["media/placeholders/test_diary.mp4"],
            }
        )

        assert created["success"] is True
        assert created["metadata"]["storage_mode"] == "file_backed"
        assert created["metadata"]["data_source"]["write_back"] is True
        diary_id = created["results"][0]["id"]

        reloaded_after_create = DiaryService(data_path=temp_path)
        created_record = next(record for record in reloaded_after_create.records if record["id"] == diary_id)
        assert len(reloaded_after_create.records) == baseline_count + 1
        assert created_record["title"] == "真实写回创建验证"
        assert created_record["videos"] == ["media/placeholders/test_diary.mp4"]

        fulltext_result = search_diaries_fulltext(
            query="真实写回创建验证",
            limit=5,
            data_path=temp_path,
        )
        assert fulltext_result["success"] is True
        assert any(item["id"] == diary_id for item in fulltext_result["results"])

        updated = reloaded_after_create.update_diary(
            diary_id,
            {
                "title": "真实写回更新验证",
                "content": "更新后的正文仍应能在重载后读到。",
                "tags": "更新后",
            },
        )
        assert updated["success"] is True

        reloaded_after_update = DiaryService(data_path=temp_path)
        updated_record = next(record for record in reloaded_after_update.records if record["id"] == diary_id)
        assert updated_record["title"] == "真实写回更新验证"
        assert updated_record["tags"] == ["更新后"]

        rated = reloaded_after_update.rate_diary(diary_id, 4.9)
        assert rated["success"] is True

        reloaded_after_rate = DiaryService(data_path=temp_path)
        rated_record = next(record for record in reloaded_after_rate.records if record["id"] == diary_id)
        assert rated_record["rating"] == 4.9

        deleted = reloaded_after_rate.delete_diary(diary_id)
        assert deleted["success"] is True

        reloaded_after_delete = DiaryService(data_path=temp_path)
        assert len(reloaded_after_delete.records) == baseline_count
        assert all(record["id"] != diary_id for record in reloaded_after_delete.records)
    finally:
        temp_dir.cleanup()
    print("test_diary_management_file_backed_persistence_flow passed.")


def test_diary_management_records_injection_does_not_write_back():
    temp_dir, temp_path = make_temp_diary_data_path()
    try:
        original_records = DiaryService(data_path=temp_path).records
        service = DiaryService(records=[], data_path=temp_path)
        created = service.create_diary(
            {
                "title": "隔离内存态验证",
                "content": "这条记录不应写回临时日记文件。",
            }
        )

        assert created["success"] is True
        assert created["metadata"]["storage_mode"] == "memory_only"
        assert created["metadata"]["data_source"]["write_back"] is False

        reloaded = DiaryService(data_path=temp_path)
        assert len(reloaded.records) == len(original_records)
        assert all(record["title"] != "隔离内存态验证" for record in reloaded.records)
    finally:
        temp_dir.cleanup()
    print("test_diary_management_records_injection_does_not_write_back passed.")


def test_diary_management_file_backed_concurrent_create_keeps_both_records():
    temp_dir, temp_path = make_temp_diary_data_path()
    try:
        baseline_count = len(DiaryService(data_path=temp_path).records)
        barrier = threading.Barrier(2)
        results: list[dict[str, object]] = []
        result_lock = threading.Lock()

        def create_from_separate_service(title: str) -> None:
            service = DiaryService(data_path=temp_path)
            barrier.wait()
            response = service.create_diary(
                {
                    "title": title,
                    "content": "并发写入回归测试。",
                    "rating": 4.1,
                }
            )
            with result_lock:
                results.append(response)

        threads = [
            threading.Thread(
                target=create_from_separate_service,
                args=(f"并发写入回归 {index}",),
            )
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(results) == 2
        assert all(result["success"] is True for result in results)
        created_ids = [result["results"][0]["id"] for result in results]
        assert len(set(created_ids)) == 2

        reloaded = DiaryService(data_path=temp_path)
        created_records = [
            record
            for record in reloaded.records
            if str(record.get("title", "")).startswith("并发写入回归")
        ]
        assert len(reloaded.records) == baseline_count + 2
        assert len(created_records) == 2
        assert {record["id"] for record in created_records} == set(created_ids)
    finally:
        temp_dir.cleanup()
    print("test_diary_management_file_backed_concurrent_create_keeps_both_records passed.")


def test_diary_management_create_rejects_invalid_rating_without_write_back():
    temp_dir, temp_path = make_temp_diary_data_path()
    try:
        service = DiaryService(data_path=temp_path)
        baseline_count = len(service.records)

        invalid = service.create_diary(
            {
                "title": "非法评分不应落盘",
                "content": "显式传入不可解析评分时应失败。",
                "rating": "not-a-number",
            }
        )

        assert invalid["success"] is False
        assert invalid["query_type"] == "diary_create"
        assert invalid["message"] == "diary rating must be a number between 0 and 5"

        reloaded = DiaryService(data_path=temp_path)
        assert len(reloaded.records) == baseline_count
        assert all(record["title"] != "非法评分不应落盘" for record in reloaded.records)

        valid_without_rating = service.create_diary({"title": "未传评分仍可创建"})
        assert valid_without_rating["success"] is True
        assert valid_without_rating["results"][0]["rating"] == 0.0
    finally:
        temp_dir.cleanup()
    print("test_diary_management_create_rejects_invalid_rating_without_write_back passed.")


def test_diary_management_validation_errors():
    service = DiaryService(records=[])

    empty_title = service.create_diary({"title": "   "})
    assert empty_title["success"] is False
    assert empty_title["query_type"] == "diary_create"

    first = service.create_diary({"id": "manual_diary", "title": "测试日记"})
    duplicate = service.create_diary({"id": "manual_diary", "title": "重复日记"})
    invalid_create_rating = service.create_diary(
        {"title": "非法创建评分", "rating": "not-a-number"}
    )
    invalid_update = service.update_diary("manual_diary", {"title": ""})
    invalid_rating = service.rate_diary("manual_diary", "bad-rating")
    missing_delete = service.delete_diary("missing_diary")

    assert first["success"] is True
    assert duplicate["success"] is False
    assert invalid_create_rating["success"] is False
    assert invalid_update["success"] is False
    assert invalid_rating["success"] is False
    assert missing_delete["success"] is False
    print("test_diary_management_validation_errors passed.")


def test_search_fulltext_single_keyword():
    result = search_diaries_fulltext(query="北大图书馆", limit=5)

    assert result["success"] is True
    assert result["query_type"] == "diary_fulltext_search"
    assert result["total"] >= 1
    assert result["metadata"]["fulltext"]["backend"].startswith("src.compress.fulltext.")
    assert result["metadata"]["fulltext"]["backend_mode"] == "primary"
    assert result["metadata"]["fulltext"]["index_manifest"]["document_count"] >= 132
    assert result["results"][0]["title"] == "图书馆自习攻略"
    assert "北大图书馆" in result["results"][0]["matched_terms"]
    assert result["results"][0]["destination_node_id"] == "library"
    print("test_search_fulltext_single_keyword passed.")


def test_search_fulltext_multi_keyword():
    result = search_diaries_fulltext(query="北大图书馆 自习", limit=5)

    assert result["success"] is True
    assert result["total"] >= 1
    assert result["results"][0]["title"] == "图书馆自习攻略"
    assert "北大图书馆" in result["results"][0]["matched_terms"]
    assert "自习" in result["results"][0]["matched_terms"]
    assert result["metadata"]["fulltext"]["route_hint_available_count"] >= 1
    print("test_search_fulltext_multi_keyword passed.")


def test_search_fulltext_empty_query():
    result = search_diaries_fulltext(query="   ", limit=3)

    assert result["success"] is False
    assert result["message"] == "fulltext query cannot be empty"
    assert result["results"] == []
    print("test_search_fulltext_empty_query passed.")


def run_all_tests():
    print("Running diary module tests...")
    test_load_default_records()
    test_default_records_cover_formal_campus_sites()
    test_load_legacy_records_markdown_json()
    test_search_by_title_exact()
    test_search_by_title_fuzzy()
    test_search_by_destination_exact()
    test_search_sort_by_heat()
    test_search_sort_by_rating()
    test_search_limit_and_total_matched()
    test_search_no_match()
    test_search_legacy_dataset_support()
    test_diary_response_shape()
    test_diary_interest_recommendation_changes_with_user_interests()
    test_diary_management_create_update_rate_delete_flow()
    test_diary_management_file_backed_persistence_flow()
    test_diary_management_records_injection_does_not_write_back()
    test_diary_management_file_backed_concurrent_create_keeps_both_records()
    test_diary_management_create_rejects_invalid_rating_without_write_back()
    test_diary_management_validation_errors()
    test_search_fulltext_single_keyword()
    test_search_fulltext_multi_keyword()
    test_search_fulltext_empty_query()
    print("All diary tests passed.")


if __name__ == "__main__":
    run_all_tests()
