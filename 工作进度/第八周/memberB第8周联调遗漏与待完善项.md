# memberB第8周联调遗漏与待完善项

> 本文档用于记录成员B在第八周系统联调过程中发现的接口、数据和链路缺口。当前内容已整理进 `memberB第8周工作内容陈述.md`，后续 A/C 更新接口或数据后可继续在本文档中更新状态。

## 一、当前待完善项

| 编号 | 类型 | 问题描述 | 影响范围 | 当前处理方式 | 需要协作对象 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| B8-001 | 接口差异 | 文档中的分层路径接口包含 `site_id`，但当前代码中的 `Router.query_distance` 实际签名为 `query_distance(start_node_id, target_node_id, strategy="shortest_distance")`，暂未包含 `site_id`。 | 成员B距离排序、后续分层景区/建筑内推荐 | 成员B已通过 `src/search/distance_adapter.py` 接入现有接口，不直接修改成员A接口；后续如 A 升级为分层接口，只需调整适配层。 | 成员A | B侧已适配，待A侧分层接口升级 |
| B8-002 | 数据缺字段 | 旧参考景点数据 `data/成员Cdata/scenic_spots.json` 仍缺少 `node_id` 或 `map_node_id`，无法直接映射到图节点。标准分层数据 `data/sites/PKU/*.json` 已提供全局唯一节点 `id`，成员B可直接将其作为 `node_id` 使用。 | 旧景点数据距离计算、历史兼容查询 | 成员B已将默认数据源切换到标准分层目录，并在加载时把节点 `id` 规范化为 `node_id`；旧参考数据若继续使用，仍会返回 `missing_node_id`。 | 成员C | 标准数据已可用，旧参考数据待补字段 |
| B8-003 | 分层格式兼容 | 原 `NodeWithEdges.json` 问题已废弃，但当前新的标准分层格式 `data/sites/PKU/*.json` 为 `nodes + edges` 同文件，成员A的 `GraphLoader.load_from_json(nodes_path, edges_path)` 仍不直接兼容。 | A 侧标准数据加载、B 侧默认距离图来源 | 成员B已在 `src/search/distance_adapter.py` 中适配标准分层格式，并在 B 侧补充门节点到室内入口的桥接边；成员A若要直接使用标准数据，仍需升级 loader。 | 成员A | B侧已适配，A侧待升级 |
| B8-004 | 距离不可达处理 | `query_distance` 对不可达或节点不存在返回 `float("inf")`，业务层需要统一转换为可展示状态，不能直接暴露给 CLI 用户。 | 推荐结果展示、Response 结构、测试断言 | 成员B已在 `src/search/search_service.py` 中通过 `attach_distance_fields` 统一转换为 `distance_m=None` 与 `distance_status`。 | 成员B | B侧已处理，待真实联调验证 |
| B8-005 | 数据目录未规范化 | 该问题已解决。标准数据已迁移到 `data/global_sites.json` 与 `data/sites/PKU/*.json`，成员B默认加载路径已切换到标准分层目录。旧参考目录 `data/成员Cdata/` 仅作历史兼容。 | 默认查询路径、CLI、测试数据口径 | 成员B已将默认查询数据源切换到标准分层目录；保留 `prefer_member_c_data=True` 仅用于兼容旧参考数据。 | 成员C | 已解决 |

## 二、整理状态

- 当前文档已完成第八周阶段性整理。
- 关键问题已同步写入 `工作进度/第八周/memberB第8周工作内容陈述.md`。
- 后续如果成员A更新分层距离接口，优先更新 B8-001。
- 后续如果成员C补充旧参考数据的 `node_id`，优先更新 B8-002。
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
| 成员A | 如果路由模块后续希望直接读取标准分层数据，需为 `data/sites/PKU/*.json` 提供原生 loader 或统一加载接口。 | 当前成员B已在适配层中兼容；若 A 侧补齐，后续联调口径会更统一。 |
| 成员C | 如果组内仍保留旧参考数据 `data/成员Cdata/scenic_spots.json` 作为演示或回归数据，需要补充 `node_id` 或 `map_node_id`。 | 没有节点 ID 时，成员B只能返回 `missing_node_id`，不能计算旧参考数据上的真实距离。 |
| 成员A/成员C | 若最终决定完全以标准分层数据为唯一数据源，需要同步在文档和协作说明中明确废弃旧 `scenic_spots.json` 的口径。 | 影响成员B是否继续保留 `prefer_member_c_data=True` 这条兼容路径。 |

## 六、成员B当前可交付联调入口

- 服务层入口：`src/search/search_service.py` 中的 `search_and_recommend(...)`。
- 距离适配入口：`src/search/distance_adapter.py` 中的 `build_distance_provider()`。
- CLI 演示入口：`src/search/cli_demo.py`。
- 测试入口：`tests/test_search.py` 与 `tests/test_recommend.py`。
