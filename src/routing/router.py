import heapq

class Router:
    """
    路径规划核心类，基于 Dijkstra 算法实现。
    """
    def __init__(self, graph):
        self.graph = graph

    def _normalize_site_id(self, site_id):
        """标准化 site_id；空值表示不限定景区。"""
        if site_id is None:
            return None

        normalized = str(site_id).strip()
        return normalized or None

    def _resolve_graph_site_id(self):
        """返回当前图对象绑定的景区 ID；不存在时返回空字符串。"""
        site_id = getattr(self.graph, "site_id", "")
        if site_id:
            return str(site_id).strip()

        layer_id = getattr(self.graph, "layer_id", "")
        return str(layer_id).strip()

    def _validate_site_id(self, site_id):
        """
        校验本次查询的 site_id 是否与当前图对象一致。

        兼容策略：
        - 未传 site_id：直接通过
        - 图对象未绑定 site_id：直接通过
        - 二者都存在时必须一致
        """
        normalized_site_id = self._normalize_site_id(site_id)
        if normalized_site_id is None:
            return True, None

        graph_site_id = self._resolve_graph_site_id()
        if not graph_site_id:
            return True, normalized_site_id

        if graph_site_id != normalized_site_id:
            return False, normalized_site_id

        return True, normalized_site_id

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
        - vehicle_access: all / pedestrian_only / vehicle_only
        """
        if transport_mode is None:
            return True

        normalized_mode = str(transport_mode).strip().casefold()
        if not normalized_mode or normalized_mode == "any":
            return True

        vehicle_access = str(edge.get("vehicle_access", "")).strip().casefold()
        if vehicle_access == "pedestrian_only" and normalized_mode not in {"walk", "pedestrian", "foot"}:
            return False
        if vehicle_access == "vehicle_only" and normalized_mode in {"walk", "pedestrian", "foot"}:
            return False

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

    def _get_travel_time_seconds(self, edge):
        """按秒计算边的预计通行时间。"""
        distance = edge.get("distance", float('inf'))
        speed = edge.get("ideal_speed", 1.0)
        congestion = edge.get("congestion", 1.0)

        if speed <= 0 or congestion <= 0:
            return float('inf')

        return distance / (speed * congestion)

    def _summarize_path_metrics(self, path_edges):
        """
        统计一条路径的总距离和总时间。
        """
        total_distance_m = 0.0
        total_time_s = 0.0

        for edge in path_edges:
            total_distance_m += float(edge.get("distance", 0))
            edge_time = self._get_travel_time_seconds(edge)
            if edge_time == float('inf'):
                total_time_s = None
            elif total_time_s is not None:
                total_time_s += edge_time

        return total_distance_m, total_time_s

    def _resolve_node_layer(self, node_id):
        """
        解析节点所属层；标准分层数据优先使用 source_sub_graph_id。
        """
        node_data = self.graph.nodes.get(node_id, {})
        layer = str(node_data.get("source_sub_graph_id", "")).strip()
        if layer:
            return layer

        graph_layer = str(getattr(self.graph, "layer_id", "")).strip()
        return graph_layer or "default"

    def _get_node_name(self, node_id):
        """返回节点展示名称；缺失时退回到节点 ID。"""
        node_data = self.graph.nodes.get(node_id, {})
        name = str(node_data.get("name", "")).strip()
        return name or str(node_id)

    def _build_path_steps(self, path, path_edges):
        """
        为业务层构造逐边的路径明细，便于展示“经过了哪条路、进了哪一层”。
        """
        steps = []

        for index, edge in enumerate(path_edges):
            start_node_id = path[index]
            end_node_id = path[index + 1]
            start_layer = self._resolve_node_layer(start_node_id)
            end_layer = self._resolve_node_layer(end_node_id)
            edge_type = str(edge.get("type", "")).strip()
            edge_name = str(edge.get("name", "")).strip()
            edge_time = self._get_travel_time_seconds(edge)

            steps.append(
                {
                    "step_index": index + 1,
                    "from_node_id": start_node_id,
                    "from_node_name": self._get_node_name(start_node_id),
                    "to_node_id": end_node_id,
                    "to_node_name": self._get_node_name(end_node_id),
                    "from_layer": start_layer,
                    "to_layer": end_layer,
                    "display_layer": end_layer if start_layer != end_layer else start_layer,
                    "transition_kind": "cross_layer" if start_layer != end_layer else "same_layer",
                    "edge_type": edge_type,
                    "edge_name": edge_name,
                    "description": str(edge.get("description", "")).strip(),
                    "distance_m": float(edge.get("distance", 0)),
                    "estimated_time_s": None if edge_time == float('inf') else edge_time,
                    "vehicle_access": str(edge.get("vehicle_access", "all")).strip() or "all",
                    "is_gate_transition": edge_type == "gate_link",
                }
            )

        return steps

    def _build_segments(self, path, path_steps):
        """
        根据路径构造分段信息。

        对标准分层数据：
        - 同层连续边会被合并为同一段
        - 跨层 gate_link 边并入目标层分段，便于业务层直接展示跨层进入动作
        """
        if not path:
            return []

        if not path_steps:
            return [
                {
                    "segment_index": 1,
                    "layer": self._resolve_node_layer(path[0]),
                    "path": path[:],
                    "start_node_id": path[0],
                    "target_node_id": path[0],
                    "start_node_name": self._get_node_name(path[0]),
                    "target_node_name": self._get_node_name(path[0]),
                    "node_count": len(path),
                    "edge_count": 0,
                    "edge_names": [],
                    "edge_types": [],
                    "distance": 0.0,
                    "distance_m": 0.0,
                    "estimated_time_s": 0.0,
                }
            ]

        segments = []

        for step in path_steps:
            segment_layer = step["display_layer"]
            edge_distance = step["distance_m"]
            edge_time_s = step["estimated_time_s"]

            if segments and segments[-1]["layer"] == segment_layer:
                segment = segments[-1]
                if segment["path"][-1] != step["from_node_id"]:
                    segment["path"].append(step["from_node_id"])
                segment["path"].append(step["to_node_id"])
                segment["target_node_id"] = step["to_node_id"]
                segment["target_node_name"] = step["to_node_name"]
                segment["node_count"] = len(segment["path"])
                segment["edge_count"] += 1
                if step["edge_name"]:
                    segment["edge_names"].append(step["edge_name"])
                if step["edge_type"]:
                    segment["edge_types"].append(step["edge_type"])
                segment["distance"] += edge_distance
                segment["distance_m"] += edge_distance
                if segment["estimated_time_s"] is None or edge_time_s is None:
                    segment["estimated_time_s"] = None
                else:
                    segment["estimated_time_s"] += edge_time_s
                continue

            segments.append(
                {
                    "segment_index": len(segments) + 1,
                    "layer": segment_layer,
                    "path": [step["from_node_id"], step["to_node_id"]],
                    "start_node_id": step["from_node_id"],
                    "target_node_id": step["to_node_id"],
                    "start_node_name": step["from_node_name"],
                    "target_node_name": step["to_node_name"],
                    "node_count": 2,
                    "edge_count": 1,
                    "edge_names": [step["edge_name"]] if step["edge_name"] else [],
                    "edge_types": [step["edge_type"]] if step["edge_type"] else [],
                    "distance": edge_distance,
                    "distance_m": edge_distance,
                    "estimated_time_s": edge_time_s,
                }
            )

        return segments

    def _build_route_overview(self, path, path_steps, segments, strategy, transport_mode):
        """
        构造路径摘要，供业务层快速展示。
        """
        if not path:
            return {
                "start_node_id": None,
                "start_node_name": None,
                "target_node_id": None,
                "target_node_name": None,
                "node_count": 0,
                "edge_count": 0,
                "segment_count": 0,
                "layer_sequence": [],
                "cross_layer": False,
                "cross_layer_step_count": 0,
                "strategy": strategy,
                "weight_unit": "meter" if strategy == "shortest_distance" else "second",
                "transport_mode": transport_mode,
            }

        cross_layer_step_count = sum(
            1 for step in path_steps if step.get("transition_kind") == "cross_layer"
        )
        layer_sequence = [segment["layer"] for segment in segments] or [self._resolve_node_layer(path[0])]

        return {
            "start_node_id": path[0],
            "start_node_name": self._get_node_name(path[0]),
            "target_node_id": path[-1],
            "target_node_name": self._get_node_name(path[-1]),
            "node_count": len(path),
            "edge_count": len(path_steps),
            "segment_count": len(segments),
            "layer_sequence": layer_sequence,
            "cross_layer": cross_layer_step_count > 0,
            "cross_layer_step_count": cross_layer_step_count,
            "strategy": strategy,
            "weight_unit": "meter" if strategy == "shortest_distance" else "second",
            "transport_mode": transport_mode,
        }

    def _get_weight(self, edge, strategy):
        """
        根据当前策略计算边的权重。
        """
        if strategy == "shortest_distance":
            return edge.get("distance", float('inf'))
        elif strategy == "shortest_time":
            # 时间单位：秒 (distance: 米, ideal_speed: 米/秒)
            return self._get_travel_time_seconds(edge)
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")

    def query_routing(
        self,
        start_node_id,
        target_node_id,
        strategy="shortest_distance",
        transport_mode=None,
        site_id=None,
    ):
        """
        完整路径查询接口
        :param start_node_id: 起点 ID
        :param target_node_id: 终点 ID
        :param strategy: 规划策略 ('shortest_distance' 或 'shortest_time')
        :param transport_mode: 交通方式，可选；未提供时表示不过滤
        :param site_id: 景区 ID，可选；未提供时默认使用当前图对象绑定景区
        :return: 包含路径信息、总权重、距离、时间和分段信息的字典
        """
        site_is_valid, normalized_site_id = self._validate_site_id(site_id)
        if not site_is_valid:
            return {
                "success": False,
                "message": f"site_id 不匹配，当前图仅支持景区 {self._resolve_graph_site_id()}。",
            }

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
        path_edges = []
        curr = target_node_id
        while curr is not None:
            path.append(curr)
            prev, edge_used = came_from.get(curr, (None, None))
            if edge_used is not None:
                path_edges.append(edge_used)
            curr = prev
            
        path.reverse()
        path_edges.reverse()

        total_distance_m, estimated_time_s = self._summarize_path_metrics(path_edges)
        total_weight = distances[target_node_id]
        weight_unit = "meter" if strategy == "shortest_distance" else "second"
        path_steps = self._build_path_steps(path, path_edges)
        segments = self._build_segments(path, path_steps)
        route_overview = self._build_route_overview(path, path_steps, segments, strategy, transport_mode)

        # 返回符合文档约定的数据结构
        return {
            "success": True,
            "site_id": normalized_site_id or self._resolve_graph_site_id() or None,
            "start_node_id": start_node_id,
            "target_node_id": target_node_id,
            "start_node_name": self._get_node_name(start_node_id),
            "target_node_name": self._get_node_name(target_node_id),
            "path": path,
            "path_node_names": [self._get_node_name(node_id) for node_id in path],
            "path_steps": path_steps,
            "total_weight": total_weight,
            "weight_unit": weight_unit,
            "total_distance_m": total_distance_m,
            "estimated_time_s": estimated_time_s,
            "total_distance": total_distance_m,
            "estimated_time": estimated_time_s,
            "strategy": strategy,
            "transport_mode": transport_mode,
            "layer_sequence": route_overview["layer_sequence"],
            "route_overview": route_overview,
            "segments": segments,
        }

    def query_distance(
        self,
        start_node_id,
        target_node_id,
        strategy="shortest_distance",
        transport_mode=None,
        site_id=None,
    ):
        """
        轻量级查询接口，专供 Member B 推荐系统排序使用。
        :return: 仅返回两点之间的最短距离/时间数值。
                 - shortest_distance: 米
                 - shortest_time: 秒
                 不可达则返回 infinity。
        """
        result = self.query_routing(
            start_node_id=start_node_id,
            target_node_id=target_node_id,
            strategy=strategy,
            transport_mode=transport_mode,
            site_id=site_id,
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
        site_id=None,
    ):
        """
        多目标路径基础版接口。

        当前实现思路：
        1. 先复用单目标最短路径，预计算起点和各目标点之间的最短路
        2. 再使用状态压缩 DP 搜索最优访问顺序
        3. 最后将各段最短路径拼接成完整路线
        """
        site_is_valid, normalized_site_id = self._validate_site_id(site_id)
        if not site_is_valid:
            return {
                "success": False,
                "message": f"site_id 不匹配，当前图仅支持景区 {self._resolve_graph_site_id()}。",
            }

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
                "site_id": normalized_site_id or self._resolve_graph_site_id() or None,
                "path": [start_node_id],
                "visit_order": [start_node_id],
                "path_node_names": [self._get_node_name(start_node_id)],
                "visit_order_names": [self._get_node_name(start_node_id)],
                "target_node_ids": [],
                "total_weight": 0,
                "weight_unit": "meter" if strategy == "shortest_distance" else "second",
                "total_distance_m": 0,
                "estimated_time_s": 0,
                "total_distance": 0,
                "estimated_time": 0,
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
                    site_id=normalized_site_id,
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
                "start_node_name": route.get("start_node_name", self._get_node_name(leg_start)),
                "target_node_name": route.get("target_node_name", self._get_node_name(leg_target)),
                "site_id": route.get("site_id"),
                "path": route["path"],
                "path_node_names": route.get("path_node_names", []),
                "path_steps": route.get("path_steps", []),
                "total_weight": route["total_weight"],
                "weight_unit": route.get("weight_unit"),
                "total_distance_m": route.get("total_distance_m", 0.0),
                "estimated_time_s": route.get("estimated_time_s"),
                "total_distance": route.get("total_distance", route.get("total_distance_m", 0.0)),
                "estimated_time": route.get("estimated_time", route.get("estimated_time_s")),
                "route_overview": route.get("route_overview", {}),
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
            "site_id": normalized_site_id or self._resolve_graph_site_id() or None,
            "path": full_path,
            "path_node_names": [self._get_node_name(node_id) for node_id in full_path],
            "visit_order": visit_order,
            "visit_order_names": [self._get_node_name(node_id) for node_id in visit_order],
            "target_node_ids": unique_targets,
            "total_weight": best_total,
            "weight_unit": "meter" if strategy == "shortest_distance" else "second",
            "total_distance_m": sum(leg["total_distance_m"] for leg in leg_results),
            "estimated_time_s": sum(
                leg["estimated_time_s"] for leg in leg_results if leg["estimated_time_s"] is not None
            ) if all(leg["estimated_time_s"] is not None for leg in leg_results) else None,
            "total_distance": sum(leg["total_distance_m"] for leg in leg_results),
            "estimated_time": sum(
                leg["estimated_time_s"] for leg in leg_results if leg["estimated_time_s"] is not None
            ) if all(leg["estimated_time_s"] is not None for leg in leg_results) else None,
            "strategy": strategy,
            "transport_mode": transport_mode,
            "return_to_start": return_to_start,
            "segments": merged_segments,
            "leg_results": leg_results,
        }
