# memberC 第12周工作内容陈述

> 角色：Member C（数据、检索、压缩、测试与文档负责人）  
> 周期：2026-05-18 至 2026-05-24  
> 阶段定位：M3 全量功能接入周，负责课程核验、数据口径、联调证据和冻结前文档材料收口

---

## 1. 本周任务目标

第十二周成员 C 的核心目标，不再是继续单点补功能，而是把第十一周已经建立的课程硬指标底座升级为“可持续回归、可对外说明、可支持 Web 演示”的稳定证据链。对应本周，我重点负责以下事项：

1. 继续维护 `tests/test_course_requirements.py`，把它固定为课程硬指标回归入口。
2. 复核扩展对象、用户样例、设施与图边数据，修正口径不一致或文档落后问题。
3. 配合 Member B 检查日记媒体占位、AIGC 样例、全文检索结果和压缩演示样例是否适合直接用于 Web 展示。
4. 配合 Member A / B 跑通 `tests/test_integration.py`、`tests/test_ui_demo.py`，确认第 12 周主入口收口没有破坏日记 / 检索 / 路径联动。
5. 更新课程要求覆盖清单、数据字典和第 12 周书面材料，为第 13 周正式产品冻结准备文档证据。

---

## 2. 本周完成事项

1. 继续维护并升级 `tests/test_course_requirements.py`，将核验定位从“第 11 周最低门槛脚本”更新为“第 12 周课程硬指标与联调固定入口”。
2. 为课程核验脚本补入第 12 周文档存在性检查，确保以下材料已经落盘：
   - `memberC第12周课程核验与联调记录.md`
   - `memberC第12周工作内容陈述.md`
   - `第12周周报.md`
3. 保持用户样例、日记作者、扩展对象、AIGC 样例和当前 PKU 全量图快照的强断言不回退，并补充 `output_type`、`duration_s` 等 Web 直接展示会使用的字段检查。
4. 复核当前课程规模快照，确认本周固定口径已切换到：
   - `users=70`
   - `diary_authors=70`
   - `extension_objects=208`
   - `mapped_extension_objects=5`
   - `pku_nodes=1565`
   - `pku_edges=3550`
5. 更新 [课程要求覆盖清单.md](/C:/code/Data-Structure-Course-Design/docs/课程要求覆盖清单.md)，把“第 11 周当前核验结果”升级为“第 12 周当前核验结果”，并补入固定回归集合和当前快照口径。
6. 更新 [数据字典.md](/C:/code/Data-Structure-Course-Design/docs/数据字典.md)，补充第 12 周固定课程核验快照、70 个用户样例口径、AIGC 轻量预览样例说明和固定回归入口说明。
7. 补齐 [memberC第12周课程核验与联调记录.md](/C:/code/Data-Structure-Course-Design/工作进度/第十二周/memberC第12周课程核验与联调记录.md)，把课程核验、集成联调和 Web 主入口联调证据集中记录。
8. 同步修正第 12 周材料中的一处旧分支描述，使材料与当前 `main` 主线状态一致。

---

## 3. 涉及文件

- `tests/test_course_requirements.py`
- `docs/课程要求覆盖清单.md`
- `docs/数据字典.md`
- `工作进度/第十二周/memberC第12周课程核验与联调记录.md`
- `工作进度/第十二周/memberC第12周工作内容陈述.md`
- `工作进度/第十二周/第12周周报.md`
- `工作进度/第十二周/memberB第12周工作内容陈述.md`

---

## 4. 测试命令与结果

本周优先尝试的统一验证入口：

```powershell
python -m pytest
```

结果：当前环境仍报 `No module named pytest`，说明统一入口尚未恢复。这属于本机环境缺少 `pytest` 模块，不是本周数据 / 文档改动引起的问题。

因此本周继续采用分脚本回归：

```powershell
python -B tests/test_course_requirements.py
python -B tests/test_integration.py
python -B tests/test_ui_demo.py
node --check src/ui/static/app.js
```

当前验证结论：

1. `tests/test_course_requirements.py`：通过。当前课程硬指标和书面证据链核验稳定，输出快照为 `users=70`、`diary_authors=70`、`extension_objects=208`、`pku_nodes=1565`、`pku_edges=3550`。
2. `tests/test_integration.py`：通过。查询 / 推荐 / 日记 / 全文检索 / 压缩 / 路径联调主链路保持稳定，`19` 项通过、`0` 失败。
3. `tests/test_ui_demo.py`：通过。第 12 周 Web 主入口、地图、多目标路径、日记中心和 AIGC 可见入口回归均保持稳定。
4. `node --check src/ui/static/app.js`：前端脚本语法检查通过。

---

## 5. 当前判断

1. 以成员 C 负责范围来看，第十二周当前已不存在“课程硬指标只靠口头说明”的问题，核验脚本和书面记录已经形成固定入口。
2. 当前最大价值不在继续扩容数据，而在于维持“当前快照数字、测试输出、课程覆盖清单和周报材料”一致。
3. 日记与 AIGC 的边界已经足够清晰：前者是 `memory_only` 轻量演示，后者是 `template_preview` / `placeholder_ready` 轻量可见输出。
4. 扩展对象规模已经达标，但 `mapped_extension_objects=5` 仍说明大多数对象是推荐 / 查询规模口径，不应在答辩中被表述为“全部支持深度导航”。

---

## 6. 当前剩余风险

1. `pytest` 统一入口尚未恢复，冻结前回归仍依赖分脚本执行。
2. 若后续材料仍引用第 11 周的旧快照，会与当前 `1565` 节点 / `3550` 边的系统现状冲突。
3. 若 Web 端后续继续扩张“所有扩展对象直接导航”的承诺，会超出当前 `5` 条稳定映射样例的真实能力边界。

---

## 7. 第13周计划

1. 继续维护课程核验脚本，避免第 13 周产品冻结阶段出现数据口径回退。
2. 配合 Member B 继续检查日记、全文检索、AIGC 轻量预览相关字段是否与页面说明一致。
3. 配合 Member A 维持“课程规模快照 + 路径性能口径 + 扩展对象边界”的统一答辩说法。
4. 继续整理冻结版数据说明、课程文档和最终验收材料。
