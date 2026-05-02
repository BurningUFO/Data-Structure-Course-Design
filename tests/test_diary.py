import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.diary.diary_service import DiaryService, load_diary_records, search_diaries


LEGACY_DIARY_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "成员Cdata",
    "diary_test.json",
)


def test_load_default_records():
    service = DiaryService()

    assert len(service.records) == 12
    assert service.records[0]["id"] == "diary_001"
    assert service.records[0]["title"] == "秋日燕园游记"
    print("test_load_default_records passed.")


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
    assert result["metadata"]["data_source"]["path"].endswith("diary_data.json")
    assert "destination_node_id" in result["metadata"]["result_fields"]
    print("test_diary_response_shape passed.")


def run_all_tests():
    print("Running diary module tests...")
    test_load_default_records()
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
    print("All diary tests passed.")


if __name__ == "__main__":
    run_all_tests()
