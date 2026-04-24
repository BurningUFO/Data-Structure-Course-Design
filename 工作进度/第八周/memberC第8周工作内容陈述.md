# memberC第8周工作内容陈述

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

---

## 三、本周提交物位置

| 类型 | 文件位置 | 说明 |
|------|---------|------|
| 全局景区列表 | `data/global_sites.json` | 注册 PKU 景区元信息 |
| 室外道路图 | `data/sites/PKU/outdoor.json` | 15 节点 + 28 边，含完整字段 |
| 室内图（图书馆） | `data/sites/PKU/indoor_LIB.json` | 9 节点 + 20 边，1F 布局 |
| 数据字典 v2.0 | `docs/数据字典.md` | 全字段定义 + 跨模块依赖表 |
| 联调问题跟踪表 | `工作进度/第八周/三模块联调问题跟踪表.md` | 见第五节 |

---

## 四、现有联调问题（待解决）

以下为本周检查发现的关键接口对齐问题：

| 编号 | 问题描述 | 涉及模块 | 优先级 | 建议方案 |
|------|---------|---------|--------|---------|
| 1 | `data/成员Cdata/scenic_spots.json` 中景点缺少 `node_id` 或 `map_node_id`，无法映射到图节点 | C → B | 高 | Member C 为景点数据补充图节点 ID 映射字段 |
| 2 | 新分层格式（nodes+edges 同文件）与旧 loader（分离文件）不兼容 | C → A | 高 | Member A 升级 loader 支持递归读取 `data/sites/` |
| 3 | `NodeWithEdges.json` 格式（节点内嵌邻接表）与标准 loader 期望的不一致 | C → A | 中 | 已废弃，以标准格式为准 |
| 4 | Member A `query_distance` 暂未包含 `site_id` 参数，无法区分景区 | A → B | 中 | Member A 确认是否需要分景区查询 |
| 5 | Member B 默认读取 `data/scenic_spots.json`，未指向新的分层路径 | B → C | 中 | Member C 在标准目录补充兼容路径或 Member B 更新加载路径 |

---

## 五、联调问题跟踪表

已整理至独立文件：

```text
工作进度/第八周/三模块联调问题跟踪表.md
```

包含完整的问题编号、描述、涉及模块、优先级、状态、建议方案和建议解决时间。

---

## 六、后续建议

- Member A 需要升级 `GraphLoader`，增加对合并格式 JSON（nodes + edges 同文件）和递归 `data/sites/` 目录的支持
- Member B 可考虑将景点加载路径从 `data/scenic_spots.json` 迁移到新分层路径，或保留兼容路径
- 景点数据（scenic_spots.json）的 `node_id` 映射字段需尽快补充，否则推荐系统无法计算真实距离
- `data/成员Cdata/` 的旧文件建议在联调确认无影响后清理
- 后续可扩展更多景区（如清华、故宫等）的分层数据，加入 `global_sites.json` 注册
