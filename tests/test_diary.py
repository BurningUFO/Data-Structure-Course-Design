"""
第九周新增：日记模块基础查询测试

测试覆盖：
- DiaryService 基本加载
- 按标题精确查询 / 模糊查询
- 按目的地查询
- 按热度 / 评分排序
- 通用 search 入口
- 边界情况：空查询、不存在关键词
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.diary.diary_service import DiaryService, load_diary_records, search_diaries  # noqa: E402


class TestDiaryService:
    """日记查询服务测试集"""

    @classmethod
    def setup_class(cls):
        cls.service = DiaryService()

    def test_load_records(self):
        """测试日记数据加载"""
        assert len(self.service.records) > 0, "至少应加载 12 篇日记数据"
        assert self.service.records[0]["id"] == "diary_001"
        assert self.service.records[0]["title"] == "秋日燕园游记"

    def test_search_by_title_exact(self):
        """测试标题精确匹配"""
        result = self.service.search_by_title_exact("黄山行")
        assert len(result) == 0, "标题精确匹配应区分大小写"

        result = self.service.search_by_title_exact("五一黄山行")
        assert len(result) == 1
        assert result[0]["id"] == "diary_004"

    def test_search_by_title_fuzzy(self):
        """测试标题模糊匹配"""
        result = self.service.search_by_title("黄山", match_mode="fuzzy")
        assert len(result) == 1
        assert "黄山" in result[0]["title"]

        # 多个匹配
        result = self.service.search_by_title("美食", match_mode="fuzzy")
        assert len(result) >= 1

    def test_search_by_title_empty(self):
        """测试空标题"""
        assert self.service.search_by_title("") == []
        assert self.service.search_by_title_exact("") == []

    def test_search_by_destination_fuzzy(self):
        """测试按目的地模糊查询"""
        result = self.service.search_by_destination("北京大学")
        assert len(result) == 7, "应有 7 篇北京大学相关日记"

    def test_search_by_destination_exact(self):
        """测试按目的地精确查询"""
        result = self.service.search_by_destination("北京大学", match_mode="exact")
        assert len(result) == 7

        result = self.service.search_by_destination("黄山", match_mode="exact")
        assert len(result) == 0, "黄山风景区不等于黄山"

    def test_search_by_destination_empty(self):
        """测试空目的地"""
        assert self.service.search_by_destination("") == []

    def test_search_general_success(self):
        """测试通用 search 入口：正常查询"""
        result = search_diaries(destination="北京大学")
        assert result["success"] is True
        assert result["query_type"] == "diary_search"
        assert result["total"] == 7
        assert result["message"] == "diary query success"

    def test_search_no_match(self):
        """测试通用 search 入口：未匹配"""
        result = search_diaries(keyword="不存在的日记")
        assert result["success"] is True
        assert result["total"] == 0
        assert result["message"] == "no matched diaries"

    def test_search_sort_by_heat(self):
        """测试按热度降序排序"""
        result = search_diaries(destination="北京大学", sort_field="heat")
        heats = [r["heat"] for r in result["data"]]
        assert heats == sorted(heats, reverse=True), "热度应降序排列"

    def test_search_sort_by_rating(self):
        """测试按评分降序排序"""
        result = search_diaries(destination="北京大学", sort_field="rating")
        ratings = [r["rating"] for r in result["data"]]
        assert ratings == sorted(ratings, reverse=True), "评分应降序排列"

    def test_search_sort_by_views(self):
        """测试按浏览量排序"""
        result = search_diaries(destination="北京", sort_field="views")
        views = [r["views"] for r in result["data"]]
        assert views == sorted(views, reverse=True), "浏览量应降序排列"

    def test_search_limit(self):
        """测试 limit 限制"""
        result = search_diaries(destination="北京大学", limit=3)
        assert result["total"] == 3

    def test_load_from_custom_path(self):
        """测试从自定义路径加载"""
        data_path = os.path.join(os.path.dirname(__file__), "../data/diary_data.json")
        records = load_diary_records(data_path)
        assert len(records) == 12

    def test_service_reload(self):
        """测试重新加载数据"""
        service = DiaryService()
        original_count = len(service.records)
        service.reload()
        assert len(service.records) == original_count


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
