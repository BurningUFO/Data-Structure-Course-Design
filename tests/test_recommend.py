import os
import sys

# 将项目根目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.recommend.ranking import recommend_top_k
from src.recommend.catering_service import recommend_catering
from src.recommend.interest import rank_interest_aware_records
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


def test_recommend_catering_top_k():
    response = recommend_catering(limit=2, sort_field="heat")

    assert response["success"] is True
    assert response["query_type"] == "catering_recommend"
    assert response["total"] == 2
    assert all(item["category"] == "catering" for item in response["data"])
    print("test_recommend_catering_top_k passed.")


def test_recommend_catering_defaults_to_top_ten():
    records = [
        {
            "id": f"food_{index:03d}",
            "name": f"餐饮 {index}",
            "category": "catering",
            "heat": 200 - index,
            "rating": 4.0 + ((11 - index) * 0.01),
            "node_id": f"food_node_{index}",
        }
        for index in range(12)
    ]

    response = recommend_catering(records=records, sort_field="heat")

    assert response["success"] is True
    assert response["filters"]["limit"] == 10
    assert response["total"] == 10
    assert len(response["data"]) == 10
    assert response["data"][0]["name"] == "餐饮 0"
    assert response["data"][-1]["name"] == "餐饮 9"
    print("test_recommend_catering_defaults_to_top_ten passed.")


def test_recommend_catering_distance_sort():
    response = recommend_catering(
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=2,
    )

    assert response["success"] is True
    distances = [
        item["distance_m"]
        for item in response["data"]
        if item.get("distance_status") == "available"
    ]
    assert distances == sorted(distances)
    assert response["metadata"]["distance"]["available_count"] == 2
    assert response["metadata"]["distance"]["status_counts"]["available"] == 2
    assert all(item["distance_status"] == "available" for item in response["data"])
    assert response["data"][0]["target_node_id"]
    assert response["data"][0]["distance_m"] == distances[0]
    print("test_recommend_catering_distance_sort passed.")


def test_recommend_catering_optional_cuisine_filter():
    records = [
        {
            "id": "food_001",
            "name": "图书馆咖啡角",
            "category": "catering",
            "heat": 90,
            "rating": 4.8,
            "tags": ["咖啡", "轻食"],
            "keywords": ["咖啡"],
            "description": "提供拿铁和三明治。",
            "cuisine": "咖啡",
            "node_id": "lib_cafe",
        },
        {
            "id": "food_002",
            "name": "农园食堂",
            "category": "catering",
            "heat": 88,
            "rating": 4.7,
            "tags": ["食堂", "套餐"],
            "keywords": ["主食"],
            "description": "提供多种家常菜。",
            "node_id": "canteen",
        },
    ]

    response = recommend_catering(
        cuisine="咖啡",
        records=records,
        sort_field="heat",
        limit=5,
    )

    assert response["success"] is True
    assert [item["name"] for item in response["data"]] == ["图书馆咖啡角"]
    print("test_recommend_catering_optional_cuisine_filter passed.")


def test_recommend_catering_keyword_sort_uses_user_field_first():
    records = [
        {
            "id": "food_low_rating",
            "name": "餐饮综合楼（家园食堂）",
            "category": "catering",
            "heat": 99,
            "rating": 4.2,
            "tags": ["食堂"],
            "keywords": ["食堂"],
            "node_id": "jiayuan",
        },
        {
            "id": "food_high_rating",
            "name": "北大青鸟总部食堂",
            "category": "catering",
            "heat": 80,
            "rating": 4.8,
            "tags": ["食堂"],
            "keywords": ["食堂"],
            "node_id": "qingniao",
        },
        {
            "id": "food_mid_rating",
            "name": "农园食堂",
            "category": "catering",
            "heat": 90,
            "rating": 4.5,
            "tags": ["食堂"],
            "keywords": ["食堂"],
            "node_id": "nongyuan",
        },
    ]

    response = recommend_catering(
        keyword="食堂",
        records=records,
        sort_field="rating",
        limit=3,
    )

    assert response["success"] is True
    assert [item["rating"] for item in response["data"]] == [4.8, 4.5, 4.2]
    assert response["data"][0]["_match_score"] > 0
    print("test_recommend_catering_keyword_sort_uses_user_field_first passed.")


def test_recommend_catering_keyword_keeps_direct_food_intent():
    def distance_provider(start_node_id, target_node_id, strategy):
        distances = {
            "near_coffee": 20.0,
            "generic_cafe": 30.0,
            "real_canteen": 200.0,
        }
        return distances[target_node_id]

    records = [
        {
            "id": "near_coffee",
            "name": "图书馆咖啡服务点",
            "category": "catering",
            "heat": 80,
            "rating": 4.5,
            "tags": ["咖啡", "餐饮"],
            "keywords": ["咖啡", "餐饮", "catering"],
            "description": "作为非食堂餐饮推荐的补充样例。",
            "node_id": "near_coffee",
        },
        {
            "id": "generic_cafe",
            "name": "图书馆咖啡厅",
            "category": "catering",
            "heat": 78,
            "rating": 4.6,
            "tags": ["咖啡", "轻食"],
            "keywords": ["咖啡", "catering"],
            "node_id": "generic_cafe",
        },
        {
            "id": "real_canteen",
            "name": "德智园学生食堂",
            "category": "catering",
            "heat": 88,
            "rating": 4.7,
            "tags": ["食堂"],
            "keywords": ["学生食堂", "餐饮"],
            "node_id": "real_canteen",
        },
    ]

    response = recommend_catering(
        keyword="食堂",
        records=records,
        start_node_id="gate",
        sort_field="distance_m",
        distance_provider=distance_provider,
        use_default_distance_provider=False,
        limit=3,
    )

    assert response["success"] is True
    assert [item["id"] for item in response["data"]] == ["real_canteen"]
    assert "食堂" in response["data"][0]["cuisine_labels"]
    assert "食堂" not in [
        label
        for record in records[:2]
        for label in recommend_catering(records=[record], limit=1)["data"][0]["cuisine_labels"]
    ]
    print("test_recommend_catering_keyword_keeps_direct_food_intent passed.")


def test_recommend_catering_center_node_controls_distance_origin():
    calls = []

    def distance_provider(start_node_id, target_node_id, strategy):
        calls.append((start_node_id, target_node_id, strategy))
        distances = {
            ("library", "near_cafe"): 80.0,
            ("library", "far_canteen"): 320.0,
            ("gate_north", "near_cafe"): 500.0,
            ("gate_north", "far_canteen"): 100.0,
        }
        return distances[(start_node_id, target_node_id)]

    records = [
        {
            "id": "near_cafe",
            "name": "图书馆咖啡厅",
            "category": "catering",
            "heat": 80,
            "rating": 4.6,
            "tags": ["咖啡"],
            "node_id": "near_cafe",
        },
        {
            "id": "far_canteen",
            "name": "远处食堂",
            "category": "catering",
            "heat": 90,
            "rating": 4.8,
            "tags": ["食堂"],
            "node_id": "far_canteen",
        },
    ]

    response = recommend_catering(
        records=records,
        start_node_id="gate_north",
        center_node_id="library",
        sort_field="distance_m",
        distance_provider=distance_provider,
        use_default_distance_provider=False,
        limit=2,
    )

    assert response["success"] is True
    assert [item["id"] for item in response["data"]] == ["near_cafe", "far_canteen"]
    assert response["filters"]["distance_origin_node_id"] == "library"
    assert response["metadata"]["business"]["distance_basis"] == "selected_center"
    assert all(call[0] == "library" for call in calls)
    print("test_recommend_catering_center_node_controls_distance_origin passed.")


def test_recommend_catering_infers_cuisine_labels():
    response = recommend_catering(
        cuisine="咖啡",
        records=[
            {
                "id": "coffee",
                "name": "泊星地咖啡馆",
                "category": "catering",
                "heat": 80,
                "rating": 4.5,
                "tags": ["amenity:cafe"],
                "node_id": "coffee",
            },
            {
                "id": "canteen",
                "name": "普通食堂",
                "category": "catering",
                "heat": 90,
                "rating": 4.4,
                "tags": ["食堂"],
                "node_id": "canteen",
            },
        ],
        sort_field="heat",
        limit=5,
    )

    assert response["success"] is True
    assert [item["id"] for item in response["data"]] == ["coffee"]
    assert "咖啡" in response["data"][0]["cuisine_labels"]
    print("test_recommend_catering_infers_cuisine_labels passed.")


def test_interest_aware_ranking_uses_interest_heat_rating_and_distance():
    records = [
        {
            "id": "library",
            "name": "图书馆",
            "category": "education",
            "heat": 80,
            "rating": 4.5,
            "distance_m": 300,
            "tags": ["图书馆", "自习"],
            "description": "安静学习空间。",
        },
        {
            "id": "canteen",
            "name": "农园食堂",
            "category": "catering",
            "heat": 95,
            "rating": 4.9,
            "distance_m": 80,
            "tags": ["食堂", "美食"],
            "description": "校园餐饮。",
        },
        {
            "id": "sports",
            "name": "五四体育场",
            "category": "sports",
            "heat": 90,
            "rating": 4.8,
            "distance_m": 60,
            "tags": ["运动", "跑步"],
            "description": "适合锻炼。",
        },
    ]

    study_result = rank_interest_aware_records(
        records,
        interests=["图书馆", "学习"],
        limit=3,
    )
    food_result = rank_interest_aware_records(
        records,
        interests=["美食", "食堂"],
        limit=3,
    )

    assert study_result[0]["id"] == "library"
    assert food_result[0]["id"] == "canteen"
    assert study_result[0]["interest_match_score"] > 0
    assert food_result[0]["interest_match_score"] > 0
    assert study_result[0]["recommendation_components"]["weights"]["distance_m"] == 0.1
    assert "兴趣命中" in study_result[0]["interest_reason"]
    print("test_interest_aware_ranking_uses_interest_heat_rating_and_distance passed.")


def run_all_tests():
    print("Running recommend module tests...")
    test_sort_by_heat()
    test_sort_by_rating_then_heat()
    test_top_k_heat()
    test_top_k_rating()
    test_recommend_top_k_by_distance()
    test_recommend_top_k_heat_uses_distance_tiebreaker()
    test_recommend_catering_top_k()
    test_recommend_catering_defaults_to_top_ten()
    test_recommend_catering_distance_sort()
    test_recommend_catering_optional_cuisine_filter()
    test_recommend_catering_keyword_sort_uses_user_field_first()
    test_recommend_catering_keyword_keeps_direct_food_intent()
    test_recommend_catering_center_node_controls_distance_origin()
    test_recommend_catering_infers_cuisine_labels()
    test_interest_aware_ranking_uses_interest_heat_rating_and_distance()
    print("All recommend tests passed.")


if __name__ == "__main__":
    run_all_tests()
