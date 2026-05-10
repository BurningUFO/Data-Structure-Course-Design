# memberA 第11周统筹清单

> 角色：Member A（图结构与路径规划负责人 / 本周协作统筹）
> 周期：2026-05-11 至 2026-05-17
> 目标：先统一三人对课程硬指标、接口冻结和主链路风险的理解，再进入并行实现。

---

## 1. 课程硬指标缺口

| 硬指标 | 当前核对结果 | 缺口判断 | 负责人 | 第11周动作 |
|--------|--------------|----------|--------|------------|
| `>=10` 用户样例 | `data/diary_data.json` 有 12 篇日记，但独立 `author_id` 约 7 个 | 未达标 | Member C | 补齐 10+ 用户样例，建议新增 `data/users.json` 并同步日记作者字段 |
| `200+` 推荐 / 查询对象 | `global_sites.json` 当前 1 个站点，旧景区对象约 48 条 | 未达标 | Member C | 明确“1 个深度导航核心站点 + 200+ 推荐对象”落库方案 |
| 20+ 建筑 / 景点 / 楼宇节点 | PKU 分层图约 34 节点，类别覆盖较全 | 基本可支撑，但需核验口径 | Member C + A | C 输出核验表，A 确认可路由节点和建筑节点口径 |
| 10+ 服务设施类别 | PKU 节点类别约 14 类，设施相关类别约 11 类 | 基本达标 | Member C | 写入课程要求核验记录 |
| 50+ 服务设施总数 | 当前标准站点节点数不足 50 | 未达标 | Member C | 扩展设施对象或明确核心站点 + 扩展对象统计口径 |
| 200+ 道路图边 | PKU 分层图约 66 条边 | 未达标 | Member C + A | C 扩展图边数据，A 准备 200+ 边性能验证方法 |
| 日记 CRUD / 评分 / 媒体占位 | 当前主要是查询和全文检索 | 未达标 | Member B + C | B 接 Web 入口，C 提供样例字段和数据 |
| AIGC 轻量演示 | 文档已有口径，Web 中未形成真实入口 | 未达标 | Member B + C | B 做预览入口，C 提供样例图片 / 文本 / 占位数据 |
| 课程要求核验脚本 | `tests/test_course_requirements.py` 尚不存在 | 未达标 | Member C | 第11周至少创建脚本或人工替代核验说明 |

---

## 2. 接口冻结项

### 2.1 Member A 对外接口

第11周第一轮冻结以下接口，不主动破坏已有参数顺序和字段语义：

```python
query_routing(
    start_node_id,
    target_node_id,
    strategy="shortest_distance",
    transport_mode=None,
    site_id=None,
)

query_distance(
    start_node_id,
    target_node_id,
    strategy="shortest_distance",
    transport_mode=None,
    site_id=None,
)

query_multi_target(
    start_node_id,
    target_node_ids,
    strategy="shortest_distance",
    transport_mode=None,
    return_to_start=True,
    site_id=None,
)
```

### 2.2 UI 和业务层优先消费字段

单目标路径稳定字段：

- `success`、`message`
- `site_id`
- `start_node_id`、`target_node_id`
- `start_node_name`、`target_node_name`
- `path`、`path_node_names`
- `total_weight`、`weight_unit`
- `total_distance_m`、`estimated_time_s`
- `total_distance`、`estimated_time`
- `strategy`、`transport_mode`
- `layer_sequence`
- `route_overview`
- `path_steps`
- `segments`

多目标路径稳定字段：

- `success`、`message`
- `site_id`
- `path`、`path_node_names`
- `visit_order`、`visit_order_names`
- `target_node_ids`
- `total_weight`、`weight_unit`
- `total_distance_m`、`estimated_time_s`
- `total_distance`、`estimated_time`
- `strategy`、`transport_mode`
- `return_to_start`
- `segments`
- `leg_results`

### 2.3 冻结规则

1. 业务层和 UI 缺展示字段时，优先追加字段，不重命名、不删除、不改变单位。
2. `shortest_distance` 的距离单位固定为米，`shortest_time` 的时间单位固定为秒。
3. 不可达、站点不匹配、节点不存在均返回 `success=False` 与可展示 `message`。
4. 公共字段变更必须先同步 `docs/项目代码骨架与职责划分.md`，再改代码和测试。

---

## 3. 本周主链路风险

| 风险 | 当前表现 | 影响 | 处理方式 |
|------|----------|------|----------|
| Web 多目标路径入口缺失 | 现有 Web API 只有 `/api/route` | 多目标路径不能从浏览器验收 | Member B 接 `/api/route/multi`，A 保持 `query_multi_target` 字段稳定 |
| Web 正式产品骨架不足 | UI 仍有 `Minimal Demo UI` 口径 | 第13周正式产品观感和入口不稳定 | Member B 升级首页、导航、帮助入口和状态管理 |
| 数据规模不足 | 200+ 对象、50+ 设施、200+ 边未达标 | 第13周数据验收风险高 | Member C 本周先给落库方案和核验表 |
| 课程核验脚本缺失 | `tests/test_course_requirements.py` 不存在 | 周末验收命令无法完整执行 | Member C 创建脚本，A/B 配合补断言 |
| 日记 CRUD / AIGC 未接入 Web | 当前主要是查询和全文检索 | 课程硬功能仍停留在文档口径 | Member B + C 补入口、样例和占位输出 |
| `py` 启动器不可用 | 当前环境运行 `py -3 -B ...` 失败 | 验证命令在不同机器上不一致 | 工作陈述记录 `python -B ...` 替代命令 |

---

## 4. Member A 本周落地动作

1. 冻结 `query_routing`、`query_distance`、`query_multi_target` 的参数和展示字段。
2. 补充多目标路径接口文档，明确 `visit_order_names`、`path_node_names`、`leg_results` 等 Web 展示字段。
3. 更新 `tests/test_routing.py`，覆盖标准站点多目标路径字段、单目标展示字段和不可达提示。
4. 等 Member C 数据扩展后，补 200+ 边规模下的路径性能验证记录。
5. 周末提交 `memberA第11周工作内容陈述.md`，记录测试命令、结果、阻塞和第12周计划。
