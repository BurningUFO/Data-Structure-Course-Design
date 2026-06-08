import heapq
import re

class Router:
    """
    路径规划核心类，基于 Dijkstra 算法实现。
    """
    WALK_MODES = {"walk", "pedestrian", "foot"}
    BIKE_MODES = {"bike", "bicycle", "cycling"}
    MIXED_MODES = {"mixed", "walk_bike", "walk+bike", "walk-bike"}
    TRANSPORT_ALIASES = {
        "pedestrian": "walk",
        "foot": "walk",
        "步行": "walk",
        "bicycle": "bike",
        "cycling": "bike",
        "自行车": "bike",
        "walk+bike": "mixed",
        "walk-bike": "mixed",
        "walk_bike": "mixed",
        "步行+自行车": "mixed",
        "步行 + 自行车": "mixed",
        "混合交通": "mixed",
    }
    TIME_SLOT_LABELS = {
        "normal": "平峰",
        "morning_peak": "早高峰",
        "lunch_peak": "午间高峰",
        "evening_peak": "晚高峰",
    }
    TIME_SLOT_ALIASES = {
        "": "normal",
        "normal": "normal",
        "off_peak": "normal",
        "offpeak": "normal",
        "平峰": "normal",
        "常规": "normal",
        "morning": "morning_peak",
        "morning_peak": "morning_peak",
        "am_peak": "morning_peak",
        "早高峰": "morning_peak",
        "早峰": "morning_peak",
        "lunch": "lunch_peak",
        "lunch_peak": "lunch_peak",
        "noon": "lunch_peak",
        "午间高峰": "lunch_peak",
        "午高峰": "lunch_peak",
        "evening": "evening_peak",
        "evening_peak": "evening_peak",
        "pm_peak": "evening_peak",
        "晚高峰": "evening_peak",
        "晚峰": "evening_peak",
    }
    TIME_SLOT_PROFILE_FACTORS = {
        "normal": {"default": 1.0},
        "morning_peak": {
            "default": 0.78,
            "road": 0.66,
            "bike_lane": 0.82,
            "poi_access": 0.86,
            "gate_link": 0.9,
            "indoor": 0.94,
        },
        "lunch_peak": {
            "default": 0.84,
            "road": 0.78,
            "bike_lane": 0.9,
            "poi_access": 0.72,
            "gate_link": 0.92,
            "indoor": 0.9,
        },
        "evening_peak": {
            "default": 0.72,
            "road": 0.62,
            "bike_lane": 0.8,
            "poi_access": 0.82,
            "gate_link": 0.84,
            "indoor": 0.94,
        },
    }

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

    def _canonical_transport_mode(self, value):
        """将交通方式别名折叠成路由内部的稳定字段。"""
        normalized = str(value).strip().casefold()
        return self.TRANSPORT_ALIASES.get(normalized, normalized)

    def _normalize_time_slot(self, value):
        """将时段别名折叠成路由内部的稳定字段。"""
        normalized = str(value or "").strip().casefold()
        return self.TIME_SLOT_ALIASES.get(normalized, "normal")

    def _infer_time_slot_from_departure_time(self, departure_time):
        """从 HH:MM 或 ISO-like 时间字符串推断高峰时段。"""
        text = str(departure_time or "").strip()
        if not text:
            return None

        match = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)", text)
        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2))
        value = hour + minute / 60
        if 7 <= value < 10:
            return "morning_peak"
        if 11 <= value < 14:
            return "lunch_peak"
        if 17 <= value < 20:
            return "evening_peak"
        return "normal"

    def _resolve_time_context(self, time_slot=None, departure_time=None):
        departure_text = str(departure_time or "").strip()
        raw_slot = str(time_slot or "").strip()
        if raw_slot:
            slot = self._normalize_time_slot(raw_slot)
            source = "time_slot"
        else:
            inferred_slot = self._infer_time_slot_from_departure_time(departure_text)
            slot = inferred_slot or "normal"
            source = "departure_time" if inferred_slot is not None else "default"

        return {
            "time_slot": slot,
            "label": self.TIME_SLOT_LABELS.get(slot, slot),
            "departure_time": departure_text,
            "source": source,
            "dynamic_congestion": slot != "normal",
        }

    def _normalize_transport_modes(self, value):
        """
        将边上的交通方式配置统一转成小写列表，便于做兼容判断。
        """
        if value is None:
            return []

        if isinstance(value, str):
            normalized = self._canonical_transport_mode(value)
            return [normalized] if normalized else []

        result = []
        for item in value:
            if item is None:
                continue
            normalized = self._canonical_transport_mode(item)
            if normalized:
                result.append(normalized)
        return result

    def _is_walk_mode(self, transport_mode):
        return self._canonical_transport_mode(transport_mode) == "walk"

    def _is_bike_mode(self, transport_mode):
        return self._canonical_transport_mode(transport_mode) == "bike"

    def _is_mixed_mode(self, transport_mode):
        return self._canonical_transport_mode(transport_mode) == "mixed"

    def _is_indoor_or_gate_edge(self, edge, from_node_id=None):
        edge_type = str(edge.get("type", "")).strip().casefold()
        if edge_type == "gate_link":
            return True

        for node_id in (from_node_id, edge.get("to")):
            if node_id is None:
                continue
            if self._resolve_node_layer(node_id).startswith("indoor_"):
                return True
        return False

    def _edge_configured_transport_modes(self, edge):
        allowed_modes = edge.get("allowed_transports")
        if allowed_modes is None:
            allowed_modes = edge.get("transport_modes")
        if allowed_modes is None:
            allowed_modes = edge.get("transport_mode")
        return set(self._normalize_transport_modes(allowed_modes))

    def _default_edge_transport_modes(self, edge, from_node_id=None):
        if self._is_indoor_or_gate_edge(edge, from_node_id):
            return {"walk"}

        vehicle_access = str(edge.get("vehicle_access", "")).strip().casefold()
        if vehicle_access == "pedestrian_only":
            return {"walk"}
        if vehicle_access == "vehicle_only":
            return {"bike", "car"}
        return {"walk", "bike", "car"}

    def _supported_edge_transport_modes(self, edge, from_node_id=None):
        modes = self._edge_configured_transport_modes(edge)
        if not modes:
            modes = self._default_edge_transport_modes(edge, from_node_id)

        if self._is_indoor_or_gate_edge(edge, from_node_id):
            modes = modes & {"walk"}

        blocked_modes = set(self._normalize_transport_modes(edge.get("blocked_transports")))
        return modes - blocked_modes

    def _is_edge_allowed(self, edge, transport_mode, from_node_id=None):
        """
        根据边上声明的交通方式限制判断当前边是否可通行。

        支持的边字段：
        - allowed_transports / transport_modes / transport_mode
        - blocked_transports
        - vehicle_access: all / pedestrian_only / vehicle_only
        """
        if transport_mode is None:
            return True

        normalized_mode = self._canonical_transport_mode(transport_mode)
        if not normalized_mode or normalized_mode == "any":
            return True

        supported_modes = self._supported_edge_transport_modes(edge, from_node_id)
        if normalized_mode == "mixed":
            return bool(supported_modes & {"walk", "bike"})

        return normalized_mode in supported_modes

    def _resolve_transport_value(self, edge, field_names, mode):
        for field_name in field_names:
            value = edge.get(field_name)
            if not isinstance(value, dict):
                continue
            candidates = [
                mode,
                "pedestrian" if mode == "walk" else mode,
                "bicycle" if mode == "bike" else mode,
            ]
            for candidate in candidates:
                if candidate in value:
                    return value[candidate]
        return None

    def _get_transport_speed(self, edge, mode=None):
        value = None
        if mode:
            value = self._resolve_transport_value(
                edge,
                ("transport_speeds", "ideal_speeds", "speed_by_transport"),
                mode,
            )
        if value is None:
            value = edge.get("ideal_speed", 1.0)
        return float(value)

    def _get_base_transport_congestion(self, edge, mode=None):
        value = None
        if mode:
            value = self._resolve_transport_value(
                edge,
                ("transport_congestion", "congestion_by_transport"),
                mode,
            )
        if value is None:
            value = edge.get("congestion", 1.0)
        return float(value)

    def _dict_get_casefold(self, mapping, candidates):
        if not isinstance(mapping, dict):
            return None
        for candidate in candidates:
            if candidate in mapping:
                return mapping[candidate]
        lowered = {str(key).strip().casefold(): value for key, value in mapping.items()}
        for candidate in candidates:
            normalized = str(candidate).strip().casefold()
            if normalized in lowered:
                return lowered[normalized]
        return None

    def _resolve_time_congestion_value(self, value, mode, time_slot):
        if not isinstance(value, dict):
            return None

        slot_candidates = [
            time_slot,
            self.TIME_SLOT_LABELS.get(time_slot, ""),
            "morning" if time_slot == "morning_peak" else "",
            "lunch" if time_slot == "lunch_peak" else "",
            "evening" if time_slot == "evening_peak" else "",
        ]
        slot_candidates = [item for item in slot_candidates if item]
        mode_candidates = [
            mode,
            "pedestrian" if mode == "walk" else mode,
            "bicycle" if mode == "bike" else mode,
        ]
        mode_candidates = [item for item in mode_candidates if item]

        if mode_candidates:
            mode_value = self._dict_get_casefold(value, mode_candidates)
            slot_value = self._dict_get_casefold(mode_value, slot_candidates)
            if slot_value is not None:
                return slot_value

        slot_value = self._dict_get_casefold(value, slot_candidates)
        if isinstance(slot_value, dict) and mode_candidates:
            return self._dict_get_casefold(slot_value, mode_candidates)
        return slot_value

    def _get_explicit_time_congestion(self, edge, mode=None, time_slot="normal"):
        if time_slot == "normal":
            return None

        for field_name in (
            "transport_congestion_by_time",
            "congestion_by_transport_time",
            "congestion_by_time",
            "time_congestion",
            "congestion_by_slot",
            "time_slot_congestion",
        ):
            resolved = self._resolve_time_congestion_value(
                edge.get(field_name),
                mode,
                time_slot,
            )
            if resolved is None:
                continue
            try:
                return float(resolved)
            except (TypeError, ValueError):
                return None
        return None

    def _get_profile_congestion_factor(self, edge, time_slot="normal", from_node_id=None):
        profile = self.TIME_SLOT_PROFILE_FACTORS.get(time_slot) or self.TIME_SLOT_PROFILE_FACTORS["normal"]
        if time_slot == "normal":
            return 1.0

        if self._is_indoor_or_gate_edge(edge, from_node_id):
            return profile.get("indoor", profile["default"])

        edge_type = str(edge.get("type", "")).strip().casefold()
        if edge_type in profile:
            return profile[edge_type]
        if edge_type in {"white_road", "walkway", "pedestrian_path", "campus_road"}:
            return profile.get("road", profile["default"])
        return profile["default"]

    def _get_transport_congestion(self, edge, mode=None, time_slot="normal", from_node_id=None):
        base_congestion = self._get_base_transport_congestion(edge, mode)
        explicit_congestion = self._get_explicit_time_congestion(edge, mode, time_slot)
        if explicit_congestion is not None:
            return explicit_congestion
        return base_congestion * self._get_profile_congestion_factor(edge, time_slot, from_node_id)

    def _select_edge_transport_mode(self, edge, transport_mode=None, from_node_id=None, time_slot="normal"):
        normalized_mode = None
        if transport_mode is not None:
            normalized_mode = self._canonical_transport_mode(transport_mode)

        if not normalized_mode or normalized_mode == "any":
            return None

        supported_modes = self._supported_edge_transport_modes(edge, from_node_id)
        if normalized_mode != "mixed":
            return normalized_mode if normalized_mode in supported_modes else None

        candidates = [mode for mode in ("bike", "walk") if mode in supported_modes]
        best_mode = None
        best_time = float("inf")
        distance = float(edge.get("distance", float("inf")))
        for mode in candidates:
            speed = self._get_transport_speed(edge, mode)
            congestion = self._get_transport_congestion(edge, mode, time_slot, from_node_id)
            if speed <= 0 or congestion <= 0:
                continue
            travel_time = distance / (speed * congestion)
            if travel_time < best_time:
                best_time = travel_time
                best_mode = mode
        return best_mode

    def _get_travel_time_seconds(self, edge, transport_mode=None, from_node_id=None, time_slot="normal"):
        """按秒计算边的预计通行时间。"""
        selected_mode = self._select_edge_transport_mode(edge, transport_mode, from_node_id, time_slot)
        if transport_mode is not None and selected_mode is None:
            return float('inf')

        distance = edge.get("distance", float('inf'))
        speed = self._get_transport_speed(edge, selected_mode)
        congestion = self._get_transport_congestion(edge, selected_mode, time_slot, from_node_id)

        if speed <= 0 or congestion <= 0:
            return float('inf')

        return distance / (speed * congestion)

    def _summarize_path_metrics(self, path, path_edges, transport_mode=None, time_slot="normal"):
        """
        统计一条路径的总距离和总时间。
        """
        total_distance_m = 0.0
        total_time_s = 0.0

        for index, edge in enumerate(path_edges):
            from_node_id = path[index] if index < len(path) else None
            total_distance_m += float(edge.get("distance", 0))
            edge_time = self._get_travel_time_seconds(edge, transport_mode, from_node_id, time_slot)
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

    def _resolve_node_floor_id(self, node_id):
        """返回节点所在楼层 ID；缺失时返回空字符串。"""
        node_data = self.graph.nodes.get(node_id, {})
        return str(node_data.get("floor_id", "")).strip()

    def _resolve_node_floor_label(self, node_id):
        """返回节点所在楼层展示名；缺失时回退到 floor_id。"""
        node_data = self.graph.nodes.get(node_id, {})
        floor_label = str(node_data.get("floor_label", "")).strip()
        if floor_label:
            return floor_label
        return self._resolve_node_floor_id(node_id)

    def _resolve_node_display_layer(self, node_id):
        """
        返回面向 UI 的层级展示文本。

        室内多层节点优先展示楼层标签，保持稳定的 source_sub_graph_id
        仍通过 from_layer / to_layer 单独透传。
        """
        floor_label = self._resolve_node_floor_label(node_id)
        if floor_label:
            return floor_label
        return self._resolve_node_layer(node_id)

    def _is_cross_layer_transition(self, start_node_id, end_node_id):
        """
        判断一步路径是否发生了跨层切换。

        兼容两种情况：
        - 室外 / 室内子图切换
        - 同一 indoor_*.json 内不同 floor_id 的跨楼层切换
        """
        start_layer = self._resolve_node_layer(start_node_id)
        end_layer = self._resolve_node_layer(end_node_id)
        if start_layer != end_layer:
            return True

        start_floor_id = self._resolve_node_floor_id(start_node_id)
        end_floor_id = self._resolve_node_floor_id(end_node_id)
        return bool(start_floor_id and end_floor_id and start_floor_id != end_floor_id)

    def _get_node_name(self, node_id):
        """返回节点展示名称；缺失时退回到节点 ID。"""
        node_data = self.graph.nodes.get(node_id, {})
        name = str(node_data.get("name", "")).strip()
        return name or str(node_id)

    def _build_path_steps(self, path, path_edges, transport_mode=None, time_slot="normal"):
        """
        为业务层构造逐边的路径明细，便于展示“经过了哪条路、进了哪一层”。
        """
        steps = []

        for index, edge in enumerate(path_edges):
            start_node_id = path[index]
            end_node_id = path[index + 1]
            start_layer = self._resolve_node_layer(start_node_id)
            end_layer = self._resolve_node_layer(end_node_id)
            start_floor_id = self._resolve_node_floor_id(start_node_id)
            end_floor_id = self._resolve_node_floor_id(end_node_id)
            start_floor_label = self._resolve_node_floor_label(start_node_id)
            end_floor_label = self._resolve_node_floor_label(end_node_id)
            start_display_layer = self._resolve_node_display_layer(start_node_id)
            end_display_layer = self._resolve_node_display_layer(end_node_id)
            is_cross_layer = self._is_cross_layer_transition(start_node_id, end_node_id)
            edge_type = str(edge.get("type", "")).strip()
            edge_name = str(edge.get("name", "")).strip()
            edge_time = self._get_travel_time_seconds(edge, transport_mode, start_node_id, time_slot)
            selected_transport_mode = self._select_edge_transport_mode(
                edge,
                transport_mode,
                start_node_id,
                time_slot,
            )
            base_congestion = self._get_base_transport_congestion(edge, selected_transport_mode)
            effective_congestion = self._get_transport_congestion(
                edge,
                selected_transport_mode,
                time_slot,
                start_node_id,
            )
            congestion_ratio = (
                effective_congestion / base_congestion
                if base_congestion and base_congestion > 0
                else None
            )

            steps.append(
                {
                    "step_index": index + 1,
                    "from_node_id": start_node_id,
                    "from_node_name": self._get_node_name(start_node_id),
                    "to_node_id": end_node_id,
                    "to_node_name": self._get_node_name(end_node_id),
                    "from_layer": start_layer,
                    "to_layer": end_layer,
                    "from_floor_id": start_floor_id,
                    "to_floor_id": end_floor_id,
                    "from_floor_label": start_floor_label,
                    "to_floor_label": end_floor_label,
                    "display_layer": end_display_layer if start_display_layer != end_display_layer else start_display_layer,
                    "transition_kind": "cross_layer" if is_cross_layer else "same_layer",
                    "edge_type": edge_type,
                    "edge_name": edge_name,
                    "description": str(edge.get("description", "")).strip(),
                    "distance_m": float(edge.get("distance", 0)),
                    "estimated_time_s": None if edge_time == float('inf') else edge_time,
                    "vehicle_access": str(edge.get("vehicle_access", "all")).strip() or "all",
                    "allowed_transports": sorted(
                        self._supported_edge_transport_modes(edge, start_node_id)
                    ),
                    "transport_mode_used": selected_transport_mode,
                    "time_slot": time_slot,
                    "time_slot_label": self.TIME_SLOT_LABELS.get(time_slot, time_slot),
                    "base_congestion": base_congestion,
                    "effective_congestion": effective_congestion,
                    "congestion_factor": congestion_ratio,
                    "congestion_text": f"拥堵系数 {effective_congestion:.2f}",
                    "is_cross_floor_transition": bool(
                        start_floor_id and end_floor_id and start_floor_id != end_floor_id
                    ),
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
            segment_layer = step["to_layer"] or step["from_layer"]
            segment_floor_id = step["to_floor_id"] or step["from_floor_id"]
            segment_floor_label = step["to_floor_label"] or step["from_floor_label"]
            edge_distance = step["distance_m"]
            edge_time_s = step["estimated_time_s"]

            if (
                segments
                and segments[-1]["layer"] == segment_layer
                and segments[-1].get("floor_id", "") == segment_floor_id
            ):
                segment = segments[-1]
                if segment["path"][-1] != step["from_node_id"]:
                    segment["path"].append(step["from_node_id"])
                segment["path"].append(step["to_node_id"])
                segment["target_node_id"] = step["to_node_id"]
                segment["target_node_name"] = step["to_node_name"]
                segment["display_layer"] = step["display_layer"]
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
                    "floor_id": segment_floor_id,
                    "floor_label": segment_floor_label,
                    "display_layer": step["display_layer"],
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

    def _build_route_overview(self, path, path_steps, segments, strategy, transport_mode, time_context=None):
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
                "floor_sequence": [],
                "cross_layer": False,
                "cross_layer_step_count": 0,
                "cross_floor_step_count": 0,
                "strategy": strategy,
                "weight_unit": "meter" if strategy == "shortest_distance" else "second",
                "transport_mode": transport_mode,
                "time_slot": (time_context or {}).get("time_slot", "normal"),
            }

        cross_layer_step_count = sum(
            1 for step in path_steps if step.get("transition_kind") == "cross_layer"
        )
        cross_floor_step_count = sum(
            1 for step in path_steps if step.get("is_cross_floor_transition")
        )
        layer_sequence = [segment["layer"] for segment in segments] or [self._resolve_node_layer(path[0])]
        floor_sequence = [
            segment.get("floor_label") or segment.get("floor_id") or segment["layer"]
            for segment in segments
        ] or [self._resolve_node_display_layer(path[0])]

        return {
            "start_node_id": path[0],
            "start_node_name": self._get_node_name(path[0]),
            "target_node_id": path[-1],
            "target_node_name": self._get_node_name(path[-1]),
            "node_count": len(path),
            "edge_count": len(path_steps),
            "segment_count": len(segments),
            "layer_sequence": layer_sequence,
            "floor_sequence": floor_sequence,
            "cross_layer": cross_layer_step_count > 0,
            "cross_layer_step_count": cross_layer_step_count,
            "cross_floor_step_count": cross_floor_step_count,
            "strategy": strategy,
            "weight_unit": "meter" if strategy == "shortest_distance" else "second",
            "transport_mode": transport_mode,
            "time_slot": (time_context or {}).get("time_slot", "normal"),
            "time_slot_label": (time_context or {}).get("label", self.TIME_SLOT_LABELS["normal"]),
            "dynamic_congestion": bool((time_context or {}).get("dynamic_congestion")),
        }

    def _get_weight(self, edge, strategy, transport_mode=None, from_node_id=None, time_slot="normal"):
        """
        根据当前策略计算边的权重。
        """
        if strategy == "shortest_distance":
            return edge.get("distance", float('inf'))
        elif strategy == "shortest_time":
            # 时间单位：秒 (distance: 米, ideal_speed: 米/秒)
            return self._get_travel_time_seconds(edge, transport_mode, from_node_id, time_slot)
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")

    def query_routing(
        self,
        start_node_id,
        target_node_id,
        strategy="shortest_distance",
        transport_mode=None,
        site_id=None,
        time_slot=None,
        departure_time=None,
    ):
        """
        完整路径查询接口
        :param start_node_id: 起点 ID
        :param target_node_id: 终点 ID
        :param strategy: 规划策略 ('shortest_distance' 或 'shortest_time')
        :param transport_mode: 交通方式，可选；未提供时表示不过滤
        :param site_id: 景区 ID，可选；未提供时默认使用当前图对象绑定景区
        :param time_slot: 出发时段，可选；normal/morning_peak/lunch_peak/evening_peak
        :param departure_time: 出发时间，可选；未传 time_slot 时可由 HH:MM 推断时段
        :return: 包含路径信息、总权重、距离、时间和分段信息的字典
        """
        time_context = self._resolve_time_context(time_slot=time_slot, departure_time=departure_time)
        resolved_time_slot = time_context["time_slot"]
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
                if not self._is_edge_allowed(edge, transport_mode, current_node):
                    continue

                neighbor = edge["to"]
                weight = self._get_weight(edge, strategy, transport_mode, current_node, resolved_time_slot)
                
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

        total_distance_m, estimated_time_s = self._summarize_path_metrics(
            path,
            path_edges,
            transport_mode,
            resolved_time_slot,
        )
        total_weight = distances[target_node_id]
        weight_unit = "meter" if strategy == "shortest_distance" else "second"
        path_steps = self._build_path_steps(path, path_edges, transport_mode, resolved_time_slot)
        segments = self._build_segments(path, path_steps)
        route_overview = self._build_route_overview(
            path,
            path_steps,
            segments,
            strategy,
            transport_mode,
            time_context,
        )

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
            "time_slot": resolved_time_slot,
            "departure_time": time_context["departure_time"],
            "time_context": time_context,
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
        time_slot=None,
        departure_time=None,
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
            time_slot=time_slot,
            departure_time=departure_time,
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
        time_slot=None,
        departure_time=None,
    ):
        """
        多目标路径基础版接口。

        当前实现思路：
        1. 先复用单目标最短路径，预计算起点和各目标点之间的最短路
        2. 再使用状态压缩 DP 搜索最优访问顺序
        3. 最后将各段最短路径拼接成完整路线
        """
        time_context = self._resolve_time_context(time_slot=time_slot, departure_time=departure_time)
        resolved_time_slot = time_context["time_slot"]
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
                "time_slot": resolved_time_slot,
                "departure_time": time_context["departure_time"],
                "time_context": time_context,
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
                    time_slot=resolved_time_slot,
                    departure_time=time_context["departure_time"],
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
                "time_context": route.get("time_context", time_context),
                "time_slot": route.get("time_slot", resolved_time_slot),
                "departure_time": route.get("departure_time", time_context["departure_time"]),
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
            "time_slot": resolved_time_slot,
            "departure_time": time_context["departure_time"],
            "time_context": time_context,
            "return_to_start": return_to_start,
            "segments": merged_segments,
            "leg_results": leg_results,
        }
