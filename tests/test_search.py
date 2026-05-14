import os
import sys
from contextlib import redirect_stdout
from io import StringIO

# 将项目根目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.search.cli_demo import print_response, query_and_recommend
from src.search.distance_adapter import build_distance_provider
from src.search.exact_search import (
    filter_by_category,
    filter_by_keyword,
    filter_by_name,
    search_records,
)
from src.search.fuzzy_search import fuzzy_search
from src.search.response import build_error_response, build_success_response
from src.search.search_service import (
    attach_distance_fields,
    count_distance_status,
    load_scenic_spots,
    search_places,
    search_and_recommend,
)


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


def test_fuzzy_search_matches_name_tags_and_description():
    records = [
        {
            "id": "svc_001",
            "name": "热水房",
            "category": "service",
            "heat": 70,
            "rating": 4.2,
            "tags": ["生活服务"],
            "keywords": ["宿舍热水"],
            "description": "提供热水和开水。",
        },
        {
            "id": "svc_002",
            "name": "宿舍服务台",
            "category": "service",
            "heat": 88,
            "rating": 4.7,
            "tags": ["热水报修"],
            "keywords": ["生活服务"],
            "description": "可办理热水卡和宿舍报修。",
        },
        {
            "id": "svc_003",
            "name": "公共活动室",
            "category": "service",
            "heat": 95,
            "rating": 4.9,
            "tags": ["休闲"],
            "keywords": ["活动"],
            "description": "靠近热水房，适合休息。",
        },
    ]

    result = fuzzy_search(records, "热水")

    assert [item["id"] for item in result] == ["svc_001", "svc_002", "svc_003"]
    print("test_fuzzy_search_matches_name_tags_and_description passed.")


def test_fuzzy_search_supports_synonyms_and_initials():
    records = [
        {
            "id": "svc_010",
            "name": "校园洗手间",
            "category": "restroom",
            "heat": 60,
            "rating": 4.1,
            "tags": ["公共服务"],
            "keywords": ["卫生间"],
            "description": "位于体育场旁边。",
        },
        {
            "id": "svc_011",
            "name": "图书馆",
            "category": "education",
            "heat": 98,
            "rating": 4.9,
            "tags": ["学习"],
            "keywords": ["阅览室"],
            "description": "适合自习。",
        },
    ]

    synonym_result = fuzzy_search(records, "厕所")
    initial_result = fuzzy_search(records, "tsg")

    assert synonym_result[0]["id"] == "svc_010"
    assert initial_result[0]["id"] == "svc_011"
    print("test_fuzzy_search_supports_synonyms_and_initials passed.")


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
    assert "metadata" in success
    assert success["results"] == success["data"]
    assert error["success"] is False
    assert error["total"] == 0
    assert "metadata" in error
    assert error["results"] == error["data"]
    print("test_response_builder passed.")


def test_query_and_recommend_flow():
    response = query_and_recommend(
        keyword="图书馆",
        category="",
        match_mode="fuzzy",
        sort_field="heat",
        limit=3,
    )

    assert response["success"] is True
    assert response["query_type"] == "scenic_search"
    assert response["total"] >= 1
    assert response["data"][0]["name"] == "图书馆"
    assert response["data"][0]["node_id"] == "library"
    print("test_query_and_recommend_flow passed.")


def test_cli_wrapper_distance_response_and_print():
    response = query_and_recommend(
        keyword="图书馆",
        start_node_id="gate_north",
        sort_field="distance_m",
        records=[
            {
                "id": "campus_poi_001",
                "name": "图书馆",
                "category": "建筑",
                "heat": 80,
                "rating": 4.8,
                "tags": ["学习"],
                "keywords": ["图书馆"],
                "description": "适合学习和借阅图书。",
                "node_id": "library",
            }
        ],
        limit=1,
    )

    output_buffer = StringIO()
    with redirect_stdout(output_buffer):
        print_response(response)

    output = output_buffer.getvalue()

    assert response["success"] is True
    assert response["metadata"]["ranking"]["sort_field"] == "distance_m"
    assert response["data"][0]["distance_status"] == "available"
    assert response["data"][0]["distance_m"] > 0
    assert "Unified Response" in output
    assert "metadata:" in output
    assert "distance=" in output
    print("test_cli_wrapper_distance_response_and_print passed.")


def test_default_site_data_load():
    records = load_scenic_spots()

    assert len(records) >= 20
    assert any(record.get("name") == "图书馆" for record in records)
    assert any(record.get("name") == "中文社科阅览室" for record in records)
    print("test_default_site_data_load passed.")


def test_default_site_data_query_flow():
    response = search_and_recommend(
        keyword="图书馆",
        category="education",
        match_mode="fuzzy",
        sort_field="heat",
        limit=5,
    )

    assert response["success"] is True
    assert response["query_type"] == "scenic_search"
    assert response["total"] >= 1
    assert response["data"][0]["name"] == "图书馆"
    assert response["data"][0]["node_id"] == "library"
    print("test_default_site_data_query_flow passed.")


def test_search_places_distance_sort():
    response = search_places(
        keyword="",
        category="restroom",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=3,
    )

    assert response["success"] is True
    assert response["query_type"] == "place_search"
    assert response["metadata"]["business"]["scope"] == "facility_place"
    assert all(item["category"] == "restroom" for item in response["data"])
    available_distances = [item["distance_m"] for item in response["data"] if item.get("distance_status") == "available"]
    assert available_distances == sorted(available_distances)
    assert response["metadata"]["distance"]["available_count"] == 3
    assert response["data"][0]["distance_status"] == "available"
    print("test_search_places_distance_sort passed.")


def test_search_places_keyword_only_scope():
    response = search_places(
        keyword="便利店",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=3,
    )

    assert response["success"] is True
    assert response["query_type"] == "place_search"
    assert response["data"][0]["name"] == "中关新园超市"
    assert response["data"][0]["category"] == "shopping"
    print("test_search_places_keyword_only_scope passed.")


def test_distance_adapter_uses_member_a_router():
    provider = build_distance_provider()
    distance = provider("gate_north", "library", "shortest_distance")

    assert distance > 0
    print("test_distance_adapter_uses_member_a_router passed.")


def test_search_service_distance_integration():
    records = [
        {
            "id": "campus_poi_001",
            "name": "图书馆",
            "category": "建筑",
            "heat": 80,
            "rating": 4.8,
            "tags": ["学习"],
            "keywords": ["图书馆"],
            "description": "适合学习和借阅图书。",
            "node_id": "library",
        }
    ]

    response = search_and_recommend(
        keyword="图书馆",
        start_node_id="gate_north",
        sort_field="distance_m",
        records=records,
        limit=1,
    )

    assert response["success"] is True
    assert response["data"][0]["distance_status"] == "available"
    assert response["data"][0]["distance_m"] > 0
    assert response["data"][0]["target_node_id"] == "library"
    assert response["metadata"]["ranking"]["sort_field"] == "distance_m"
    assert response["metadata"]["ranking"]["distance_used_for_ranking"] is True
    assert response["metadata"]["distance"]["requested"] is True
    assert response["metadata"]["distance"]["provider_active"] is True
    assert response["metadata"]["distance"]["unit"] == "meter"
    assert response["metadata"]["distance"]["available_count"] == 1
    assert response["metadata"]["distance"]["status_counts"]["available"] == 1
    print("test_search_service_distance_integration passed.")


def test_missing_node_id_distance_status():
    records = [
        {
            "id": "poi_without_node",
            "name": "故宫博物院",
            "category": "历史文化景区",
            "heat": 99,
            "rating": 4.9,
            "tags": ["世界遗产"],
            "keywords": ["故宫"],
            "description": "景点数据缺少图节点 ID。",
        }
    ]

    result = attach_distance_fields(
        records,
        start_node_id="gate_north",
        distance_provider=build_distance_provider(),
    )

    assert result[0]["distance_status"] == "missing_node_id"
    assert result[0]["distance_m"] is None
    print("test_missing_node_id_distance_status passed.")


def test_member_c_real_data_missing_node_id_metadata():
    response = search_and_recommend(
        keyword="故宫",
        category="历史文化景区",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=5,
        prefer_member_c_data=True,
    )

    assert response["success"] is True
    assert response["total"] == 1
    assert response["data"][0]["distance_status"] == "missing_node_id"
    assert response["data"][0]["distance_m"] is None
    assert response["metadata"]["distance"]["requested"] is True
    assert response["metadata"]["distance"]["provider_active"] is True
    assert response["metadata"]["distance"]["status_counts"]["missing_node_id"] == 1
    print("test_member_c_real_data_missing_node_id_metadata passed.")


def test_member_c_real_data_pku_distance_available_in_m14_graph():
    response = search_and_recommend(
        keyword="图书馆",
        category="校园建筑",
        start_node_id="gate_north",
        sort_field="distance_m",
        limit=5,
        prefer_member_c_data=True,
    )

    assert response["success"] is True
    assert response["total"] == 1
    assert response["data"][0]["id"] == "pku_001"
    assert response["data"][0]["map_node_id"] == "library"
    assert response["data"][0]["distance_status"] == "available"
    assert response["data"][0]["distance_m"] > 0
    assert response["metadata"]["distance"]["status_counts"]["available"] == 1
    print("test_member_c_real_data_pku_distance_available_in_m14_graph passed.")


def test_distance_provider_disabled_status():
    records = [
        {
            "id": "campus_poi_002",
            "name": "第一教学楼",
            "category": "建筑",
            "heat": 70,
            "rating": 4.5,
            "tags": ["教学"],
            "keywords": ["教学楼"],
            "description": "教学区域。",
            "node_id": "node_003",
        }
    ]

    response = search_and_recommend(
        keyword="教学楼",
        start_node_id="gate_north",
        records=records,
        use_default_distance_provider=False,
    )

    assert response["success"] is True
    assert response["data"][0]["distance_status"] == "distance_provider_missing"
    assert response["metadata"]["distance"]["provider_active"] is False
    assert response["metadata"]["distance"]["status_counts"]["distance_provider_missing"] == 1
    print("test_distance_provider_disabled_status passed.")


def test_unreachable_distance_status():
    def unreachable_provider(start_node_id, target_node_id, strategy):
        return float("inf")

    records = [
        {
            "id": "campus_poi_003",
            "name": "不可达地点",
            "category": "建筑",
            "heat": 50,
            "rating": 4.0,
            "tags": ["测试"],
            "keywords": ["不可达"],
            "description": "用于测试不可达距离。",
            "node_id": "isolated_node",
        }
    ]

    response = search_and_recommend(
        keyword="不可达",
        start_node_id="gate_north",
        records=records,
        distance_provider=unreachable_provider,
    )

    assert response["success"] is True
    assert response["data"][0]["distance_status"] == "unreachable"
    assert response["data"][0]["distance_m"] is None
    assert response["metadata"]["distance"]["status_counts"]["unreachable"] == 1
    print("test_unreachable_distance_status passed.")


def test_distance_provider_error_status():
    def error_provider(start_node_id, target_node_id, strategy):
        return "invalid-distance"

    records = [
        {
            "id": "campus_poi_004",
            "name": "异常距离地点",
            "category": "建筑",
            "heat": 55,
            "rating": 4.1,
            "tags": ["测试"],
            "keywords": ["异常距离"],
            "description": "用于测试距离接口异常值。",
            "node_id": "node_002",
        }
    ]

    response = search_and_recommend(
        keyword="异常距离",
        start_node_id="gate_north",
        records=records,
        distance_provider=error_provider,
    )

    assert response["success"] is True
    assert response["data"][0]["distance_status"] == "distance_error"
    assert response["data"][0]["distance_m"] is None
    assert response["metadata"]["distance"]["status_counts"]["distance_error"] == 1
    print("test_distance_provider_error_status passed.")


def test_distance_status_counter():
    records = [
        {"distance_status": "available"},
        {"distance_status": "available"},
        {"distance_status": "missing_node_id"},
        {},
    ]

    counts = count_distance_status(records)

    assert counts["available"] == 2
    assert counts["missing_node_id"] == 1
    assert counts["not_requested"] == 1
    print("test_distance_status_counter passed.")


def run_all_tests():
    print("Running search module tests...")
    test_exact_name_search()
    test_category_filter()
    test_keyword_filter()
    test_combined_search()
    test_fuzzy_search()
    test_fuzzy_search_matches_name_tags_and_description()
    test_fuzzy_search_supports_synonyms_and_initials()
    test_response_builder()
    test_query_and_recommend_flow()
    test_cli_wrapper_distance_response_and_print()
    test_default_site_data_load()
    test_default_site_data_query_flow()
    test_search_places_distance_sort()
    test_search_places_keyword_only_scope()
    test_distance_adapter_uses_member_a_router()
    test_search_service_distance_integration()
    test_missing_node_id_distance_status()
    test_member_c_real_data_missing_node_id_metadata()
    test_member_c_real_data_pku_distance_available_in_m14_graph()
    test_distance_provider_disabled_status()
    test_unreachable_distance_status()
    test_distance_provider_error_status()
    test_distance_status_counter()
    print("All search tests passed.")


if __name__ == "__main__":
    run_all_tests()
