"""
成员 B：Top-K 核心模块

本模块基于“小顶堆（Min-Heap）”实现 Top-K 选择，
用于景点推荐、美食推荐、日记推荐等场景。

设计目标：
- 不经过全量完全排序选出前 K 个结果
- 支持按任意数值字段取 Top-K
- 支持升序 / 降序语义下的“前 K 个”

复杂度说明：
- 对 n 条记录取前 k 条，整体时间复杂度为 O(n log k)
- 额外空间复杂度为 O(k)

说明：
- 这里不直接调用现成堆排序函数来完成核心逻辑
- 使用自定义 Min-Heap，体现数据结构实现过程
"""

from __future__ import annotations

from typing import Any


class MinHeap:
    """简单小顶堆，堆顶始终是当前最小元素。"""

    def __init__(self) -> None:
        self.data: list[tuple[float, int, dict[str, Any]]] = []

    def __len__(self) -> int:
        return len(self.data)

    def peek(self) -> tuple[float, int, dict[str, Any]] | None:
        if not self.data:
            return None
        return self.data[0]

    def push(self, item: tuple[float, int, dict[str, Any]]) -> None:
        self.data.append(item)
        self._shift_up(len(self.data) - 1)

    def pop(self) -> tuple[float, int, dict[str, Any]] | None:
        if not self.data:
            return None
        if len(self.data) == 1:
            return self.data.pop()

        top = self.data[0]
        self.data[0] = self.data.pop()
        self._shift_down(0)
        return top

    def replace_top(self, item: tuple[float, int, dict[str, Any]]) -> None:
        if not self.data:
            self.push(item)
            return
        self.data[0] = item
        self._shift_down(0)

    def _shift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self.data[parent][0] <= self.data[index][0]:
                break
            self.data[parent], self.data[index] = self.data[index], self.data[parent]
            index = parent

    def _shift_down(self, index: int) -> None:
        size = len(self.data)
        while True:
            left = index * 2 + 1
            right = index * 2 + 2
            smallest = index

            if left < size and self.data[left][0] < self.data[smallest][0]:
                smallest = left
            if right < size and self.data[right][0] < self.data[smallest][0]:
                smallest = right

            if smallest == index:
                break

            self.data[index], self.data[smallest] = (
                self.data[smallest],
                self.data[index],
            )
            index = smallest


def get_numeric_value(record: dict[str, Any], field: str) -> float:
    """读取记录中的数值字段，不存在时按 0.0 处理。"""
    value = record.get(field, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def top_k(
    records: list[dict[str, Any]],
    field: str,
    k: int,
    order: str = "desc",
) -> list[dict[str, Any]]:
    """
    基于小顶堆返回前 K 个结果。

    参数：
    - records: 原始记录列表
    - field: 参与 Top-K 的字段，如 heat / rating
    - k: 需要返回的个数
    - order: "desc" 表示取最大的前 K 个；"asc" 表示取最小的前 K 个
    """
    if k <= 0 or not records:
        return []

    if k >= len(records):
        return _finalize(records[:], field, order)

    normalized_order = order.strip().lower()
    if normalized_order not in {"asc", "desc"}:
        normalized_order = "desc"

    heap = MinHeap()

    for index, record in enumerate(records):
        raw_value = get_numeric_value(record, field)
        # 小顶堆默认保留“最小键值”在堆顶。
        # 若要取最大的前 K 个，则直接把原值作为键，堆顶就是当前第 K 大中的最小值。
        # 若要取最小的前 K 个，则取相反数作为键，仍可复用同一套逻辑。
        heap_key = raw_value if normalized_order == "desc" else -raw_value
        item = (heap_key, index, record)

        if len(heap) < k:
            heap.push(item)
            continue

        top_item = heap.peek()
        if top_item is not None and item[0] > top_item[0]:
            heap.replace_top(item)

    result = [entry[2] for entry in heap.data]
    return _finalize(result, field, order)


def _finalize(
    records: list[dict[str, Any]],
    field: str,
    order: str,
) -> list[dict[str, Any]]:
    """
    对 Top-K 结果做最终顺序整理。

    这里结果规模已经缩小到 K，允许用简单插入排序整理最终输出顺序，
    不会破坏整体 O(n log k) 的核心复杂度。
    """
    normalized_order = order.strip().lower()
    reverse = normalized_order == "desc"
    result = records[:]

    for i in range(1, len(result)):
        current = result[i]
        current_value = get_numeric_value(current, field)
        j = i - 1

        while j >= 0:
            left_value = get_numeric_value(result[j], field)
            should_move = left_value < current_value if reverse else left_value > current_value
            if not should_move:
                break
            result[j + 1] = result[j]
            j -= 1

        result[j + 1] = current

    return result
