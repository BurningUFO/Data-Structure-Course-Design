import os
import sys

# 将项目根目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.recommend.ranking import recommend_top_k
from src.recommend.sorter import sort_records
from src.recommend.topk import top_k


SAMPLE_RECORDS = [
    {"id": "site_001", "name": "图书馆", "heat": 92, "rating": 4.8, "category": "education"},
    {"id": "site_002", "name": "百周年纪念广场", "heat": 96, "rating": 4.9, "category": "landmark"},
    {"id": "site_003", "name": "农园食堂", "heat": 80, "rating": 4.5, "category": "catering"},
    {"id": "site_004", "name": "第一教学楼", "heat": 88, "rating": 4.7, "category": "education"},
    {"id": "site_005", "name": "五四体育场", "heat": 84, "rating": 4.6, "category": "sports"},
]


def test_sort_by_heat():
    records = SAMPLE_RECORDS[:]
    sorted_records = sort_records(
        records,
        [{"field": "heat", "order": "desc"}],
    )

    assert len(sorted_records) == len(records)
    assert sorted_records[0]["name"] == "百周年纪念广场"
    assert sorted_records[0]["heat"] == 96
    assert sorted_records[-1]["heat"] == 80

    print("test_sort_by_heat passed.")


def test_sort_by_rating_then_heat():
    records = SAMPLE_RECORDS[:]
    sorted_records = sort_records(
        records,
        [
            {"field": "rating", "order": "desc"},
            {"field": "heat", "order": "desc"},
        ],
    )

    assert len(sorted_records) == len(records)
    assert sorted_records[0]["rating"] == 4.9
    assert sorted_records[0]["heat"] == 96
    assert sorted_records[1]["rating"] == 4.8

    print("test_sort_by_rating_then_heat passed.")


def test_top_k_heat():
    records = SAMPLE_RECORDS[:]
    result = top_k(records, field="heat", k=3, order="desc")

    assert len(result) == 3
    assert result[0]["name"] == "百周年纪念广场"
    assert result[1]["name"] == "图书馆"
    assert result[2]["name"] == "第一教学楼"

    print("test_top_k_heat passed.")


def test_top_k_rating():
    records = SAMPLE_RECORDS[:]
    result = top_k(records, field="rating", k=5, order="desc")

    assert len(result) == len(records)
    assert result[0]["rating"] >= result[1]["rating"] >= result[2]["rating"]
    assert result[-1]["rating"] >= 4.5

    print("test_top_k_rating passed.")


def test_recommend_top_k_by_distance():
    records = [
        {"name": "远处景点", "distance_m": 450, "heat": 99, "rating": 4.9},
        {"name": "近处景点", "distance_m": 120, "heat": 80, "rating": 4.5},
        {"name": "中间景点", "distance_m": 250, "heat": 90, "rating": 4.7},
        {"name": "未知距离景点", "distance_m": None, "heat": 100, "rating": 5.0},
    ]

    result = recommend_top_k(records, sort_field="distance_m", limit=3)

    assert [item["name"] for item in result] == ["近处景点", "中间景点", "远处景点"]
    assert all("_distance_rank" not in item for item in result)
    print("test_recommend_top_k_by_distance passed.")


def test_recommend_top_k_heat_uses_distance_tiebreaker():
    records = [
        {"name": "同热度较远", "heat": 90, "rating": 4.8, "distance_m": 300},
        {"name": "同热度较近", "heat": 90, "rating": 4.8, "distance_m": 100},
        {"name": "低热度", "heat": 80, "rating": 5.0, "distance_m": 20},
    ]

    result = recommend_top_k(records, sort_field="heat", limit=2)

    assert [item["name"] for item in result] == ["同热度较近", "同热度较远"]
    print("test_recommend_top_k_heat_uses_distance_tiebreaker passed.")


def run_all_tests():
    print("Running recommend module tests...")
    test_sort_by_heat()
    test_sort_by_rating_then_heat()
    test_top_k_heat()
    test_top_k_rating()
    test_recommend_top_k_by_distance()
    test_recommend_top_k_heat_uses_distance_tiebreaker()
    print("All recommend tests passed.")


if __name__ == "__main__":
    run_all_tests()
