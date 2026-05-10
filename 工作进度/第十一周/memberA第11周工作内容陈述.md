# memberA 第11周工作内容陈述

> 阶段版本：第11周启动与接口冻结阶段
> 负责范围：图结构、路径规划、路径接口冻结、路径验证样例、协作风险统筹

---

## 1. 本阶段完成事项

1. 阅读并对齐第11周任务要求、三人协作方式、软件开发任务、课程要求覆盖清单和项目接口文档。
2. 整理 `课程硬指标缺口 + 接口冻结项 + 本周主链路风险`，形成 `工作进度/第十一周/memberA第11周统筹清单.md`。
3. 对 `query_routing(...)`、`query_distance(...)`、`query_multi_target(...)` 做第一轮冻结口径确认。
4. 补充多目标路径接口文档，明确 Web 展示优先消费字段：
   - `visit_order` / `visit_order_names`
   - `path` / `path_node_names`
   - `total_distance_m` / `estimated_time_s`
   - `segments`
   - `leg_results`
5. 更新路由测试，新增标准站点下单目标和多目标冻结字段断言，确保成员 B 可稳定接入 Web 展示。

---

## 2. 涉及文件

- `工作进度/第十一周/memberA第11周统筹清单.md`
- `工作进度/第十一周/memberA第11周工作内容陈述.md`
- `docs/项目代码骨架与职责划分.md`
- `tests/test_routing.py`

---

## 3. 测试命令与结果

当前环境未识别 `py` 启动器，因此使用 `python -B` 作为等价替代命令。

```powershell
python -B tests\test_routing.py
```

结果：18 项通过。

```powershell
python -B tests\test_integration.py
```

结果：19 项通过。

```powershell
python -B tests\test_ui_demo.py
```

结果：全部 UI demo service 测试通过。

---

## 4. 当前阻塞与协作依赖

1. Member C 仍需补齐 `>=10` 用户样例、200+ 推荐 / 查询对象、50+ 设施和 200+ 图边数据，否则 Member A 暂无法完成 200+ 边规模下的真实性能验证。
2. `tests/test_course_requirements.py` 尚未存在，需要 Member C 建立课程硬指标核验脚本，Member A 后续配合补路径相关断言。
3. Web 主入口当前尚未接入 `/api/route/multi`，成员 B 需要基于已冻结的 `query_multi_target(...)` 字段完成多目标路径页面展示。
4. 日记 CRUD、评分、多媒体占位和 AIGC 轻量演示仍主要是 B/C 任务，Member A 仅负责保证日记结果中的 `destination_node_id` 可继续进入路径规划。

---

## 5. 下周计划

1. 等待 Member C 扩展数据后，补充 200+ 节点 / 边规模下的典型路径性能验证。
2. 配合 Member B 调试 `/api/route/multi`，重点检查访问顺序、总距离、总时间和各段路径步骤是否稳定展示。
3. 继续维护路径接口冻结口径，若新增字段只采用追加方式并同步文档。
4. 准备第12周全量功能接入所需的路径规划答疑材料和演示样例。

---

## 6. 可演示入口

当前可稳定演示的 Member A 相关入口：

```powershell
python -B tests\test_routing.py
python -B tests\test_integration.py
python -m src.ui.demo_server
```

Web 默认地址：

```text
http://127.0.0.1:8765
```
