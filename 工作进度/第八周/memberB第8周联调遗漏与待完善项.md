# memberB第8周联调遗漏与待完善项

> 本文档用于记录成员B在第八周系统联调过程中发现的接口、数据和链路缺口。当前内容已整理进 `memberB第8周工作内容陈述.md`，后续 A/C 更新接口或数据后可继续在本文档中更新状态。

## 一、当前待完善项

| 编号 | 类型 | 问题描述 | 影响范围 | 当前处理方式 | 需要协作对象 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| B8-001 | 接口差异 | 文档中的分层路径接口包含 `site_id`，但当前代码中的 `Router.query_distance` 实际签名为 `query_distance(start_node_id, target_node_id, strategy="shortest_distance")`，暂未包含 `site_id`。 | 成员B距离排序、后续分层景区/建筑内推荐 | 成员B已通过 `src/search/distance_adapter.py` 接入现有接口，不直接修改成员A接口；后续如 A 升级为分层接口，只需调整适配层。 | 成员A | B侧已适配，待A侧分层接口升级 |
| B8-002 | 数据缺字段 | `data/scenic_spots.json` 与 `data/成员Cdata/scenic_spots.json` 中景点数据已有 `id`、`name`、`category`、`heat`、`rating` 等推荐字段，但缺少 `node_id` 或 `map_node_id`，无法直接映射到图节点。 | 真实距离计算、按距离排序、CLI 距离展示 | 成员B先兼容处理：有节点 ID 才计算距离，没有则输出距离不可用状态；真实数据查询已通过 `prefer_member_c_data=True` 验证。 | 成员C | 待补字段 |
| B8-003 | 数据格式不一致 | `data/NodeWithEdges.json` 使用 `node_id` 和 `connected_nodes`，而当前成员A的 `GraphLoader.load_from_json(nodes_path, edges_path)` 期望 `id` 字段和独立 `edges` 数组。 | 真实图数据加载、距离计算联调 | 成员B暂不直接依赖该格式，优先使用当前 loader 可读取的 `map_nodes.json` 与 `map_edges.json`。 | 成员A、成员C | 待统一格式 |
| B8-004 | 距离不可达处理 | `query_distance` 对不可达或节点不存在返回 `float("inf")`，业务层需要统一转换为可展示状态，不能直接暴露给 CLI 用户。 | 推荐结果展示、Response 结构、测试断言 | 成员B已在 `src/search/search_service.py` 中通过 `attach_distance_fields` 统一转换为 `distance_m=None` 与 `distance_status`。 | 成员B | B侧已处理，待真实联调验证 |
| B8-005 | 数据目录未规范化 | 成员C真实景点数据当前位于 `data/成员Cdata/scenic_spots.json`，标准根目录 `data/scenic_spots.json` 仍只有 10 条样例数据，尚未完全合并为统一数据源。 | CLI 默认数据、联调数据口径、测试数据一致性 | 成员B在服务层中提供 `prefer_member_c_data=True` 显式接入成员C真实数据，待成员C后续规范化目录。 | 成员C | 待规范化 |

## 二、整理状态

- 当前文档已完成第八周阶段性整理。
- 关键问题已同步写入 `工作进度/第八周/memberB第8周工作内容陈述.md`。
- 后续如果成员A更新分层距离接口，优先更新 B8-001。
- 后续如果成员C补充 `node_id` 或规范化数据目录，优先更新 B8-002 与 B8-005。
- 后续如果图数据格式统一，优先更新 B8-003。

## 三、后续更新规则

- 发现接口不一致、数据字段缺失、节点无法映射、路径不可达等问题时，追加到“当前待完善项”表格。
- 如果问题已经通过 A/C 更新或 B 侧适配解决，将状态改为“已解决”并说明处理方式。
- 如果后续继续更新本文件，需要同步评估是否补充到 `memberB第8周工作内容陈述.md`。

## 四、当前联调确认结论

截至当前实现，成员B侧已经完成以下兼容处理：

- 已通过 `src/search/distance_adapter.py` 接入成员A当前版本的 `Router.query_distance(start_node_id, target_node_id, strategy)`。
- 已在 `src/search/search_service.py` 中提供统一服务层入口，支持真实数据查询、距离字段补充、Top-K 推荐和统一 Response。
- 已在 `src/recommend/ranking.py` 中将 `distance_m` 纳入推荐排序策略，距离排序默认按升序处理。
- 已在统一 Response 的 `metadata.distance.status_counts` 中统计 `available`、`missing_node_id`、`unreachable`、`distance_provider_missing`、`distance_error` 等状态。
- 已通过测试覆盖成员C真实景点数据查询、A 距离接口接入、缺少 `node_id`、不可达、禁用 provider、异常距离返回等场景。

## 五、仍需 A/C 后续补齐的内容

| 协作对象 | 需补齐内容 | 对成员B的影响 |
| --- | --- | --- |
| 成员A | 明确后续是否将 `query_distance` 升级为带 `site_id` 的分层接口。 | 如果升级，成员B只需调整 `distance_adapter.py`，服务层和 CLI 不需要大改。 |
| 成员A | 明确 `shortest_time` 返回值单位和是否需要同时返回距离与时间。 | 影响 Response 中 `distance_value`、`distance_m`、时间字段的最终命名。 |
| 成员C | 为景点/场所数据补充 `node_id` 或 `map_node_id`。 | 没有节点 ID 时，成员B只能返回 `missing_node_id`，不能计算真实距离。 |
| 成员C | 将 `data/成员Cdata/` 下真实数据规范化到标准 `data/` 目录，或更新数据字典说明。 | 影响 CLI 默认数据源和联调数据口径。 |
| 成员A/成员C | 统一 `NodeWithEdges.json` 与 `GraphLoader.load_from_json` 的数据格式。 | 影响后续使用真实图数据进行距离计算和联调。 |

## 六、成员B当前可交付联调入口

- 服务层入口：`src/search/search_service.py` 中的 `search_and_recommend(...)`。
- 距离适配入口：`src/search/distance_adapter.py` 中的 `build_distance_provider()`。
- CLI 演示入口：`src/search/cli_demo.py`。
- 测试入口：`tests/test_search.py` 与 `tests/test_recommend.py`。
