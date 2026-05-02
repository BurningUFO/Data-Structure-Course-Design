"""
第九周新增：集成测试

覆盖第九周关键链路，验证三模块协作：
  查询 -> 推荐 -> 距离计算 -> 路径规划

测试场景：
1. 主链路：从 gate_north 出发，查询"图书馆"展示距离排序和路径规划结果
2. 场所查询链路：查询洗手间/便利店/食堂，展示真实路径距离排序
3. 完整端到端链路：查询→推荐→路径规划
4. 跨层路径：室外到图书馆室内
5. 多目标路径：访问多个地点
6. 日记查询链路
7. 日记查询 + 路径规划结合

使用说明：
  python -B tests/test_integration.py
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graph.loader import GraphLoader
from src.routing.router import Router
from src.search.search_service import search_and_recommend, load_site_records
from src.search.response import build_success_response, build_error_response
from src.search.distance_adapter import RouterDistanceAdapter
from src.diary.diary_service import search_diaries


class IntegrationTests:
    """第九周期中检查集成测试"""

    def __init__(self):
        self.graph = None
        self.router = None
        self.passed = 0
        self.failed = 0
        self.errors = []

    # ──────────────────── 基础模块验证 ────────────────────

    def test_01_graph_loader_works(self):
        """验证标准 PKU 分层图成功加载"""
        self.graph = GraphLoader.load_site_graph("PKU")
        assert self.graph is not None, "图加载失败"
        assert getattr(self.graph, "site_id", None) == "PKU"
        assert "library" in self.graph.nodes
        assert "dormitory_1" in self.graph.nodes
        assert "dorm1_entrance" in self.graph.nodes, "indoor_DORM1 未加载"
        assert "lib_entrance" in self.graph.nodes
        print(f"  ✓  标准 PKU 分层图加载成功：{len(self.graph.nodes)} 节点")
        return True

    def test_02_router_works(self):
        """验证路由器创建成功"""
        assert self.graph is not None
        self.router = Router(self.graph)
        assert self.router is not None
        print("  ✓  Router 创建成功")
        return True

    # ──────────────────── 路径规划链路 ────────────────────

    def test_03_single_target_routing(self):
        """单目标路径规划：gate_north -> library"""
        result = self.router.query_routing("gate_north", "library")
        assert result["success"] is True
        assert len(result["path"]) >= 2
        assert result["path"][0] == "gate_north"
        assert result["path"][-1] == "library"
        assert result["total_distance_m"] > 0
        assert result["estimated_time_s"] > 0
        assert len(result["segments"]) >= 1
        print(f"  ✓  单目标路径 {result['path']}")
        print(f"      距离={result['total_distance_m']:.1f}m, 时间={result['estimated_time_s']:.1f}s")
        return True

    def test_04_cross_layer_routing(self):
        """跨层路径规划：gate_north -> lib_reading_room_1（室外→室内）"""
        result = self.router.query_routing("gate_north", "lib_reading_room_1")
        assert result["success"] is True
        assert "lib_entrance" in result["path"], "应经过图书馆入口"
        segments = result.get("segments", [])
        layers = [s["layer"] for s in segments]
        assert "outdoor" in layers
        assert "indoor_LIB" in layers
        print(f"  ✓  跨层路径 gate_north -> lib_reading_room_1")
        print(f"      路径={result['path']}")
        print(f"      分段层级={layers}")
        return True

    def test_05_multi_target_routing(self):
        """多目标路径规划"""
        result = self.router.query_multi_target(
            "gate_north",
            ["library", "canteen", "convenience_store"],
            return_to_start=True,
        )
        assert result["success"] is True
        assert len(result["visit_order"]) >= 4  # start + 3 targets + return
        assert result["visit_order"][0] == "gate_north"
        assert len(result["leg_results"]) == 4  # 三段+返回
        print(f"  ✓  多目标路径：{result['visit_order']}")
        print(f"      总距离={result['total_distance_m']:.1f}m")
        return True

    def test_06_empty_multi_target(self):
        """空目标列表多目标路径"""
        result = self.router.query_multi_target("gate_north", [])
        assert result["success"] is True
        assert result["target_node_ids"] == []
        assert result["path"] == ["gate_north"]
        print("  ✓  空目标列表路径：返回起点自身")
        return True

    def test_07_unreachable_target(self):
        """不可达目标"""
        result = self.router.query_routing("gate_north", "nonexistent_node")
        assert result["success"] is False
        assert "message" in result
        print(f"  ✓  不可达节点：{result['message']}")
        return True

    def test_08_dormitory_cross_layer(self):
        """宿舍室外->室内跨层路径：dormitory_1 -> dorm1_room_101"""
        result = self.router.query_routing("gate_north", "dorm1_room_101")
        assert result["success"] is True
        assert "dormitory_1" in result["path"]
        assert "dorm1_entrance" in result["path"]
        assert "dorm1_corridor" in result["path"]
        print(f"  ✓  宿舍跨层路径 gate_north -> dorm1_room_101")
        print(f"      路径={result['path']}")
        return True

    def test_09_distance_query(self):
        """轻量距离查询"""
        dist = self.router.query_distance("gate_north", "library")
        assert dist != float('inf')
        assert dist > 0
        print(f"  ✓  gate_north -> library 距离={dist:.1f}m")
        return True

    # ──────────────────── 查询 + 推荐链路 ────────────────────

    def test_10_search_with_distance(self):
        """场所查询 + 距离排序"""
        records = load_site_records("PKU")
        # 注入真实的距离 provider
        dist_adapter = RouterDistanceAdapter(site_id="PKU")
        distance_provider = dist_adapter.as_provider()
        result = search_and_recommend(
            keyword="洗手间",
            start_node_id="gate_north",
            sort_field="distance_m",
            records=records,
            distance_provider=distance_provider,
            use_default_distance_provider=False,
        )
        assert result["success"] is True
        if result["total"] > 0:
            for r in result["data"]:
                assert r["distance_status"] in ("available", "unreachable", "missing_node_id")
        print(f"  ✓  场所查询：关键词=洗手间, 返回={result['total']} 条")
        return True

    def test_11_catering_recommend(self):
        """美食推荐查询（类别过滤 + 热度排序）"""
        records = load_site_records("PKU")
        result = search_and_recommend(
            keyword="",
            category="catering",
            records=records,
            sort_field="heat",
        )
        assert result["success"] is True
        for r in result["data"]:
            assert r.get("category") == "catering"
        print(f"  ✓  美食推荐：返回 {result['total']} 条餐饮设施")
        return True

    def test_12_category_filter(self):
        """类别过滤查询"""
        records = load_site_records("PKU")
        result = search_and_recommend(
            keyword="",
            category="education",
            records=records,
            sort_field="heat",
        )
        assert result["success"] is True
        print(f"  ✓  类别过滤(education)：返回 {result['total']} 条")
        return True

    # ──────────────────── 日记查询链路 ────────────────────

    def test_13_diary_search_by_destination(self):
        """日记按目的地查询"""
        result = search_diaries(destination="北京大学")
        assert result["success"] is True
        assert result["total"] >= 7
        assert result["query_type"] == "diary_search"
        print(f"  ✓  日记目的地查询(北京大学)：{result['total']} 篇")
        return True

    def test_14_diary_search_by_title(self):
        """日记按标题查询"""
        result = search_diaries(keyword="黄山")
        assert result["success"] is True
        assert result["total"] == 1
        assert result["data"][0]["title"] == "五一黄山行"
        print("  ✓  日记标题查询(黄山)：1 篇")
        return True

    def test_15_diary_sort_by_rating(self):
        """日记按评分排序"""
        result = search_diaries(destination="北京大学", sort_field="rating")
        assert result["success"] is True
        ratings = [r["rating"] for r in result["data"]]
        assert ratings == sorted(ratings, reverse=True)
        print(f"  ✓  日记评分排序：第1篇={result['data'][0]['title']} 评分={result['data'][0]['rating']}")
        return True

    # ──────────────────── 完整端到端链路 ────────────────────

    def test_16_end_to_end_flow(self):
        """完整链路：场所查询 -> 推荐 -> 距离 -> 路径规划"""
        records = load_site_records("PKU")

        # Step 1: 场所查询
        search_result = search_and_recommend(
            keyword="图书馆",
            start_node_id="gate_north",
            records=records,
            sort_field="heat",
            use_default_distance_provider=False,
        )
        assert search_result["success"] is True
        assert search_result["total"] > 0

        # Step 2: 取第一个结果的 node_id，做路径规划
        first_record = search_result["data"][0]
        target_node_id = first_record.get("target_node_id") or first_record.get("node_id")
        assert target_node_id, "查询结果缺少 node_id"

        route = self.router.query_routing("gate_north", target_node_id)
        assert route["success"] is True

        print(f"  ✓  完整端到端链路验证通过")
        print(f"      查询：keyword=图书馆")
        print(f"      目标节点：{target_node_id}")
        print(f"      路径距离：{route['total_distance_m']:.1f}m")
        print(f"      路径长度：{len(route['path'])} 节点")
        return True

    def test_17_diary_to_routing_flow(self):
        """日记查询 -> 路径规划链路"""
        # Step 1: 查询北京大学相关的日记
        diary_result = search_diaries(destination="北京大学", sort_field="heat", limit=3)
        assert diary_result["success"] is True

        # Step 2: 取日记中带 destination_node_id 的
        for diary in diary_result["data"]:
            dest_node = diary.get("destination_node_id")
            if dest_node:
                route = self.router.query_routing("gate_north", dest_node)
                assert route["success"] is True
                print(f"  日记《{diary['title']}》-> 目的地节点={dest_node}")
                print(f"    路径距离={route['total_distance_m']:.1f}m")
                return True

        print("  ⚠  未找到带有 destination_node_id 的日记")
        return False

    # ──────────────────── 运行入口 ────────────────────

    def run_all(self):
        """运行所有集成测试"""
        tests = [
            self.test_01_graph_loader_works,
            self.test_02_router_works,
            self.test_03_single_target_routing,
            self.test_04_cross_layer_routing,
            self.test_05_multi_target_routing,
            self.test_06_empty_multi_target,
            self.test_07_unreachable_target,
            self.test_08_dormitory_cross_layer,
            self.test_09_distance_query,
            self.test_10_search_with_distance,
            self.test_11_catering_recommend,
            self.test_12_category_filter,
            self.test_13_diary_search_by_destination,
            self.test_14_diary_search_by_title,
            self.test_15_diary_sort_by_rating,
            self.test_16_end_to_end_flow,
            self.test_17_diary_to_routing_flow,
        ]

        print("=" * 60)
        print("第九周期中检查 — 集成测试报告")
        print("=" * 60)
        print()

        for test in tests:
            test_name = test.__name__
            try:
                test()
                self.passed += 1
                print()
            except AssertionError as e:
                self.failed += 1
                self.errors.append((test_name, str(e)))
                print(f"  ✗  [{test_name}] 失败: {e}")
                print()
            except Exception as e:
                self.failed += 1
                self.errors.append((test_name, f"{type(e).__name__}: {e}"))
                print(f"  ✗  [{test_name}] 异常: {type(e).__name__}: {e}")
                print()

        print("=" * 60)
        print(f"测试结果：{self.passed} 通过，{self.failed} 失败，共 {self.passed + self.failed} 项")
        if self.errors:
            print("-" * 40)
            print("失败详情：")
            for name, msg in self.errors:
                print(f"  [{name}] {msg}")
        print("=" * 60)

        return self.failed == 0


if __name__ == "__main__":
    suite = IntegrationTests()
    success = suite.run_all()
    sys.exit(0 if success else 1)
