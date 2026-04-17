"""
成员 B：统一业务响应结构

本模块用于统一查询 / 推荐接口的输出格式，
方便后续：

- CLI 展示
- 测试校验
- 和成员 C 做联调
"""

from __future__ import annotations

from typing import Any


def build_success_response(
    *,
    data: list[dict[str, Any]],
    message: str = "query success",
    query_type: str = "query",
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "query_type": query_type,
        "filters": filters or {},
        "total": len(data),
        "data": data,
    }


def build_error_response(
    message: str,
    *,
    query_type: str = "query",
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "query_type": query_type,
        "filters": filters or {},
        "total": 0,
        "data": [],
    }
