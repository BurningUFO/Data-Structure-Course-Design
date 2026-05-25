# memberA第13周工作内容陈述

> 成员：Member A（项目大总管 & 算法中枢）
> 周次：第13周（2026-05-25 至 2026-05-31）
> 阶段：正式产品冻结周

---

## 1. 本周目标

本周目标不是继续扩功能，而是把第12周已经接入 Web 主入口的路线规划、室内导航、多目标路径和演示链路冻结下来，形成可重复验收的正式产品版本。A 侧重点保护路径接口、演示路线、回归证据和答辩口径。

---

## 2. 启动检查

已按 README 和 AGENTS 要求完成开工检查：

- `git status --short --branch`：当前为 `main...origin/main`，仅存在既有未跟踪目录 `.codex_tmp/`。
- `git branch --show-current`：`main`。
- `git pull --rebase`：`Already up to date.`。

说明：`.codex_tmp/` 属于既有未跟踪临时目录，本周不删除、不暂存、不纳入提交。

---

## 3. A 侧冻结项

### 3.1 路由接口冻结

第13周冻结 `/api/route` 和 `/api/route/multi` 当前 Web 已依赖的字段，除 P0 / P1 缺陷修复外不做破坏性调整。

重点保护字段：

- 单目标：`start_node_id`、`target_node_id`、`start_node_name`、`target_node_name`、`path`、`path_node_names`、`path_steps`、`segments`、`layer_sequence`、`total_distance_m`、`estimated_time_s`、`strategy`、`transport_mode`、`ui`、`summary`。
- 多目标：`visit_order`、`visit_order_names`、`target_node_ids`、`leg_results`、`segments`、`path_steps`、`total_distance_m`、`estimated_time_s`、`route_type`、`ui`、`summary`。

若冻结周必须补字段，只允许追加，不允许删除、重命名或改变旧字段含义。

### 3.2 固定演示路线

本周固定以下 A 侧讲解样例：

| 场景 | 输入 | 讲解重点 |
|------|------|----------|
| 单目标路线 | `gate_north -> library` | 最短距离、真实道路高亮、路径步骤 |
| 多目标路线 | `gate_north -> [library, canteen]` | 访问顺序、分段摘要、总距离 / 总时间 |
| 纯室内路线 | `library -> lib_reading_room_1` | 室内路径、楼层信息、室内步行语义 |
| 跨层路线 | `gate_north -> lib_reading_room_1` | 室外到室内自动衔接、`gate_link` |
| 交通方式对比 | `gate_south -> sports_ground` | 步行 / 自行车 / mixed 最短时间差异 |
| 异常输入 | 不存在节点或不兼容交通方式 | 明确失败提示，不伪造路线 |

### 3.3 冻结边界

本周不做以下事项：

- 不新增课程硬功能。
- 不重写路径算法或图加载语义。
- 不扩大“全部 208 个扩展对象可直接深度导航”的承诺。
- 不把日记 `memory_only` 或 AIGC `template_preview` 讲成生产级能力。

---

## 4. 当前验证记录

截至 2026-05-25，已完成冻结基线验证：

| 命令 | 结果 |
|------|------|
| `node --check src\ui\static\app.js` | 通过 |
| `py -3 -B tests\test_routing.py` | 83 tests OK |
| `py -3 -B tests\test_integration.py` | 19 项通过 |
| `py -3 -B tests\test_course_requirements.py` | 课程核验通过 |
| `py -3 -B tests\test_ui_demo.py` | UI demo 服务测试通过 |
| `py -3 -m pytest -q` | 373 passed in 62.25s |
| 临时端口 HTTP 冒烟 | `/api/health`、`/api/bootstrap`、`/api/map/geojson?site_id=PKU`、`/api/route`、`/api/route/multi` 通过 |
| `netstat -ano \| findstr :8765` | 当前无 8765 监听进程 |

解释：本机 `py -3` 可正常运行项目测试；`python` 命令命中 WindowsApps 占位程序，不应作为本机有效解释器。冻结周正式回归优先使用 `py -3`。

---

## 5. 本周输出物

- `工作进度/第十三周/memberA第13周工作内容陈述.md`
- `工作进度/第十三周/第13周高优问题清单.md`
- 同步修正 `docs/用户使用说明.md` 中的第13周正式产品冻结口径。
- 同步修正 Web 帮助内容中的阶段标签，避免旧阶段表述影响验收。

---

## 6. 后续统筹动作

1. 周二晚前确认 Member B 页面结构冻结候选版和 Member C 文档核验清单。
2. 周四晚前完成第一次全链路串测，并只保留 P0 / P1 问题进入冻结修复。
3. 周六晚前完成正式演示彩排，确认五条固定演示链路可重复。
4. 周日 20:00 前收齐三人工作内容陈述并汇总第13周周报。
