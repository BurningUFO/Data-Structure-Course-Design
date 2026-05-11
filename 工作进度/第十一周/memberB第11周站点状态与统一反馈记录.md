# memberB第11周站点状态与统一反馈记录

> 任务阶段：任务 4，站点状态与统一页面反馈
> 完成日期：2026-05-11
> 目标：让 Web 主入口具备可扩展站点状态管理，并把加载、空结果、异常和路径失败统一反馈到页面。

---

## 1. 本次完成内容

### 1.1 后端站点服务选择

更新 `src/ui/demo_server.py`：

- `GET /api/bootstrap` 支持 `site_id` 或 `site` 查询参数。
- `GET /api/health` 支持 `site_id` 或 `site` 查询参数。
- POST 业务请求会读取请求体中的 `site_id`，按站点选择对应 `DemoUIService`。
- 服务端按 `site_id` 做简单缓存，避免同一站点重复初始化。

当前数据只有 `PKU` 一个站点，但后端已经具备按站点扩展的基础结构。

### 1.2 Bootstrap 状态策略

更新 `src/ui/demo_service.py`，新增：

- `state_policy`：声明站点切换时需要重置的状态。
- `feedback_messages`：统一页面反馈文案。
- `stats.site_count`：当前可选站点数量。

新增状态覆盖：

- `ready`
- `loading`
- `success`
- `empty`
- `error`

### 1.3 前端站点状态重置

更新 `src/ui/static/app.js`：

- 新增 `loadSiteBootstrap(siteId)`，支持按站点重新加载 bootstrap。
- 站点选择器变化后会重新加载站点数据。
- 站点切换或重复选择当前站点时，会重置：
  - 查询结果
  - 当前路径
  - 地图高亮
  - 表单输入
  - 当前起点
- POST 请求会自动附带当前 `site_id`。

### 1.4 统一页面反馈

更新 `src/ui/static/app.js` 和 `src/ui/static/styles.css`：

- 查询开始时显示 loading 状态。
- 查询空结果显示 empty 状态。
- 查询异常会清空旧结果、旧路径和地图高亮。
- 路径规划开始时显示 loading 状态。
- 路径规划失败或不可达时会清空旧路径并在路径摘要区域展示原因。
- 状态横幅新增 `role="status"` 和 `aria-live="polite"`，让反馈更明确。

---

## 2. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/ui/demo_server.py` | 修改 | 支持按 `site_id` 获取服务与处理请求 |
| `src/ui/demo_service.py` | 修改 | 新增状态策略、反馈文案和站点数量 |
| `src/ui/static/index.html` | 修改 | 状态横幅补充可访问性属性 |
| `src/ui/static/app.js` | 修改 | 站点切换、状态重置、统一反馈、请求附带 `site_id` |
| `src/ui/static/styles.css` | 修改 | 新增 loading / empty 状态样式 |
| `tests/test_ui_demo.py` | 修改 | 增加状态策略和反馈字段断言 |

---

## 3. 当前边界

已完成：

- 站点选择机制已具备扩展结构。
- 页面内站点状态重置已实现。
- 查询、空结果、异常、路径失败已有统一页面反馈。
- 当前只有 `PKU` 一个站点时，重复选择当前站点也会触发页面状态重置。

后续继续：

- 多目标路径接入后，需要复用同一套 loading / error / empty 反馈。
- 日记 CRUD 和 AIGC 入口接入后，也应统一使用 `setStatus(...)` 和页面结果区反馈，不再依赖控制台。

---

## 4. 测试结果

已执行：

```text
python -B tests/test_ui_demo.py
node --check src\ui\static\app.js
python -B -m py_compile src/ui/demo_server.py src/ui/demo_service.py
```

结果：

```text
All UI demo service tests passed.
```

结论：

- 状态策略字段已进入 bootstrap。
- 原有查询、推荐、日记全文检索和单目标路径服务层能力未被破坏。
- 前端脚本语法通过检查。
