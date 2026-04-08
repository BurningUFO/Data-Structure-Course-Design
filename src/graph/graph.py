class Graph:
    """
    分层图结构类
    """
    def __init__(self, layer_id="root", name="Global"):
        self.layer_id = layer_id
        self.name = name
        # 节点信息: { node_id: { "name": str, "type": str, ... } }
        self.nodes = {}
        # 邻接表: { start_node_id: [ { "to": target_id, "distance": float, ... }, ... ] }
        self.adj = {}
        # 子图引用: { parent_node_id: GraphObject }
        # 例如: 某个建筑节点作为 ID，其对应的内部地图作为 Graph 对象
        self.sub_graphs = {}

    def add_node(self, node_id, **kwargs):
        self.nodes[node_id] = kwargs
        if node_id not in self.adj:
            self.adj[node_id] = []

    def add_sub_graph(self, parent_node_id, sub_graph):
        """将子图（如室内）挂载到父级点位（如建筑大门）"""
        self.sub_graphs[parent_node_id] = sub_graph

    def add_edge(self, u, v, distance, **kwargs):
        edge_info = {"to": v, "distance": distance}
        edge_info.update(kwargs)
        if u not in self.adj: self.adj[u] = []
        self.adj[u].append(edge_info)

    def find_node_recursive(self, node_id):
        """递归查找节点，返回 (NodeData, GraphContext)"""
        if node_id in self.nodes:
            return self.nodes[node_id], self
        for sub in self.sub_graphs.values():
            res = sub.find_node_recursive(node_id)
            if res: return res
        return None

    def __str__(self):
        sub_info = f", {len(self.sub_graphs)} sub-graphs" if self.sub_graphs else ""
        return f"Layer[{self.layer_id}]: {len(self.nodes)} nodes{sub_info}"
