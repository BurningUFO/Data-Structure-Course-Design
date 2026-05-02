# memberB第9周工作内容陈述

> 本周角色：查找、排序、推荐与业务负责人（成员 B）  
> 提交时间：2026年5月2日  
> 核心目标：在不改动成员 A 路径接口的前提下，补齐第九周业务覆盖，并把演示入口、测试和说明材料收口到可直接验收状态。

---

## 1. 本周完成事项

### 1.1 场所查询入口落地

在现有 `search_and_recommend(...)` 主链路之上新增了明确的设施/场所查询入口 `search_places(...)`，默认继续使用标准分层数据 `data/global_sites.json` + `data/sites/{site_id}/`。

已支持：
- `restroom`、`catering`、`shopping`、`parking`、`education` 等类别过滤
- `distance_m`、`heat`、`rating` 三种排序
- 继续通过成员 A 距离适配层补真实路径距离，不修改 A 侧接口签名
- 中英文常见类别别名归一化，例如“洗手间/卫生间 -> restroom”，“食堂/餐饮 -> catering”

### 1.2 美食推荐链路落地

新增 `src/recommend/catering_service.py`，提供 `recommend_catering(...)` 业务入口，专门面向 `category="catering"` 的餐饮推荐场景。

已支持：
- Top-K 返回
- 关键词过滤
- 距离排序
- 可选 `cuisine` 过滤

说明：
- 当前标准数据里 `cuisine` 字段并不完整，因此本周采用“有字段就用、没有就回退到 `tags/keywords/name/description` 包含匹配”的最小兼容策略。

### 1.3 日记基础查询收口

在 `src/diary/` 对现有日记模块做了业务收口，保持默认标准数据 `data/diary_data.json` 不变，同时补上对历史 `data/成员Cdata/diary_test.json` 的读取兼容。

已支持：
- 标题精确查询
- 标题模糊查询
- 目的地查询
- 按 `heat` / `rating` 排序
- 统一 Response 风格返回

额外处理：
- 历史 `diary_test.json` 不是纯 JSON，实际被 Markdown 代码块包裹并带有额外内容；已补兼容解析逻辑
- 对不同来源的日记记录做统一字段归一化，避免测试和演示入口分别兜底

### 1.4 模糊查询增强

更新了 `src/search/fuzzy_search.py`，在维持轻量实现方向的前提下补强：
- 名称匹配高权重
- `keywords` / `tags` / `description` 分层权重
- 多字段同时命中加分
- 更稳定的排序规则：匹配分 -> 热度 -> 评分 -> 名称

本周明确未支持：
- 拼音首字母
- 同义词扩展
- 编辑距离阈值

### 1.5 演示入口扩展

扩展 `src/search/cli_demo.py`，新增：

```text
python -B src/search/cli_demo.py --week9
```

当前可直接演示：
1. 查询洗手间并按真实距离排序
2. 查询便利店 / 教学楼并按真实距离排序
3. 查询餐饮结果并返回 Top-K
4. 查询日记标题 / 目的地并展示排序结果
5. 从查询结果中直接打印可调用的成员 A 路径规划命令

---

## 2. 本周涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/search/exact_search.py` | 修改 | 补类别别名归一化 |
| `src/search/fuzzy_search.py` | 修改 | 补模糊匹配权重与稳定排序 |
| `src/search/search_service.py` | 修改 | 新增 `search_places(...)` 业务入口 |
| `src/search/cli_demo.py` | 修改 | 新增 `--week9` 演示入口 |
| `src/recommend/catering_service.py` | 新建 | 新增 `recommend_catering(...)` |
| `src/diary/diary_service.py` | 重构 | 收口标准数据 + 历史日记兼容 |
| `src/diary/__init__.py` | 修改 | 导出 `search_diaries` |
| `tests/test_search.py` | 修改 | 新增场所查询与模糊查询增强场景 |
| `tests/test_recommend.py` | 修改 | 新增餐饮推荐 Top-K / 距离 / 菜系过滤测试 |
| `tests/test_diary.py` | 重写 | 改为可直接 `python -B` 执行，并补旧日记兼容测试 |

---

## 3. 测试命令与结果

本周实际执行并通过：

```text
python -B tests/test_graph_load.py
python -B tests/test_routing.py
python -B tests/test_search.py
python -B tests/test_recommend.py
python -B tests/test_diary.py
python -B tests/test_integration.py
python -B src/search/cli_demo.py --week9
```

结果摘要：
- `tests/test_search.py`：通过
- `tests/test_recommend.py`：通过
- `tests/test_diary.py`：通过
- `tests/test_integration.py`：通过
- `tests/test_graph_load.py` / `tests/test_routing.py`：通过，确认未破坏 A/C 主链路

---

## 4. 可演示功能

推荐演示命令：

```text
python -B src/search/cli_demo.py --week9
```

该命令会依次展示：
- `restroom` 场所查询并按真实距离排序
- `shopping` / `education` 场所查询并打印 `target_node_id`
- `catering` Top-K 推荐并打印路径规划命令
- 日记标题查询、目的地查询及排序结果

如需单独走成员 A 的路径规划，可直接复制演示脚本打印出的 `python -B -c "...query_routing(...)"` 命令。

---

## 5. 当前限制

1. 模糊查询仍是轻量包含匹配方案，本周没有引入拼音首字母、同义词词典或编辑距离。
2. 餐饮推荐当前只基于 `name/tags/keywords/description/open_hours/category` 及可选 `cuisine` 字段，不包含菜单、价格、营业状态实时性等更细粒度信息。
3. 默认日记数据仍以标准 `data/diary_data.json` 为准；历史 `data/成员Cdata/diary_test.json` 只作为兼容输入，不作为新功能默认数据源。
4. 历史日记数据大多缺少 `destination_node_id`，因此“日记 -> 路径规划”在旧数据上只能部分演示；完整链路优先使用标准日记数据。

---

## 6. 对 C 数据依赖的当前说明

本次同步后，成员 C 已补齐：
- `data/sites/PKU/indoor_DORM1.json`
- `data/diary_data.json`
- `tests/test_integration.py`

因此成员 B 本周实现默认以标准数据为主，不再把旧 `成员Cdata` 作为默认入口。  
仅对 `data/成员Cdata/diary_test.json` 做了最小兼容读取，原因是周计划中提到过该文件，且其当前文件形态并不规范，直接读取会失败。

---

## 7. 下周建议

1. 若第10周继续扩展模糊查询，可优先做同义词和拼音缩写，再考虑编辑距离。
2. 若要增强餐饮推荐质量，建议先由成员 C 补齐 `cuisine`、`avg_price`、`open_status` 等标准字段。
3. 若要让“日记 -> 路径规划”更稳定，建议为更多校园日记补充 `destination_node_id`。
