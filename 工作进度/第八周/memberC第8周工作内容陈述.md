# memberC第8周工作内容陈述（补充版）

## 一、本周任务目标
第八周成员 C 的核心任务是完成"数据规范化、字典升级、联调主导"三大件。在第七周独立完成数据准备和单元测试的基础上，本周必须将分散的数据整合到标准分层结构中，更新数据字典以对齐 A/B 模块接口依赖，并牵头启动三模块联调。

本周核心目标如下：
```
数据目录规范化（紧急） -> 数据字典 v2.0 -> 补充缺失字段 -> 主导 A/B 联调 -> 记录问题跟踪表
```

---

## 二、本周完成内容

### 1. 规范数据目录（紧急）
将第七周临时存放的数据按照分层架构标准进行规范化整理。

**新增标准数据文件：**

| 文件 | 说明 |
|------|------|
| `data/global_sites.json` | 全局景区列表，注册 PKU（北京大学）景区元信息 |
| `data/sites/PKU/outdoor.json` | 北京大学室外道路图 |
| `data/sites/PKU/indoor_LIB.json` | 图书馆室内图（1F） |

**周中遗留文件状态：**
- `data/成员Cdata/` 目录下的 `scenic_spots.json`、`NodeWithEdges.json`、`diary_test.json` 保留作参考，新开发以标准目录为准。

#### outdoor.json 详情

| 项目 | 数量 |
|------|------|
| 节点总数 | 15 |
| 边（双向） | 28 条（14 对） |
| 门节点（Gate） | 8 个 |
| 节点类型覆盖 | entrance, building, facility, landmark, intersection, dormitory |
| 设施覆盖 | 校门（3）、教学楼（2）、图书馆、食堂、宿舍、便利店、体育场、停车场、洗手间（2） |

#### indoor_LIB.json 详情

| 项目 | 数量 |
|------|------|
| 节点总数 | 9 |
| 边（双向） | 20 条（10 对） |
| 门节点 | 1 个（lib_entrance） |
| 节点类型覆盖 | hall, service, reading_room, facility, staircase, elevator |

#### 数据质量控制
- ✅ 所有 24 个节点 ID 全局唯一，跨图不重复
- ✅ 所有边均已双向存储，无单向遗漏
- ✅ 室外 library 节点 `is_gate=true`，`sub_graph_id="indoor_LIB"`，与室内 `lib_entrance` 锚点匹配
- ✅ 所有边包含 `vehicle_access` 字段（值域：all / pedestrian_only / vehicle_only）
- ✅ 所有边包含 `type` 字段（outdoor_road / indoor_path / elevator / stairs）
- ✅ 洗手间节点增加 `is_indoor` 和 `indoor_building` 字段，支持 Member B 室内查询场景

### 2. 更新数据字典（v2.0）
`docs/数据字典.md` 完成全面升级，内容变化如下：

**新增内容：**
- 正式目录结构规范（含全局景区、分层图目录树）
- 全局景区列表 `global_sites.json` 完整字段定义
- 节点字段完整表格：含 `id`, `name`, `type`, `is_gate`, `sub_graph_id`, `tags`, `description`, `category`, `facilities`, `open_hours`, `location`, `capacity`, `is_indoor`, `indoor_building`
- 边字段完整表格：含 `from`, `to`, `distance`, `type`, `congestion`, `ideal_speed`, `vehicle_access`（第八周新增）, `name`, `description`
- 跨模块数据依赖关系表：分别列出 Member A 和 Member B 对各字段的依赖
- 门节点命名规范
- 边双向性要求
- 历史清理说明

### 3. 补充字段适配（面向 A/B 模块需求）

#### 面向 Member A（图结构/路径规划）
- 室外图中为所有边增加了 `vehicle_access` 字段，支持 Member A 第八周的交通工具过滤逻辑开发
- 边 `type` 字段已准备就绪，支持 Member A 区分不同道路类型
- `congestion` 和 `ideal_speed` 字段已沿用，支持 Member A 时间策略权重计算

#### 面向 Member B（搜索推荐）
- 室外图中洗手间节点（`toilet_lib_area`, `toilet_sports_area`）增加了 `is_indoor` 和 `indoor_building` 字段，支持 Member B 室内洗手间查询场景
- 所有室外节点包含 `tags`、`category`、`description` 字段，可供 Member B 模糊搜索匹配
- `category` 值域统一（entrance / education / dormitory / catering / shopping / sports / landmark / restroom / parking / road 等）

### 4. 三模块联调前置准备
已进行以下联调检查：

**与 Member A 的接口对齐：**
- 确认 loader 当前 `load_from_json()` 期望的格式是分离的 `map_nodes.json` + `map_edges.json`（第五周样例）
- 新分层数据格式为合并格式（nodes+edges 同一文件），确认 loader 需要升级支持递归读取 `data/sites/` 目录
- 门节点 `sub_graph_id` 命名与文件名一致（如 `indoor_LIB`），符合分层架构约定

**与 Member B 的接口对齐：**
- Member B `search_service.py` 读取景点数据的默认路径为 `data/scenic_spots.json`，对应老格式
- 新分层数据中景点信息分散到 `data/sites/PKU/outdoor.json` 的节点中，Member B 需要适配新的加载源
- 不保留 `data/成员Cdata/` 下的 `scenic_spots.json` 为标准路径，建议 Member B 使用新分层文件或保留兼容路径

### 5. 【本次补充】完善 scenic_spots.json 数据字段（04-26）

针对联调跟踪表中 **C-001** 遗留问题，本次完成以下补充工作：

#### 5.1 补充 map_node_id 映射字段

为 `data/成员Cdata/scenic_spots.json` 全量补充 `map_node_id` 字段，**彻底锁定历史兼容口径**：

| 条目类型 | map_node_id 取值 | 说明 |
|----------|----------------|------|
| 全国景区（poi_021 ~ poi_065） | `null` | 未纳入校园图，无法计算真实距离；B 侧遇到 null 应返回 `"missing_node_id"` 而非异常 |
| 校园节点（pku_001 ~ pku_005，新增） | `"node_001"` ~ `"node_005"` | 已映射到校园图，支持真实距离计算 |

**新增校园条目（pku_001~pku_005）说明：**

| id | name | map_node_id |
|----|------|-------------|
| pku_001 | 图书馆 | node_002 |
| pku_002 | 第一教学楼 | node_003 |
| pku_003 | 学生宿舍1 | node_004 |
| pku_004 | 校内便利店 | node_005 |
| pku_005 | 北门 | node_001 |

#### 5.2 清理重复数据

同步清理了原数据中的重复条目（问题 C-008）：

| 保留 | 删除 | 原因 |
|------|------|------|
| poi_031（鼓浪屿） | poi_045（鼓浪屿，重复） | ID 不同但内容完全一致 |
| poi_042（西递） | poi_047（西递古村落，重复） | 同一景区的重复录入 |

#### 5.3 destination 字段历史口径锁定（C-007 结案）

旧数据中的 `destination` 字段**不参与任何路径/距离计算**。该字段仅保留历史参考价值。

**已写死的协作说明（见联调跟踪表第四节）：**
- 如后续要做日记/目的地推荐链路，需为相应条目补充 `map_node_id`，并在 `docs/数据字典.md` 中注明
- **`data/成员Cdata/scenic_spots.json` 定性为"仅历史兼容"**，不再作为任何新开发的标准数据源
- 以上口径全组对齐，不再变更

---

## 三、本周提交物位置

| 类型 | 文件位置 | 说明 |
|------|---------|------|
| 全局景区列表 | `data/global_sites.json` | 注册 PKU 景区元信息 |
| 室外道路图 | `data/sites/PKU/outdoor.json` | 15 节点 + 28 边，含完整字段 |
| 室内图（图书馆） | `data/sites/PKU/indoor_LIB.json` | 9 节点 + 20 边，1F 布局 |
| 数据字典 v2.0 | `docs/数据字典.md` | 全字段定义 + 跨模块依赖表 |
| 补充后的景点数据 | `data/成员Cdata/scenic_spots.json` | 补充 map_node_id 字段，去重，新增 pku 条目，锁定历史兼容口径 |
| 联调问题跟踪表 | `工作进度/第八周/三模块联调问题跟踪表.md` | C-001 已解决，C-007 口径锁定，C-008 去重记录 |

---

## 四、现有联调问题（更新后状态）

所有高/中优先级问题已全部解决，当前无阻塞项。

| 编号 | 状态 | 说明 |
|------|------|------|
| C-001 | ✅ 已解决 | scenic_spots.json 已全量补充 map_node_id |
| C-002 | ✅ 已解决 | Member A 完成 loader 升级 |
| C-003 | ✅ 已废弃 | 旧格式已废弃 |
| C-004 | ✅ 已解决 | Member A 增加 site_id 参数 |
| C-005 | ✅ 已解决 | Member B 兼容新路径 |
| C-006 | ✅ 已解决 | Member A 实测跨层路径 |
| C-007 | ✅ 口径锁定 | destination 字段历史兼容，不接入路径计算 |
| C-008 | ✅ 已清理 | 重复条目已去重 |

---

## 五、后续建议
- Member B 调用 `query_distance` 时需先检查 `map_node_id` 是否为 null，null 值返回 `"missing_node_id"` 而非抛异常
- 后续扩展更多校园景点时，需同时在 `scenic_spots.json` 添加对应 pku_xxx 条目并映射 `map_node_id`
- `data/成员Cdata/` 下的旧文件可在联调全部贯通后申请大总管确认清理

---

> 📅 本周工作时间：4月20日 - 4月26日
> 📝 记录人：成员C
> 🔄 最后更新：2026-04-26（补充 scenic_spots.json map_node_id 字段及历史口径锁定）
