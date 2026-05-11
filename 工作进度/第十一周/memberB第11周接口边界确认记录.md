# memberB第11周接口边界确认记录

> 任务阶段：任务 1，启动对齐与接口边界确认
> 确认日期：2026-05-11
> 成员 B 范围：Web 主入口、业务服务层、查询 / 推荐 / 日记 / AIGC 页面接入与测试

---

## 1. 本次核对依据

已核对的文档与代码：

- `工作进度/第十一周/第十一周具体工作任务要求.md`
- `工作进度/第十一周/第十一周三人协作方式.md`
- `docs/项目代码骨架与职责划分.md`
- `docs/课程要求覆盖清单.md`
- `docs/软件开发任务.md`
- `src/routing/router.py`
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `src/diary/diary_service.py`
- `src/search/response.py`
- `data/global_sites.json`
- `data/diary_data.json`
- `data/aigc_media_samples.json`

当前仓库状态：

- 本地 `main` 已对齐远端 `origin/main`。
- 第九周正式任务以远端版本为准。
- 第十周最小 Web 演示页已经存在。
- 第十一周成员 B 当前新增文档为任务推进清单与本确认记录。

---

## 2. 成员 B 本周改动边界

成员 B 本周优先改动范围：

- `src/ui/`：正式 Web 主入口、站点状态、统一导航、多目标路径、日记中心、AIGC 入口。
- `src/diary/`：日记创建、编辑、删除、评分和媒体占位的业务接口。
- `tests/test_ui_demo.py`：Web 层新增能力测试。
- `tests/test_diary.py`：日记管理新增能力测试。
- 必要时补充 `tests/test_search.py`、`tests/test_recommend.py` 的回归断言。
- `工作进度/第十一周/`：成员 B 工作记录与最终工作内容陈述。

成员 B 本周不主动改动范围：

- 不改 `src/routing/` 的核心算法。
- 不改 `src/graph/` 的标准图加载逻辑。
- 不直接改 `data/sites/{site_id}/` 标准分层数据。
- 不直接改成员 C 的全文检索和压缩核心实现。

如发现跨模块字段确实缺失，先更新 `docs/项目代码骨架与职责划分.md` 并记录协作点，再做代码适配。

---

## 3. A 侧路径接口确认

### 3.1 单目标路径

成员 B 可直接继续使用：

```python
Router.query_routing(
    start_node_id,
    target_node_id,
    strategy="shortest_distance",
    transport_mode=None,
    site_id=None,
)
```

页面展示可用字段：

- `success`
- `message`
- `site_id`
- `start_node_id`
- `target_node_id`
- `start_node_name`
- `target_node_name`
- `path`
- `path_node_names`
- `path_steps`
- `route_overview`
- `segments`
- `total_distance_m`
- `estimated_time_s`
- `total_distance`
- `estimated_time`
- `strategy`
- `transport_mode`

确认结论：

- 单目标路径字段足够当前 Web 展示。
- `shortest_time` 的时间单位为秒。
- `total_distance` / `estimated_time` 是兼容字段，UI 优先展示 `total_distance_m` / `estimated_time_s`。
- 不需要修改 A 侧接口。

### 3.2 距离排序

成员 B 可直接继续使用：

```python
Router.query_distance(
    start_node_id,
    target_node_id,
    strategy="shortest_distance",
    transport_mode=None,
    site_id=None,
)
```

确认结论：

- `shortest_distance` 返回米。
- `shortest_time` 返回秒。
- 当前 `src/ui/demo_service.py` 已通过 `_distance_provider(...)` 接入距离排序。
- 场所查询和美食推荐可以继续沿用，不需要重写排序链路。

### 3.3 多目标路径

成员 B 本周可直接接入：

```python
Router.query_multi_target(
    start_node_id,
    target_node_ids,
    strategy="shortest_distance",
    transport_mode=None,
    return_to_start=True,
    site_id=None,
)
```

页面展示可用字段：

- `success`
- `message`
- `site_id`
- `path`
- `path_node_names`
- `visit_order`
- `visit_order_names`
- `target_node_ids`
- `total_weight`
- `weight_unit`
- `total_distance_m`
- `estimated_time_s`
- `total_distance`
- `estimated_time`
- `strategy`
- `transport_mode`
- `return_to_start`
- `segments`
- `leg_results`

注意事项：

- 当前代码字段名是 `visit_order` / `visit_order_names`，不是 `target_sequence`。
- 测试和 UI 应优先断言 `visit_order`、`total_distance_m`、`estimated_time_s`、`leg_results`。
- 当前多目标接口最多支持 12 个目标点。
- 不可达或节点不存在时返回 `success=False` 和 `message`。

确认结论：

- 多目标路径接口已经足够 B 侧接入 Web。
- 第十一周不需要修改 A 侧核心算法。
- 若后续 UI 需要更强摘要字段，优先在 B 侧服务层从现有字段派生，不直接改 A 侧。

---

## 4. C 侧数据与全文检索确认

### 4.1 站点数据

当前 `data/global_sites.json` 已注册：

- `PKU`：北京大学

确认结论：

- 第十一周站点选择器可以先基于站点列表实现。
- 当前只有一个站点也要保留选择器结构，为第十二、十三周扩展预留。
- 站点切换后需要重置查询结果、路径结果、地图高亮和表单状态。

### 4.2 日记数据

当前默认日记源：

- `data/diary_data.json`

已有日记查询能力：

- 标题查询
- 目的地查询
- 热度 / 评分排序
- 全文检索
- `results` / `data` 双字段兼容

缺口：

- 还没有创建日记接口。
- 还没有编辑日记接口。
- 还没有删除日记接口。
- 还没有评分接口。
- 媒体字段已有样例基础，但还没有管理入口。

确认结论：

- 日记 CRUD 是 B 侧本周必须补齐的业务层能力。
- 实现时优先使用内存态或可控服务对象演示，避免直接破坏标准样例数据。
- 输出结构继续复用 `src/search/response.py` 的统一 Response 风格。

### 4.3 AIGC 样例

当前样例文件：

- `data/aigc_media_samples.json`

已有字段：

- `sample_id`
- `diary_id`
- `image_placeholder`
- `text_prompt`
- `style`
- `duration_s`
- `output_type`
- `preview_placeholder`
- `status`

确认结论：

- AIGC 轻量演示入口可以直接读取该文件。
- 第十一周目标是“可见、可触发、可预览”的轻量原型，不需要接入真实生成模型。
- B 侧可返回模板化预览结果，例如动画标题、分镜步骤、素材来源、预计时长和预览占位路径。

---

## 5. B 侧现有 Web 能力确认

当前已有 API：

- `GET /api/bootstrap`
- `GET /api/health`
- `POST /api/search/scenic`
- `POST /api/search/places`
- `POST /api/recommend/catering`
- `POST /api/diaries/fulltext`
- `POST /api/route`

当前已有页面能力：

- 综合查询
- 场所查询
- 美食推荐
- 日记全文检索
- 单目标路径规划
- 室外地图高亮

本周需要新增 API：

- 多目标路径 API，例如 `POST /api/route/multi`
- 日记创建 API，例如 `POST /api/diaries`
- 日记编辑 API，例如 `POST /api/diaries/update`
- 日记删除 API，例如 `POST /api/diaries/delete`
- 日记评分 API，例如 `POST /api/diaries/rate`
- AIGC 预览 API，例如 `POST /api/aigc/preview`

本周需要增强的 bootstrap 内容：

- 站点列表。
- 当前站点。
- 功能导航信息。
- AIGC 样例列表。
- 日记媒体占位能力提示。

---

## 6. 统一 Response 边界

成员 B 新增业务接口应保持以下风格：

```json
{
  "success": true,
  "message": "operation success",
  "query_type": "xxx",
  "filters": {},
  "metadata": {},
  "total": 1,
  "data": [],
  "results": []
}
```

对于路径类接口：

- 可以保留 A 侧原始字段。
- B 侧可以追加 `summary`、`ui` 等页面字段。
- 不删除 A 侧字段。

对于错误结果：

- 必须返回 `success=False`。
- 必须给出页面可展示的 `message`。
- 不依赖控制台作为主要错误反馈。

---

## 7. 当前结论

本轮接口边界确认后，成员 B 可以直接进入第十一周后续实现。

可直接接入：

- 单目标路径规划。
- 多目标路径规划。
- 真实距离排序。
- 日记全文检索。
- AIGC 样例读取。
- 课程硬指标核验脚本。

需要本周补齐：

- 正式 Web 主入口骨架。
- 页面内站点状态与统一反馈。
- 多目标路径 Web API 与 UI。
- 日记 CRUD、评分和媒体占位业务接口。
- 日记中心页面。
- AIGC 轻量演示 API 与页面。
- 对应测试和工作陈述。

暂不需要修改：

- A 侧路径接口。
- C 侧主数据结构。
- 公共接口文档。

下一步：

- 执行任务 2：跑当前基线测试，记录修改前状态。
