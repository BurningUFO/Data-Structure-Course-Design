import os
import sys

# 将项目根目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.search.cli_demo import query_and_recommend
from src.search.exact_search import (
    filter_by_category,
    filter_by_keyword,
    filter_by_name,
    search_records,
)
from src.search.fuzzy_search import fuzzy_search
from src.search.response import build_error_response, build_success_response


SAMPLE_RECORDS = [
    {
        "id": "poi_001",
        "name": "黄山风景区",
        "category": "自然景区",
        "heat": 97,
        "rating": 4.9,
        "tags": ["世界遗产", "云海"],
        "keywords": ["黄山", "迎客松"],
        "description": "黄山以奇松怪石著称。",
    },
    {
        "id": "poi_002",
        "name": "九寨沟风景区",
        "category": "自然景区",
        "heat": 96,
        "rating": 4.9,
        "tags": ["瀑布", "湖泊"],
        "keywords": ["九寨沟", "五花海"],
        "description": "九寨沟以湖泊和彩林闻名。",
    },
    {
        "id": "poi_003",
        "name": "乌镇",
        "category": "古镇景区",
        "heat": 93,
        "rating": 4.7,
        "tags": ["江南水乡", "古镇"],
        "keywords": ["乌镇", "西栅"],
        "description": "典型的江南水乡古镇。",
    },
]


def test_exact_name_search():
    result = filter_by_name(SAMPLE_RECORDS, "黄山风景区")
    assert len(result) == 1
    assert result[0]["id"] == "poi_001"
    print("test_exact_name_search passed.")


def test_category_filter():
    result = filter_by_category(SAMPLE_RECORDS, "自然景区")
    assert len(result) == 2
    print("test_category_filter passed.")


def test_keyword_filter():
    result = filter_by_keyword(SAMPLE_RECORDS, "西栅")
    assert len(result) == 1
    assert result[0]["name"] == "乌镇"
    print("test_keyword_filter passed.")


def test_combined_search():
    result = search_records(
        SAMPLE_RECORDS,
        category="自然景区",
        keyword="黄山",
    )
    assert len(result) == 1
    assert result[0]["name"] == "黄山风景区"
    print("test_combined_search passed.")


def test_fuzzy_search():
    result = fuzzy_search(SAMPLE_RECORDS, "黄山")
    assert len(result) >= 1
    assert result[0]["name"] == "黄山风景区"
    assert "_match_score" in result[0]
    print("test_fuzzy_search passed.")


def test_response_builder():
    success = build_success_response(
        data=[{"id": "poi_001"}],
        message="ok",
        query_type="scenic_search",
        filters={"keyword": "黄山"},
    )
    error = build_error_response(
        "invalid keyword",
        query_type="scenic_search",
        filters={"keyword": ""},
    )

    assert success["success"] is True
    assert success["total"] == 1
    assert error["success"] is False
    assert error["total"] == 0
    print("test_response_builder passed.")


def test_query_and_recommend_flow():
    response = query_and_recommend(
        keyword="黄山",
        category="",
        match_mode="fuzzy",
        sort_field="heat",
        limit=3,
    )

    assert response["success"] is True
    assert response["query_type"] == "scenic_search"
    assert response["total"] >= 1
    assert response["data"][0]["name"] == "黄山风景区"
    print("test_query_and_recommend_flow passed.")


def run_all_tests():
    print("Running search module tests...")
    test_exact_name_search()
    test_category_filter()
    test_keyword_filter()
    test_combined_search()
    test_fuzzy_search()
    test_response_builder()
    test_query_and_recommend_flow()
    print("All search tests passed.")


if __name__ == "__main__":
    run_all_tests()
