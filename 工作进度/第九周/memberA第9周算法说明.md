# memberA第9周算法说明

## 1. 模块范围

成员 A 本周负责图结构与路径规划相关能力的期中检查说明，覆盖：

- 单目标路径规划：`Router.query_routing(...)`
- 轻量距离查询：`Router.query_distance(...)`
- 多目标路径规划：`Router.query_multi_target(...)`
- 交通工具约束：`vehicle_access`、`allowed_transports`、`blocked_transports`
- 标准分层数据加载：`GraphLoader.load_site_graph(site_id="PKU")`

当前接口保持第八周联调结论不变：`site_id` 为可选参数，`shortest_distance` 返回米，`shortest_time` 返回秒。

---

## 2. 单目标路径规划：Dijkstra

### 2.1 输入

```python
query_routing(
    start_node_id,
    target_node_id,
    strategy="shortest_distance",
    transport_mode=None,
    site_id=None,
)
```

### 2.2 输出

成功时返回：

- `path`：节点路径。
- `total_weight`：当前策略下的最优权重。
- `weight_unit`：`meter` 或 `second`。
- `total_distance_m`：路径总距离，单位米。
- `estimated_time_s`：预计时间，单位秒。
- `segments`：按室外/室内层级拆分的路径段。

失败时返回：

- `success=False`
- `message`：失败原因，例如节点不存在、不可达、`site_id` 不匹配。

### 2.3 核心思路

使用邻接表存储图结构，并基于优先队列 `heapq` 实现 Dijkstra：

1. 将起点距离设为 0，其余节点设为无穷大。
2. 每次从优先队列中取出当前权重最小的节点。
3. 遍历该节点出边，根据策略计算边权。
4. 如果新路径更短，则更新距离表和前驱表。
5. 到达终点后回溯前驱表生成路径。

### 2.4 复杂度

设节点数为 `V`，边数为 `E`：

- 时间复杂度：`O((V + E) log V)`
- 空间复杂度：`O(V + E)`

该复杂度适合当前课程设计要求的百级节点和数百条边规模。

---

## 3. 最短时间权重

### 3.1 权重公式

边数据中使用：

- `distance`：距离，单位米。
- `ideal_speed`：理想速度，单位米/秒。
- `congestion`：拥挤系数。

时间权重计算为：

```text
time_seconds = distance / (ideal_speed * congestion)
```

若速度或拥挤系数小于等于 0，则该边时间视为不可用。

### 3.2 策略差异

- `shortest_distance`：边权直接取 `distance`，单位米。
- `shortest_time`：边权取通行时间，单位秒。

因此同一组起终点在不同策略下可能得到不同路径。

---

## 4. 多目标路径规划：状态压缩 DP

### 4.1 输入

```python
query_multi_target(
    start_node_id,
    target_node_ids,
    strategy="shortest_distance",
    transport_mode=None,
    return_to_start=True,
    site_id=None,
)
```

### 4.2 当前处理规则

- 自动忽略重复目标点。
- 自动忽略与起点相同的目标点。
- 空目标列表返回起点自身路径，`target_node_ids=[]`。
- 任一目标点不存在时直接失败。
- 若无法覆盖全部目标点，返回失败。
- 当前基础版最多支持 12 个目标点。

### 4.3 核心思路

1. 对起点和所有目标点两两调用 `query_routing(...)`，预计算点对点最短路径。
2. 用二进制 mask 表示已访问目标集合。
3. 状态 `dp[(mask, last_index)]` 表示已经访问 `mask` 中目标，且最后停在 `last_index` 目标时的最小代价。
4. 枚举下一个未访问目标并转移状态。
5. 若 `return_to_start=True`，最后额外加上回到起点的路径代价。
6. 根据 `parent` 表回溯得到访问顺序，再拼接各段路径。

### 4.4 复杂度

设目标点数量为 `n`：

- 点对点最短路预计算：`O(n^2 * (V + E) log V)`
- 状态压缩 DP：`O(n^2 * 2^n)`
- 空间复杂度：`O(n * 2^n + n^2)`

由于 DP 部分随目标数指数增长，当前限制 `n <= 12`，避免真实联调时出现性能不可控。

---

## 5. 交通工具约束

### 5.1 支持字段

当前边过滤逻辑兼容以下字段：

- `vehicle_access`：`all`、`pedestrian_only`、`vehicle_only`
- `allowed_transports`
- `transport_modes`
- `transport_mode`
- `blocked_transports`

### 5.2 过滤规则

- 未传 `transport_mode` 时不过滤，按通用路径规划处理。
- `transport_mode="walk"`、`"pedestrian"`、`"foot"` 不能走 `vehicle_only` 边。
- 非步行交通方式不能走 `pedestrian_only` 边。
- 若边声明 `blocked_transports`，对应交通方式不能通过。
- 若边声明 `allowed_transports` / `transport_modes` / `transport_mode`，只有列出的交通方式可以通过。

### 5.3 当前测试覆盖

本周新增测试验证：

- 步行路径会选择 `pedestrian_only` 路段。
- 车辆路径会选择 `vehicle_only` 路段。
- 自行车可通过 `allowed_transports=["bike"]` 的边。
- 不允许的交通工具不会错误使用受限边。

---

## 6. 标准分层数据与跨层路径

`GraphLoader.load_site_graph("PKU")` 当前可加载：

- `data/sites/PKU/outdoor.json`
- `data/sites/PKU/indoor_LIB.json`

加载后会将室外门节点与室内入口节点通过 `gate_link` 连接，使 `query_routing(...)` 可以直接搜索室外到室内的跨层路径。

路径结果中的 `segments` 会按 `outdoor`、`indoor_LIB` 等层级拆分，便于 B 侧或演示脚本展示“室外段”和“室内段”。

---

## 7. 第九周测试命令

```text
python -B tests/test_routing.py
python -B tests/test_graph_load.py
```

当前验证结果：

- `tests/test_routing.py`：13 项测试通过。
- `tests/test_graph_load.py`：旧样例图与标准 `PKU` 分层图加载均通过。

---

## 8. 当前限制与后续方向

1. 多目标路径当前采用精确状态压缩 DP，适合小规模目标点；若目标点数量继续增大，需要引入贪心、2-opt、A* 或分组启发式。
2. 当前交通工具过滤基于静态边字段，不包含实时道路状态或分时段管制。
3. 当前跨层路径已支持图书馆室内图，宿舍室内图是否补齐由成员 C 第九周数据一致性任务决定。
4. 当前路径结果为结构化数据，尚未接入图形化地图展示；期中检查阶段以 CLI 和测试输出演示为主。
