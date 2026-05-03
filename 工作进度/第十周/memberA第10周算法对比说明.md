# memberA第10周算法对比说明

## 1. 文档目的

第十周成员 A 的重点不是重写路径算法，而是在第九周接口稳定的前提下，开始为 M3 联调和后续验收准备：

1. 路径策略对比样例
2. 交通方式过滤样例
3. 日记目的地节点到路径规划链路
4. 可直接展示的路径明细字段

本说明基于当前仓库的标准 `PKU` 分层图与 `Router` 实现整理。

---

## 2. 本周新增的 A 侧展示字段

在 **不改动原有入参顺序** 的前提下，`query_routing(...)` 本周追加了以下非破坏性字段：

- `start_node_name` / `target_node_name`
- `path_node_names`
- `path_steps`
- `layer_sequence`
- `route_overview`

同时对 `segments` 追加了更适合业务层展示的字段：

- `segment_index`
- `start_node_name` / `target_node_name`
- `node_count` / `edge_count`
- `edge_names` / `edge_types`

这些字段的作用是让 B/C 侧在做全文检索结果展示、路径卡片渲染、室内外分段说明时，不必反复手动查节点名或自己推断跨层动作。

---

## 3. 对比样例一：最短距离 vs 最短时间

### 3.1 样例输入

```python
query_routing("gate_north", "lib_reception", strategy="shortest_distance")
query_routing("gate_north", "lib_reception", strategy="shortest_time")
```

### 3.2 实际结果

| 策略 | 路径 | 总距离 | 预计时间 | 特点 |
|------|------|--------|----------|------|
| `shortest_distance` | `gate_north -> square_center -> library -> lib_entrance -> lib_reception` | `120m` | `161.11s` | 边数更少，直达服务台 |
| `shortest_time` | `gate_north -> square_center -> library -> lib_entrance -> lib_self_serve -> lib_reception` | `123m` | `155.11s` | 距离略长，但馆内段更快 |

### 3.3 对比结论

1. **最短时间路径不一定更短，甚至可能更长。**
   当前标准图里，`shortest_time` 通过 `lib_self_serve` 绕行，虽然多走了 `3m`，但因为边的 `congestion` 与 `ideal_speed` 更优，总时间反而更少。

2. **第十周的策略对比可以直接使用真实图样例，不必只依赖合成测试图。**

3. **这类差异是后续算法对比材料的重要示例。**
   它能够解释为什么系统需要同时保留“最短距离”和“最短时间”两类策略，而不是简单统一成一种最短路。

---

## 4. 对比样例二：交通方式过滤

### 4.1 样例 A：步行可达，车辆不可达

```python
query_routing("gate_north", "library", transport_mode="walk")
query_routing("gate_north", "library", transport_mode="car")
```

实际结果：

- `walk`：成功，路径为 `gate_north -> square_center -> library`
- `car`：失败，返回“无法从起点到达终点。”

原因：

- `square_center -> library` 是 `pedestrian_only`
- 当前车辆模式不会通过纯步行边

### 4.2 样例 B：车辆可达，步行不可达

```python
query_routing("gate_east", "parking_lot", transport_mode="walk")
query_routing("gate_east", "parking_lot", transport_mode="car")
```

实际结果：

- `walk`：失败
- `car`：成功，路径为 `gate_east -> parking_lot`

原因：

- `gate_east -> parking_lot` 是 `vehicle_only`

### 4.3 对比结论

1. 当前交通工具过滤逻辑已经能稳定体现**可达性差异**。
2. 本周适合把“同一路径目标在不同交通方式下成功/失败”的现象整理成验收材料。
3. 当前规则仍是**静态边字段过滤**，不包含分时段管制或实时封路。

---

## 5. 对比样例三：日记目的地节点 -> 路径规划

### 5.1 样例来源

标准 `data/diary_data.json` 中，日记《农园食堂美食测评》对应：

- `destination = "北京大学"`
- `destination_node_id = "canteen"`

### 5.2 路径结果

```python
query_routing("gate_north", "canteen")
```

实际路径：

```text
gate_north -> square_center -> road_cross -> canteen
```

关键指标：

- 总距离：`135m`
- 预计时间：`173.41s`
- 终点名称：`农园食堂`

### 5.3 对比结论

1. 只要日记记录带有 `destination_node_id`，A 侧当前接口已经可以直接支撑“日记结果 -> 路径规划”链路。
2. 本周 Member A 不负责全文检索实现本身，但已经为 B/C 后续接入准备好了更适合展示的路径摘要字段。

---

## 6. 多目标路径的当前口径

本周没有改动 `query_multi_target(...)` 的核心求解策略，仍保持：

- 基于点对点最短路 + 状态压缩 DP
- 最多支持 `12` 个目标点
- 对重复目标、空目标、不可达目标已有稳定响应

第十周补充的是展示友好字段：

- `path_node_names`
- `visit_order_names`
- `leg_results[*].path_steps`
- `leg_results[*].route_overview`

这样做的目的不是改变算法，而是提前为后续多目标演示和文档整理减少业务层的二次处理成本。

---

## 7. 当前限制

1. `shortest_time` 仍基于静态 `congestion` 与 `ideal_speed` 计算，不包含实时动态权值。
2. `vehicle_only` 目前仍是基础口径，若后续要区分自行车、摆渡车、服务车，需要继续细化边字段语义。
3. 多目标路径仍为精确状态压缩 DP 基础版，大规模目标点需要启发式算法补充。
4. A 侧已经提供日记链路所需的路径接口，但全文检索命中逻辑和压缩模块仍属于 B/C 本周任务范围。
