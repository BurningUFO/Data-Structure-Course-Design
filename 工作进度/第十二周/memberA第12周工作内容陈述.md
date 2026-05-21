# memberA 第12周工作内容陈述

> 阶段版本：第12周全量功能接入周阶段记录（截至 2026-05-21）
> 负责范围：图结构、路径规划、路径接口冻结、全量联调收口、风险统筹与周报材料整理

---

## 1. 本阶段已完成事项

1. 阅读并发布 `工作进度/第十二周/memberA第12周统筹清单.md`，明确第 12 周目标为 M3“全量功能接入周”，并将硬项、成员分工、联调节奏、验收口径和禁止事项写入仓库。
2. 复核当前 `query_routing(...)`、`query_distance(...)`、`query_multi_target(...)` 的稳定字段，确认当前 Web 主入口继续消费以下关键展示字段：
   - 单目标路径：`path`、`path_node_names`、`total_distance_m`、`estimated_time_s`、`layer_sequence`、`path_steps`、`segments`
   - 多目标路径：`visit_order`、`visit_order_names`、`path`、`path_node_names`、`total_distance_m`、`estimated_time_s`、`segments`、`leg_results`
3. 以第 12 周统筹清单为基准执行第一轮路径联调验证，确认 `/api/route`、`/api/route/multi`、日记目的地跳转路径、跨层路径、混合交通方式路径和多目标路径在当前仓库状态下仍可稳定返回。
4. 复核不可达、站点不匹配、节点不存在等错误提示口径，确认 `tests/test_routing.py` 中对应断言仍然通过，当前路径接口没有出现“字段改名”或“语义回退”。
5. 对照第 11 周 `memberA第11周路径性能验证记录.md`，将 `200` 边阶段形成的路径性能结论正式带入第 12 周材料，供后续第 13 周正式产品冻结与答辩说明继续复用。
6. 补齐第 12 周当前缺失的 Member A 文档，新增：
   - `memberA第12周工作内容陈述.md`
   - `memberA第12周第一轮串测问题清单.md`
   - `第12周周报.md`
   - `第13周正式产品冻结前风险清单.md`

---

## 2. 涉及文件

- `工作进度/第十二周/memberA第12周统筹清单.md`
- `工作进度/第十二周/memberA第12周工作内容陈述.md`
- `工作进度/第十二周/memberA第12周第一轮串测问题清单.md`
- `工作进度/第十二周/第12周周报.md`
- `工作进度/第十二周/第13周正式产品冻结前风险清单.md`
- `工作进度/第十一周/memberA第11周路径性能验证记录.md`
- `tests/test_routing.py`
- `tests/test_integration.py`
- `tests/test_course_requirements.py`
- `tests/test_ui_demo.py`

---

## 3. 测试命令与结果

优先验证命令：

```powershell
python -m pytest
```

结果：当前环境失败，报错为 `No module named pytest`。这是本机 Python 环境缺少 `pytest` 模块导致的验证入口缺失，不是本次路径或文档修改引起的问题。当前最安全替代方案仍是继续执行仓库内各条主线测试脚本。

当前环境未识别 `py` 启动器，因此本周正式核验继续统一使用 `python -B`。

```powershell
python -B tests\test_routing.py
```

结果：`83` 项通过。已覆盖单目标路径、多目标路径、跨层路径、交通方式过滤、混合交通方式、错误提示与展示字段断言。

```powershell
python -B tests\test_integration.py
```

结果：`19` 项通过。已覆盖“查询 / 推荐 -> 路径规划”“日记 / 全文检索 -> 目的地节点 -> 路径规划”等主链路联调。

```powershell
python -B tests\test_course_requirements.py
```

结果：全部通过。当前核验输出摘要如下：

- `users=70`
- `diary_authors=70`
- `extension_objects=208`
- `pku_nodes=1565`
- `pku_edges=3550`
- `facility_like_nodes=1397`

```powershell
python -B tests\test_ui_demo.py
```

结果：全部 UI demo service 测试通过。当前 Web 主入口、Leaflet 地图、室内导航、日记中心、AIGC 轻量演示、多目标路径和附近设施查询均通过自动化验收。

第 11 周性能验证结论继续有效，当前第 12 周仍沿用以下答辩口径：

- 单目标跨层最短距离：平均 `0.0923 ms`，P95 `0.1560 ms`
- 单目标最短时间策略：平均 `0.1131 ms`，P95 `0.1955 ms`
- 宿舍跨层路径：平均 `0.1314 ms`，P95 `0.2178 ms`
- 交通方式约束路径：平均 `0.0246 ms`，P95 `0.0252 ms`
- 室外多目标回路：平均 `1.1228 ms`，P95 `2.0192 ms`
- 跨层多目标回路：平均 `1.7901 ms`，P95 `2.9090 ms`

---

## 4. 当前判断

1. 以 Member A 负责范围来看，本周当前没有发现新的路径算法阻塞；路由字段、错误提示、多目标路径和跨层路径主线均处于可演示状态。
2. 当前未发现 `/api/route` 与 `/api/route/multi` 因字段变化导致的 Web 展示回退；现有自动化测试能覆盖 `visit_order`、`leg_results`、`path_steps`、`segments`、`layer_sequence` 等核心字段。
3. 第 12 周当前最大的未完成项已从“代码实现”转向“文档收口、风险清单、周末材料汇总和正式产品冻结前统一口径”。
4. 当前课程硬指标核验口径已经显著高于第 11 周的 58 节点 / 200 边阶段，后续答辩和周报中需要明确说明“第 11 周性能记录是阶段性基准，当前系统规模已扩大到更高快照”。

---

## 5. 当前仍待收口事项

截至 2026-05-21，Member A 侧仍需继续跟进以下事项：

1. 继续跟踪第 12 周后半程的高优问题，若 Member B 或 Member C 在收口中新增路径字段需求，只允许采用追加字段方式处理。
2. 在周末前吸收 Member B / Member C 的第 12 周实际完成情况，更新 `第12周周报.md` 到最终版。
3. 在第 13 周正式产品冻结前，继续维护“路径性能口径 + 错误提示口径 + 多目标展示口径”的统一说法，避免答辩时出现前后不一致。

---

## 6. 可演示入口

当前可稳定演示的 Member A 相关入口：

```powershell
python -B tests\test_routing.py
python -B tests\test_integration.py
python -B tests\test_course_requirements.py
python -B tests\test_ui_demo.py
python -m src.ui.demo_server
```

Web 默认地址：

```text
http://127.0.0.1:8765
```
