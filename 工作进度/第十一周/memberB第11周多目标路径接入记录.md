# memberB第11周多目标路径接入记录

> 任务阶段：任务 5，多目标路径业务接入
> 完成日期：2026-05-11
> 目标：把成员 A 的 `query_multi_target(...)` 接入成员 B 的 Web 主入口，页面可展示访问顺序、总距离、总时间和关键路径步骤。

---

## 1. 本次完成内容

### 1.1 服务层多目标路径封装

更新 `src/ui/demo_service.py`：

- 新增 `DemoUIService.plan_multi_route(...)`。
- 调用成员 A 的 `Router.query_multi_target(...)`。
- 支持参数：
  - `start_node_id`
  - `target_node_ids`
  - `strategy`
  - `transport_mode`
  - `return_to_start`
  - `site_id`
- 返回中保留 A 侧原始字段：
  - `visit_order`
  - `visit_order_names`
  - `target_node_ids`
  - `total_distance_m`
  - `estimated_time_s`
  - `leg_results`
  - `segments`
- 追加 B 侧 UI 字段：
  - `route_type="multi_target"`
  - `summary`
  - `ui.leg_summaries`
  - `ui.display_steps`
  - `ui.caption`

说明：

- 本次只在 B 侧做 UI 友好封装，没有修改 A 侧路由算法。
- 当前测试使用 `visit_order` / `visit_order_names` 作为访问顺序字段。

### 1.2 Web API 接入

更新 `src/ui/demo_server.py`：

- 新增 API：`POST /api/route/multi`
- 该接口会按请求体中的 `site_id` 选择对应站点服务。
- 与单目标路径 API 保持同一服务层风格。

### 1.3 Web 页面接入

更新 `src/ui/static/index.html`：

- 在“导航规划”页中保留单目标路径表单。
- 新增多目标路径表单。
- 支持多选目标点。
- 支持“访问完成后返回起点”开关。
- 新增多目标路径预设入口。

更新 `src/ui/static/app.js`：

- 新增 `planMultiRoute(...)`。
- 新增多目标预设处理。
- 多目标请求自动携带当前 `site_id`。
- 多目标结果复用统一路径结果区域。
- 多目标路径展示：
  - 访问顺序
  - 总距离
  - 总时间
  - 目标数
  - 路径段数
  - 每段起终点
  - 每段距离 / 时间
  - 前若干关键步骤

更新 `src/ui/static/styles.css`：

- 新增多目标表单分区样式。
- 新增多目标关键步骤提示样式。

---

## 2. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/ui/demo_service.py` | 修改 | 新增多目标路径服务层封装和 UI 摘要 |
| `src/ui/demo_server.py` | 修改 | 新增 `/api/route/multi` |
| `src/ui/static/index.html` | 修改 | 导航规划页新增多目标表单 |
| `src/ui/static/app.js` | 修改 | 新增多目标请求、预设、结果渲染 |
| `src/ui/static/styles.css` | 修改 | 新增多目标表单和关键步骤样式 |
| `tests/test_ui_demo.py` | 修改 | 新增多目标路径服务层测试 |

---

## 3. 当前可演示方式

启动：

```text
python -B -m src.ui.demo_server
```

浏览器访问：

```text
http://127.0.0.1:8765
```

演示路径：

1. 打开“导航规划”。
2. 在“多目标路径”中选择多个目标点，例如图书馆、食堂。
3. 选择是否返回起点。
4. 点击“规划多目标路线”。
5. 右侧路径摘要展示访问顺序、距离、时间和路径段。
6. 地图区高亮可映射的室外路径，室内段在步骤卡片中展示。

---

## 4. 测试结果

已执行：

```text
python -B tests/test_ui_demo.py
node --check src\ui\static\app.js
python -B -m py_compile src/ui/demo_server.py src/ui/demo_service.py
python -B tests/test_routing.py
python -B tests/test_integration.py
```

结果：

- `tests/test_ui_demo.py`：通过。
- `node --check src\ui\static\app.js`：通过。
- `py_compile`：通过。
- `tests/test_routing.py`：18 项通过。
- `tests/test_integration.py`：19 项通过。

结论：

- 多目标路径已经接入 Web 主入口。
- A 侧原有单目标、多目标路径能力未被破坏。
- 第十周已有查询、推荐、日记全文检索链路未受影响。

---

## 5. 后续衔接

下一项任务是日记管理业务接口。

后续接入日记中心、AIGC 入口时，应继续复用本次已经建立的：

- `site_id` 自动携带机制。
- `setStatus(...)` 页面状态反馈。
- 统一结果区 / 路径区展示逻辑。
