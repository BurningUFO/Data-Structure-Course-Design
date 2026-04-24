# memberB第8周联调遗漏与待完善项

> 本文档用于记录成员B在第八周系统联调过程中发现的接口、数据和链路缺口。当前内容已整理进 `memberB第8周工作内容陈述.md`，后续 A/C 更新接口或数据后可继续在本文档中更新状态。

## 一、当前待完善项

| 编号 | 类型 | 问题描述 | 影响范围 | 当前处理方式 | 需要协作对象 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| B8-001 | 接口差异 | 该问题已解决。成员A已将 `site_id` 作为 `query_distance`、`query_routing`、`query_multi_target` 的可选参数放在参数末尾；不传时兼容旧调用方式，传入时会校验与当前图绑定景区是否一致。 | 成员B距离排序、后续分层景区/建筑内推荐 | 成员B当前 `src/search/distance_adapter.py` 已按新接口传入 `site_id`，旧业务调用链不需要改动。 | 成员A | 已解决 |
| B8-002 | 数据缺字段 | 旧参考景点数据 `data/成员Cdata/scenic_spots.json` 仍缺少 `node_id` 或 `map_node_id`，无法直接映射到图节点。标准分层数据 `data/sites/PKU/*.json` 已提供全局唯一节点 `id`，成员B可直接将其作为 `node_id` 使用。 | 旧景点数据距离计算、历史兼容查询 | 成员B已将默认数据源切换到标准分层目录，并在加载时把节点 `id` 规范化为 `node_id`；旧参考数据若继续使用，仍会返回 `missing_node_id`。 | 成员C | 标准数据已可用，旧参考数据待补字段 |
| B8-003 | 分层格式兼容 | 该问题已解决。成员A已新增 `GraphLoader.load_site_graph(site_id=...)`，可原生读取 `data/sites/{site_id}/*.json` 的标准分层图数据，并已通过 `PKU` 实测。 | A 侧标准数据加载、B 侧默认距离图来源 | 成员B当前 `src/search/distance_adapter.py` 已切到 A 侧原生 loader，并通过标准分层数据和跨层路径测试。 | 成员A | 已解决 |
| B8-004 | 距离不可达处理 | `query_distance` 对不可达或节点不存在返回 `float("inf")`，业务层需要统一转换为可展示状态，不能直接暴露给 CLI 用户。 | 推荐结果展示、Response 结构、测试断言 | 成员B已在 `src/search/search_service.py` 中通过 `attach_distance_fields` 统一转换为 `distance_m=None` 与 `distance_status`，并已通过联调测试验证。 | 成员B | 已解决 |
| B8-005 | 数据目录未规范化 | 该问题已解决。标准数据已迁移到 `data/global_sites.json` 与 `data/sites/PKU/*.json`，成员B默认加载路径已切换到标准分层目录。旧参考目录 `data/成员Cdata/` 仅作历史兼容。 | 默认查询路径、CLI、测试数据口径 | 成员B已将默认查询数据源切换到标准分层目录；保留 `prefer_member_c_data=True` 仅用于兼容旧参考数据。 | 成员C | 已解决 |

## 二、整理状态

- 当前文档已完成第八周阶段性整理。
- 关键问题已同步写入 `工作进度/第八周/memberB第8周工作内容陈述.md`。
- 后续如果成员C补充旧参考数据的 `node_id`，优先更新 B8-002。
- 若后续完全废弃旧参考景点数据，更新 B8-002 的兼容说明即可。

## 三、后续更新规则

- 发现接口不一致、数据字段缺失、节点无法映射、路径不可达等问题时，追加到“当前待完善项”表格。
- 如果问题已经通过 A/C 更新或 B 侧适配解决，将状态改为“已解决”并说明处理方式。
- 如果后续继续更新本文件，需要同步评估是否补充到 `memberB第8周工作内容陈述.md`。

## 四、当前联调确认结论

截至当前实现，成员B侧已经完成以下兼容处理：

- 已通过 `src/search/distance_adapter.py` 接入成员A当前版本的 `Router.query_distance(..., site_id=...)`，并兼容旧调用方式。
- 已确认成员A的 `query_routing(..., site_id=...)` 与 `query_multi_target(..., site_id=...)` 也已完成可选 `site_id` 支持。
- 已确认 `shortest_time` 返回单位为秒，`query_routing` 会同时返回 `total_distance_m` 与 `estimated_time_s`，并兼容旧字段 `total_distance` 与 `estimated_time`。
- 已在 `src/search/search_service.py` 中提供统一服务层入口，支持真实数据查询、距离字段补充、Top-K 推荐和统一 Response。
- 已在 `src/recommend/ranking.py` 中将 `distance_m` 纳入推荐排序策略，距离排序默认按升序处理。
- 已在统一 Response 的 `metadata.distance.status_counts` 中统计 `available`、`missing_node_id`、`unreachable`、`distance_provider_missing`、`distance_error` 等状态。
- 已通过测试覆盖成员C真实景点数据查询、A 距离接口接入、缺少 `node_id`、不可达、禁用 provider、异常距离返回等场景；同时已验证标准分层图加载与跨层路径可达。

## 五、仍需 A/C 后续补齐的内容

| 协作对象 | 需补齐内容 | 对成员B的影响 |
| --- | --- | --- |
| 成员C | 如果组内仍保留旧参考数据 `data/成员Cdata/scenic_spots.json` 作为演示或回归数据，需要补充 `node_id` 或 `map_node_id`。 | 没有节点 ID 时，成员B只能返回 `missing_node_id`，不能计算旧参考数据上的真实距离。 |
| 成员A/成员C | 若最终决定完全以标准分层数据为唯一数据源，需要同步在文档和协作说明中明确废弃旧 `scenic_spots.json` 的口径。 | 影响成员B是否继续保留 `prefer_member_c_data=True` 这条兼容路径。 |
| 成员C | 如果后续继续推进日记/目的地推荐链路，需要为旧景点数据中的 `destination` 字段补充到图节点的映射关系。 | 影响后续 diary 场景是否能直接复用当前距离与路径链路。 |

## 六、成员B当前可交付联调入口

- 服务层入口：`src/search/search_service.py` 中的 `search_and_recommend(...)`。
- 距离适配入口：`src/search/distance_adapter.py` 中的 `build_distance_provider()`。
- CLI 演示入口：`src/search/cli_demo.py`。
- 测试入口：`tests/test_search.py` 与 `tests/test_recommend.py`。
