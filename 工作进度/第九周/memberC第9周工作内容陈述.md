# memberC第9周工作内容陈述

> **本周角色**：数据、测试、系统集成负责人（成员C）  
> **提交时间**：2026年5月2日  
> **核心目标**：M2 期中检查准备 — 数据一致性修复 + 日记模块创建 + 集成测试覆盖

---

## 1. 本周完成事项

### 1.1 数据一致性修复 — 补齐 `indoor_DORM1`

**问题**：`data/global_sites.json` 中 PKU 的 `sub_graphs` 声明了 `["outdoor", "indoor_LIB", "indoor_DORM1"]`，但 `data/sites/PKU/` 下实际只有 `outdoor.json` 和 `indoor_LIB.json`，缺少 `indoor_DORM1.json`。

**解决方案**：选择**补齐方案**，创建了学生宿舍1号楼室内图数据。

**涉及变更**：
- **新建** `data/sites/PKU/indoor_DORM1.json` — 包含宿舍一楼室内图，共 10 个节点、18 条双向边
  - 节点类型：入口大厅、走廊、4个宿舍房间（101-104）、楼梯间、洗衣房、公共卫生间、公共活动室
  - 所有边符合标准分层图格式（含 congestion、ideal_speed、vehicle_access 字段）
- **修改** `data/sites/PKU/outdoor.json` — 将 `dormitory_1` 节点的 `sub_graph_id` 从 `null` 改为 `"indoor_DORM1"`
- **更新** `docs/数据字典.md` — 目录结构中补充 `indoor_DORM1.json`

**验证结果**：`test_graph_load.py` 加载通过，PKU 图节点数增至 34 个。

### 1.2 日记模块创建

在 `src/diary/` 下实现了日记基础查询服务，支持：
- 按标题精确查询 / 模糊查询
- 按目的地查询（精确 / 模糊）
- 按热度、评分、浏览量、创建时间排序
- 统一输出风格（复用成员B `build_success_response`）
- `search_diaries(...)` 快速调用入口

**涉及文件**：
- **新建** `src/diary/__init__.py` — 模块入口
- **新建** `src/diary/diary_service.py` — 日记查询服务（含 `DiaryService` 类和 `search_diaries` 函数）
- **新建** `data/diary_data.json` — 12 篇日记测试数据（含北京大学、黄山、故宫、泰山、西湖等目的地）

### 1.3 日记测试

**新建** `tests/test_diary.py` — 16 项测试覆盖：
- DiaryService 基本加载
- 标题精确/模糊查询、空标题边界
- 目的地精确/模糊查询
- 通用 `search_diaries` 入口（正常/无匹配）
- 按热度/评分/浏览量排序
- limit 限制
- 自定义路径加载、reload 功能

### 1.4 集成测试

**新建** `tests/test_integration.py` — 17 项集成测试覆盖以下场景：

| 序号 | 测试场景 | 说明 |
|------|---------|------|
| 1 | 标准 PKU 分层图加载 | 验证 indoor_DORM1 加载正确 |
| 2 | Router 创建 | 基础对象创建 |
| 3 | 单目标路径规划 | gate_north → library |
| 4 | 跨层路径规划 | 室外 → 图书馆室内 |
| 5 | 多目标路径 | 3个目标点 + 返回起点 |
| 6 | 空目标列表边界 | 返回起点自身 |
| 7 | 不可达目标 | 稳定返回失败 |
| 8 | 宿舍跨层路径 | outdoor → indoor_DORM1 室内 |
| 9 | 轻量距离查询 | gate_north → library |
| 10 | 场所查询 + 真实距离排序 | 查询洗手间按距离排序 |
| 11 | 美食推荐 | 类别过滤（catering） |
| 12 | 类别过滤 | 教育类节点查询 |
| 13 | 日记目的地查询 | 按"北京大学"查询 |
| 14 | 日记标题查询 | 按"黄山"模糊查询 |
| 15 | 日记评分排序 | 验证降序排列 |
| **16** | **完整端到端链路** | **查询→推荐→距离→路径规划** |
| **17** | **日记→路径规划链路** | **日记目的地→路径规划** |

---

## 2. 本周涉及文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `data/sites/PKU/indoor_DORM1.json` | **新建** | 宿舍1号楼室内图数据（10节点，18边） |
| `data/sites/PKU/outdoor.json` | **修改** | dormitory_1 sub_graph_id → "indoor_DORM1" |
| `data/diary_data.json` | **新建** | 12篇日记测试数据 |
| `src/diary/__init__.py` | **新建** | 日记模块入口 |
| `src/diary/diary_service.py` | **新建** | 日记查询服务 |
| `tests/test_diary.py` | **新建** | 16项日记模块测试 |
| `tests/test_integration.py` | **新建** | 17项集成测试 |
| `docs/数据字典.md` | **修改** | 补充 indoor_DORM1 和 diary_data.json |

---

## 3. 测试结果

### 3.1 已有测试（未破坏）

```text
python -B tests/test_graph_load.py    ✓ 通过（旧图 + 标准PKU分层图）
python -B tests/test_routing.py       ✓ 通过（13项测试，成员A已有）
```

### 3.2 新增测试

```text
python -B tests/test_diary.py         ✓ 通过（16项测试）
python -B tests/test_integration.py   ✓ 通过（17项集成测试）
```

### 3.3 分成员说明

| 测试文件 | 所属成员 | 测试项数 | 结果 |
|---------|---------|---------|------|
| test_graph_load.py | 成员A | 2 | ✓ |
| test_routing.py | 成员A | 13 | ✓ |
| test_diary.py | **成员C** | **16** | ✓ |
| test_integration.py | **成员C** | **17** | ✓ |

注：`tests/test_search.py` 和 `tests/test_recommend.py` 为成员B负责的测试文件，当前未运行。

---

## 4. 可演示功能

以下是成员C负责或参与的可演示功能点：

1. **跨层路径**：从北大西门 → 宿舍101房间（室外→室内跨层，验证 indoor_DORM1 补齐）
2. **场所查询+真实距离**：从西门出发查询洗手间，按真实路径距离排序
3. **美食推荐**：查询餐饮设施，按热度排序
4. **目的地日记查询**：查询"北京大学"相关日记
5. **完整演示链路**：查询图书馆 → 推荐展示 → 路径规划（完整端到端）

**演示命令示例**：

```text
# 演示1：宿舍跨层路径
python -B -c "
from src.graph.loader import GraphLoader
from src.routing.router import Router
g = GraphLoader.load_site_graph('PKU')
r = Router(g)
print(r.query_routing('gate_north', 'dorm1_room_101'))
"

# 演示2：日记查询
python -B -c "
from src.diary.diary_service import search_diaries
print(search_diaries(destination='北京大学', sort_field='rating', limit=3))
"

# 演示3：集成测试全链路
python -B tests/test_integration.py
```

---

## 5. 当前限制

1. **日记模块目前仅支持基础查询**（标题精确/模糊、目的地查询、排序），全文检索（倒排索引）和哈夫曼压缩计划在第10-11周完成。
2. **indoor_DORM1 仅包含一楼数据**（入口大厅、走廊、4间宿舍、洗衣房、卫生间、活动室），楼上楼层和更多宿舍楼（2号楼等）尚未覆盖。
3. **日记数据目前为静态测试数据**（12篇），后续可补充更多真实数据。
4. **集成测试未覆盖模糊查询增强场景**（拼音首字母、同义词扩展），该功能为成员B负责。
5. **未安装 pytest**，测试通过手动运行验证。如需使用 pytest 运行，需先安装。

---

## 6. 下周建议（第10周）

1. **日记全文检索**：在 `src/diary/` 下实现倒排索引全文检索
2. **哈夫曼压缩/解压**：实现 `src/compress/` 模块的基本压缩功能
3. **更多集成测试**：覆盖日记全文检索 + 压缩解压链路
4. **数据字典维护**：根据新模块更新数据字典
5. **联调支持**：协助成员B接入日记全文检索和压缩模块
