import heapq

class Router:
    """
    路径规划核心类，基于 Dijkstra 算法实现。
    """
    def __init__(self, graph):
        self.graph = graph

    def _normalize_transport_modes(self, value):
        """
        将边上的交通方式配置统一转成小写列表，便于做兼容判断。
        """
        if value is None:
            return []

        if isinstance(value, str):
            return [value.strip().casefold()] if value.strip() else []

        result = []
        for item in value:
            if item is None:
                continue
            normalized = str(item).strip().casefold()
            if normalized:
                result.append(normalized)
        return result

    def _is_edge_allowed(self, edge, transport_mode):
        """
        根据边上声明的交通方式限制判断当前边是否可通行。

        支持的边字段：
        - allowed_transports / transport_modes / transport_mode
        - blocked_transports
        """
        if transport_mode is None:
            return True

        normalized_mode = str(transport_mode).strip().casefold()
        if not normalized_mode or normalized_mode == "any":
            return True

        blocked_modes = self._normalize_transport_modes(edge.get("blocked_transports"))
        if normalized_mode in blocked_modes:
            return False

        allowed_modes = edge.get("allowed_transports")
        if allowed_modes is None:
            allowed_modes = edge.get("transport_modes")
        if allowed_modes is None:
            allowed_modes = edge.get("transport_mode")

        normalized_allowed = self._normalize_transport_modes(allowed_modes)
        if not normalized_allowed:
            return True

        return normalized_mode in normalized_allowed

    def _get_weight(self, edge, strategy):
        """
        根据当前策略计算边的权重。
        """
        if strategy == "shortest_distance":
            return edge.get("distance", float('inf'))
        elif strategy == "shortest_time":
            distance = edge.get("distance", float('inf'))
            speed = edge.get("ideal_speed", 1.0)
            congestion = edge.get("congestion", 1.0)
            
            # 防御性除零保护
            if speed <= 0 or congestion <= 0:
                return float('inf')
            
            # 时间 = 距离 / (理想速度 * 拥挤系数)
            return distance / (speed * congestion)
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")

    def query_routing(
        self,
        start_node_id,
        target_node_id,
        strategy="shortest_distance",
        transport_mode=None,
    ):
        """
        完整路径查询接口
        :param start_node_id: 起点 ID
        :param target_node_id: 终点 ID
        :param strategy: 规划策略 ('shortest_distance' 或 'shortest_time')
        :param transport_mode: 交通方式，可选；未提供时表示不过滤
        :return: 包含路径信息、总权重、分段信息的字典
        """
        if start_node_id not in self.graph.nodes or target_node_id not in self.graph.nodes:
            return {"success": False, "message": "起点或终点不存在于图中。"}

        # 初始化距离表，所有节点距离设为无穷大
        distances = {node: float('inf') for node in self.graph.nodes}
        distances[start_node_id] = 0
        
        # 优先级队列，用于 Dijkstra 优化 (当前累积权重, 节点 ID)
        pq = [(0, start_node_id)]
        
        # 记录路径来源：{node: (previous_node, edge_used)}
        came_from = {start_node_id: (None, None)}

        while pq:
            current_weight, current_node = heapq.heappop(pq)

            # 提前终止：如果已经到达终点，则最短路径已确定
            if current_node == target_node_id:
                break

            # 若取出的权重比已知最短距离大，说明是过期数据，直接跳过
            if current_weight > distances.get(current_node, float('inf')):
                continue

            # 遍历相邻节点
            for edge in self.graph.adj.get(current_node, []):
                if not self._is_edge_allowed(edge, transport_mode):
                    continue

                neighbor = edge["to"]
                weight = self._get_weight(edge, strategy)
                
                new_weight = current_weight + weight
                
                # 松弛操作 (Relaxation)
                if new_weight < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_weight
                    came_from[neighbor] = (current_node, edge)
                    heapq.heappush(pq, (new_weight, neighbor))

        # 检查是否可达
        if distances.get(target_node_id, float('inf')) == float('inf'):
            return {"success": False, "message": "无法从起点到达终点。"}

        # 回溯重构路径
        path = []
        curr = target_node_id
        while curr is not None:
            path.append(curr)
            prev, _ = came_from.get(curr, (None, None))
            curr = prev
            
        path.reverse()
        
        # 返回符合文档约定的数据结构
        return {
            "success": True,
            "path": path,
            "total_weight": distances[target_node_id],
            "strategy": strategy,
            "transport_mode": transport_mode,
            "segments": [
                {
                    "layer": getattr(self.graph, 'layer_id', 'default'),
                    "path": path,
                    "distance": distances[target_node_id] if strategy == "shortest_distance" else None
                }
            ]
        }

    def query_distance(
        self,
        start_node_id,
        target_node_id,
        strategy="shortest_distance",
        transport_mode=None,
    ):
        """
        轻量级查询接口，专供 Member B 推荐系统排序使用。
        :return: 仅返回两点之间的最短距离/时间的数值。不可达则返回 infinity。
        """
        result = self.query_routing(
            start_node_id,
            target_node_id,
            strategy,
            transport_mode,
        )
        if result["success"]:
            return result["total_weight"]
        return float('inf')

    def _merge_leg_paths(self, leg_results):
        """
        将多段路径拼接为一条完整路径，避免重复拼接衔接点。
        """
        full_path = []
        for index, leg in enumerate(leg_results):
            leg_path = leg.get("path", [])
            if not leg_path:
                continue

            if index == 0:
                full_path.extend(leg_path)
            else:
                full_path.extend(leg_path[1:])
        return full_path

    def query_multi_target(
        self,
        start_node_id,
        target_node_ids,
        strategy="shortest_distance",
        transport_mode=None,
        return_to_start=True,
    ):
        """
        多目标路径基础版接口。

        当前实现思路：
        1. 先复用单目标最短路径，预计算起点和各目标点之间的最短路
        2. 再使用状态压缩 DP 搜索最优访问顺序
        3. 最后将各段最短路径拼接成完整路线
        """
        if start_node_id not in self.graph.nodes:
            return {"success": False, "message": "起点不存在于图中。"}

        unique_targets = []
        seen_targets = set()
        for node_id in target_node_ids:
            if node_id == start_node_id or node_id in seen_targets:
                continue
            if node_id not in self.graph.nodes:
                return {"success": False, "message": f"目标点不存在于图中: {node_id}"}
            seen_targets.add(node_id)
            unique_targets.append(node_id)

        if not unique_targets:
            return {
                "success": True,
                "path": [start_node_id],
                "visit_order": [start_node_id],
                "total_weight": 0,
                "strategy": strategy,
                "transport_mode": transport_mode,
                "return_to_start": return_to_start,
                "segments": [],
                "leg_results": [],
            }

        # 状态压缩 DP 只适合小规模目标点，避免在真实联调中意外爆炸
        if len(unique_targets) > 12:
            return {
                "success": False,
                "message": "多目标路径基础版当前仅支持 12 个及以下目标点。",
            }

        nodes = [start_node_id] + unique_targets
        pair_routes = {}

        for source in nodes:
            for target in nodes:
                if source == target:
                    continue
                pair_routes[(source, target)] = self.query_routing(
                    source,
                    target,
                    strategy=strategy,
                    transport_mode=transport_mode,
                )

        target_count = len(unique_targets)
        dp = {}
        parent = {}

        for index, target in enumerate(unique_targets):
            route = pair_routes[(start_node_id, target)]
            if not route["success"]:
                continue
            mask = 1 << index
            dp[(mask, index)] = route["total_weight"]
            parent[(mask, index)] = None

        full_mask = (1 << target_count) - 1

        for mask in range(1, full_mask + 1):
            for last_index in range(target_count):
                current_state = (mask, last_index)
                if current_state not in dp:
                    continue

                current_cost = dp[current_state]
                current_node = unique_targets[last_index]

                for next_index in range(target_count):
                    if mask & (1 << next_index):
                        continue

                    next_node = unique_targets[next_index]
                    route = pair_routes[(current_node, next_node)]
                    if not route["success"]:
                        continue

                    next_mask = mask | (1 << next_index)
                    next_state = (next_mask, next_index)
                    next_cost = current_cost + route["total_weight"]

                    if next_cost < dp.get(next_state, float('inf')):
                        dp[next_state] = next_cost
                        parent[next_state] = current_state

        best_state = None
        best_total = float('inf')

        for last_index in range(target_count):
            state = (full_mask, last_index)
            if state not in dp:
                continue

            total_cost = dp[state]
            last_node = unique_targets[last_index]

            if return_to_start:
                back_route = pair_routes[(last_node, start_node_id)]
                if not back_route["success"]:
                    continue
                total_cost += back_route["total_weight"]

            if total_cost < best_total:
                best_total = total_cost
                best_state = state

        if best_state is None:
            return {"success": False, "message": "无法找到覆盖所有目标点的可行路径。"}

        ordered_target_indices = []
        current_state = best_state
        while current_state is not None:
            _, last_index = current_state
            ordered_target_indices.append(last_index)
            current_state = parent[current_state]
        ordered_target_indices.reverse()

        visit_order = [start_node_id]
        visit_order.extend(unique_targets[index] for index in ordered_target_indices)
        if return_to_start:
            visit_order.append(start_node_id)

        leg_results = []
        merged_segments = []

        for leg_start, leg_target in zip(visit_order, visit_order[1:]):
            route = pair_routes[(leg_start, leg_target)]
            leg_result = {
                "start_node_id": leg_start,
                "target_node_id": leg_target,
                "path": route["path"],
                "total_weight": route["total_weight"],
                "segments": route.get("segments", []),
            }
            leg_results.append(leg_result)

            for segment in route.get("segments", []):
                copied_segment = segment.copy()
                copied_segment["start_node_id"] = leg_start
                copied_segment["target_node_id"] = leg_target
                merged_segments.append(copied_segment)

        full_path = self._merge_leg_paths(leg_results)

        return {
            "success": True,
            "path": full_path,
            "visit_order": visit_order,
            "target_node_ids": unique_targets,
            "total_weight": best_total,
            "strategy": strategy,
            "transport_mode": transport_mode,
            "return_to_start": return_to_start,
            "segments": merged_segments,
            "leg_results": leg_results,
        }
