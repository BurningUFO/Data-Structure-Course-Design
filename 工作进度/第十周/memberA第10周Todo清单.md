# memberA第10周Todo清单

## 本周执行主线

- [x] 对齐第十周总计划，明确 Member A 本周交付边界
- [x] 保持 `query_routing(...)`、`query_distance(...)`、`query_multi_target(...)` 参数顺序不变
- [x] 为 `query_routing(...)` 追加非破坏性展示字段：
  - [x] `start_node_name` / `target_node_name`
  - [x] `path_node_names`
  - [x] `path_steps`
  - [x] `layer_sequence`
  - [x] `route_overview`
- [x] 为 `segments` 追加层内展示字段：
  - [x] `segment_index`
  - [x] `start_node_name` / `target_node_name`
  - [x] `node_count` / `edge_count`
  - [x] `edge_names` / `edge_types`
- [x] 为 `query_multi_target(...)` 追加名称类辅助字段：
  - [x] `path_node_names`
  - [x] `visit_order_names`
  - [x] `leg_results[*].path_steps`
  - [x] `leg_results[*].route_overview`
- [x] 在标准 `PKU` 图上确认真实策略对比样例
- [x] 补充 `tests/test_routing.py`，覆盖：
  - [x] 路径展示字段结构
  - [x] 标准图上的距离/时间策略差异
  - [x] 标准图上的交通方式过滤差异
  - [x] 日记目的地节点到路径规划的可路由性
- [x] 同步更新 `docs/项目代码骨架与职责划分.md`
- [x] 输出第十周算法对比草稿与工作陈述

## 本周交付物

- `src/routing/router.py`
- `tests/test_routing.py`
- `docs/项目代码骨架与职责划分.md`
- `工作进度/第十周/memberA第10周算法对比说明.md`
- `工作进度/第十周/memberA第10周工作内容陈述.md`

## 仍需组内协作确认

- [ ] Member B 接入全文检索后，是否直接消费 `path_steps`，还是先只使用 `route_overview`
- [ ] Member C 的全文检索结果中，缺少 `destination_node_id` 的日记记录在业务层如何降级展示
- [ ] 若第十一周需要更细的交通工具语义，是否要继续拆分 `vehicle_only`、`bike_only`、`service_vehicle_only`
