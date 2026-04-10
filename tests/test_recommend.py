import json
import os
import sys

# 将项目根目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.recommend.sorter import sort_records
from src.recommend.topk import top_k


def load_scenic_spots():
    base_path = os.path.dirname(__file__)
    data_file = os.path.join(base_path, "../data/scenic_spots.json")

    print(f"Loading scenic spots from {data_file}...")

    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_sort_by_heat():
    records = load_scenic_spots()
    sorted_records = sort_records(
        records,
        [{"field": "heat", "order": "desc"}],
    )

    assert len(sorted_records) == len(records)
    assert sorted_records[0]["name"] == "黄山风景区"
    assert sorted_records[0]["heat"] == 97
    assert sorted_records[-1]["heat"] == 87

    print("test_sort_by_heat passed.")


def test_sort_by_rating_then_heat():
    records = load_scenic_spots()
    sorted_records = sort_records(
        records,
        [
            {"field": "rating", "order": "desc"},
            {"field": "heat", "order": "desc"},
        ],
    )

    assert len(sorted_records) == len(records)
    assert sorted_records[0]["rating"] == 4.9
    assert sorted_records[0]["heat"] == 97
    assert sorted_records[1]["rating"] == 4.9

    print("test_sort_by_rating_then_heat passed.")


def test_top_k_heat():
    records = load_scenic_spots()
    result = top_k(records, field="heat", k=3, order="desc")

    assert len(result) == 3
    assert result[0]["name"] == "黄山风景区"
    assert result[1]["name"] == "九寨沟风景区"
    assert result[2]["name"] == "张家界国家森林公园"

    print("test_top_k_heat passed.")


def test_top_k_rating():
    records = load_scenic_spots()
    result = top_k(records, field="rating", k=5, order="desc")

    assert len(result) == 5
    assert result[0]["rating"] >= result[1]["rating"] >= result[2]["rating"]
    assert result[-1]["rating"] >= 4.7

    print("test_top_k_rating passed.")


def run_all_tests():
    print("Running recommend module tests...")
    test_sort_by_heat()
    test_sort_by_rating_then_heat()
    test_top_k_heat()
    test_top_k_rating()
    print("All recommend tests passed.")


if __name__ == "__main__":
    run_all_tests()
