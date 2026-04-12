import heapq

class Router:
    """
    路径规划核心类，基于 Dijkstra 算法实现。
    """
    def __init__(self, graph):
        self.graph = graph

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

    def query_routing(self, start_node_id, target_node_id, strategy="shortest_distance"):
        """
        完整路径查询接口
        :param start_node_id: 起点 ID
        :param target_node_id: 终点 ID
        :param strategy: 规划策略 ('shortest_distance' 或 'shortest_time')
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
            "segments": [
                {
                    "layer": getattr(self.graph, 'layer_id', 'default'),
                    "path": path,
                    "distance": distances[target_node_id] if strategy == "shortest_distance" else None
                }
            ]
        }

    def query_distance(self, start_node_id, target_node_id, strategy="shortest_distance"):
        """
        轻量级查询接口，专供 Member B 推荐系统排序使用。
        :return: 仅返回两点之间的最短距离/时间的数值。不可达则返回 infinity。
        """
        result = self.query_routing(start_node_id, target_node_id, strategy)
        if result["success"]:
            return result["total_weight"]
        return float('inf')
