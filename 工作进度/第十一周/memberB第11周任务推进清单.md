# memberB第11周任务推进清单

> 成员 B 角色：查找、排序、推荐与业务交互负责人
> 本周周期：2026-05-11 至 2026-05-17
> 当前基线：本地 `main` 已对齐远端 `origin/main`，第九周以远端正式版本为准，第十周最小 Web UI 已存在，第十一周进入第 13 周正式产品倒计时。

---

## 1. 本周目标

第十一周不再继续做零散 CLI 功能，而是把成员 B 负责的业务能力推进到“浏览器可见、页面可操作、测试可验证”的产品骨架状态。

本周成员 B 需要完成的核心目标：

1. 把 `src/ui/` 从第十周临时演示页升级为正式产品主入口骨架。
2. 在 Web 中补齐站点选择、统一导航、帮助入口和基础状态管理。
3. 补齐日记创建、编辑、删除、评分和媒体占位入口。
4. 接入成员 A 已有的 `query_multi_target(...)`，展示多目标访问顺序、总距离、总时间和关键步骤。
5. 增加 AIGC 轻量演示入口，实现“图片占位 + 文字描述 -> 预览结果”的最小闭环。
6. 更新测试与第十一周工作内容陈述，确保本周产出可验收。

---

## 2. 当前代码基础判断

### 2.1 已具备能力

- `src/ui/demo_server.py` 已提供 Web 服务入口。
- `src/ui/demo_service.py` 已封装查询、场所、美食、日记全文检索和单目标路径规划。
- `src/ui/static/index.html`、`app.js`、`styles.css` 已有最小演示页面。
- `src/routing/router.py` 已提供 `query_routing(...)` 和 `query_multi_target(...)`，多目标返回中包含总距离、总时间、分段和每段路径结果。
- `src/diary/diary_service.py` 已支持日记查询和全文检索。
- `data/users.json`、`data/diary_data.json`、`data/aigc_media_samples.json` 已由成员 C 补齐课程硬指标相关样例。
- `tests/test_ui_demo.py`、`tests/test_diary.py`、`tests/test_course_requirements.py` 已有第十一周可扩展的测试基础。

### 2.2 本周主要缺口

- Web 页面仍偏“演示台”，缺少正式首页、站点选择器、帮助区和更清晰的主导航结构。
- 站点切换还没有成为页面内可操作能力，当前主要通过服务启动参数选择站点。
- 日记模块已有查询，但缺少创建、编辑、删除、评分和媒体占位的业务入口。
- Web 只接了单目标路径，尚未把 `query_multi_target(...)` 暴露为页面功能。
- AIGC 样例数据存在，但 Web 还没有对应输入表单和预览区域。
- 测试需要覆盖新增的日记管理、多目标路径、AIGC 入口和页面状态。

---

## 3. 推荐推进顺序

### 任务 1：启动对齐与接口边界确认

目标：
- 明确本周成员 B 只改业务层、UI 层和对应测试，不主动修改成员 A 的路由核心和成员 C 的主数据结构。
- 记录需要消费的外部字段，避免后续边做边改协议。

重点确认：
- 多目标路径使用 `Router.query_multi_target(...)`。
- 单目标路径继续使用 `Router.query_routing(...)`。
- 路径展示优先使用 `path_node_names`、`route_overview`、`path_steps`、`segments`、`total_distance_m`、`estimated_time_s`。
- 日记默认数据源继续使用 `data/diary_data.json`。
- AIGC 样例默认读取 `data/aigc_media_samples.json`。

建议产出：
- 在本清单中维护接口依赖说明。
- 如果发现字段缺失，再同步更新 `docs/项目代码骨架与职责划分.md`。

完成标准：
- 明确本周不需要等待 A/C 才能先做 Web 和业务层封装。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周接口边界确认记录.md`。
- 结论：A/C 当前接口与数据足够支持成员 B 启动第十一周实现，暂不需要修改公共接口文档。

---

### 任务 2：跑当前基线测试，记录修改前状态

目标：
- 在正式改代码前记录当前远端基线是否可运行，避免后续无法判断问题是原有缺陷还是本周改动引入。

建议执行命令：

```text
py -3 -B tests/test_search.py
py -3 -B tests/test_recommend.py
py -3 -B tests/test_diary.py
py -3 -B tests/test_ui_demo.py
py -3 -B tests/test_course_requirements.py
```

建议产出：
- 记录通过、失败或跳过的测试结果。
- 若发现基线已有失败，先写入第十一周工作记录，后续修复时单独说明。
- 不在此阶段大改功能，只做状态确认。

完成标准：
- 明确“修改前基线状态”，后续每个功能改造都有对照依据。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周基线测试记录.md`。
- 结论：`py -3 -B` 在当前本机环境下不可用，返回 `exit=112`；改用 `python -B` 后 10 个基线测试脚本全部通过。

---

### 任务 3：正式 Web 主入口骨架

目标：
- 把浏览器作为第十一周之后的主入口，而不是临时演示页面。

建议修改范围：
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`
- `src/ui/demo_service.py`

实现内容：
- 增加首页区域，展示系统定位、当前站点、核心能力入口。
- 增加站点选择器，至少支持显示可选站点和当前站点。
- 增加统一导航，覆盖综合查询、场所查询、美食推荐、路径规划、多目标路径、日记中心、AIGC 演示、帮助说明。
- 增加帮助入口，说明推荐演示链路和测试命令。
- 站点切换后清空查询结果、路径高亮、表单状态和提示信息。

依赖关系：
- 不阻塞 A/C。
- 只依赖 `data/global_sites.json` 和现有 bootstrap 数据。

完成标准：
- 启动 `py -m src.ui.demo_server` 后，浏览器首页能直接看到主导航、站点信息、帮助入口和核心功能入口。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周Web主入口骨架记录.md`。
- 代码范围：`src/ui/demo_service.py`、`src/ui/static/index.html`、`src/ui/static/app.js`、`src/ui/static/styles.css`、`tests/test_ui_demo.py`。
- 验证结果：`python -B tests/test_ui_demo.py` 通过。

---

### 任务 4：站点状态与统一页面反馈

目标：
- 让页面具备正式产品最基础的状态管理能力。

建议修改范围：
- `src/ui/demo_service.py`
- `src/ui/static/app.js`
- `src/ui/static/index.html`
- `src/ui/static/styles.css`

实现内容：
- 扩展 bootstrap 返回内容，包含站点列表、当前站点、功能可用性和统计信息。
- 统一页面状态：加载中、成功、空结果、输入错误、接口异常、不可达路径。
- 页面切换时保留必要上下文，但不保留错误的旧路径高亮。
- 站点切换后重置当前结果和当前路径。

依赖关系：
- 与任务 3 强相关，建议连续完成。

完成标准：
- 空查询、无结果、非法参数、不可达路线都有页面提示，不再主要依赖控制台。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周站点状态与统一反馈记录.md`。
- 代码范围：`src/ui/demo_server.py`、`src/ui/demo_service.py`、`src/ui/static/index.html`、`src/ui/static/app.js`、`src/ui/static/styles.css`、`tests/test_ui_demo.py`。
- 验证结果：`python -B tests/test_ui_demo.py`、`node --check src\ui\static\app.js`、`python -B -m py_compile src/ui/demo_server.py src/ui/demo_service.py` 均通过。

---

### 任务 5：多目标路径业务接入

目标：
- 把成员 A 的 `query_multi_target(...)` 接入成员 B 的 Web 主入口。

建议修改范围：
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`
- `tests/test_ui_demo.py`

实现内容：
- 新增 `/api/route/multi` 或等价 API。
- 支持选择多个目标节点。
- 调用 `Router.query_multi_target(...)`。
- 页面展示访问顺序、总距离、总时间、每段起终点、关键路径步骤。
- 对不可达目标给出清晰提示。

依赖关系：
- 依赖成员 A 现有多目标接口，但当前远端代码已经提供基础能力。
- 如果发现字段不够展示，再向 A 追加字段需求，不主动修改 A 的核心算法。

完成标准：
- 页面能演示“从当前起点依次访问多个地点”的结果。
- 测试能断言返回中包含 `target_sequence` 或等价访问顺序、`total_distance_m`、`estimated_time_s`、`leg_results`。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周多目标路径接入记录.md`。
- 代码范围：`src/ui/demo_service.py`、`src/ui/demo_server.py`、`src/ui/static/index.html`、`src/ui/static/app.js`、`src/ui/static/styles.css`、`tests/test_ui_demo.py`。
- 字段口径：使用 A 侧实际冻结字段 `visit_order` / `visit_order_names` 作为访问顺序，不新增 `target_sequence`。
- 验证结果：`python -B tests/test_ui_demo.py`、`node --check src\ui\static\app.js`、`python -B -m py_compile src/ui/demo_server.py src/ui/demo_service.py`、`python -B tests/test_routing.py`、`python -B tests/test_integration.py` 均通过。

---

### 任务 6：日记管理业务接口

目标：
- 让日记模块从“只能查”升级为“可管理”。

建议修改范围：
- `src/diary/diary_service.py`
- `src/diary/__init__.py`
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `tests/test_diary.py`

实现内容：
- 新增日记创建接口，支持标题、正文、目的地、评分、标签、图片/视频占位字段。
- 新增日记编辑接口，允许修改标题、正文、目的地、评分、标签和媒体占位。
- 新增日记删除接口，采用内存态演示或可控临时数据，避免直接破坏标准样例数据。
- 新增日记评分接口，保持 `rating` 字段为统一评分来源。
- 返回结构继续使用统一 Response 风格，保留 `success`、`message`、`query_type`、`results`、`data`、`metadata`。

依赖关系：
- 依赖成员 C 已提供的日记和媒体样例字段。
- 不需要成员 C 继续补数据后才能做最小实现。

完成标准：
- 测试中能完成创建、编辑、评分、删除的完整流程。
- 不破坏现有日记查询和全文检索测试。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周日记管理业务接口记录.md`。
- 代码范围：`src/diary/diary_service.py`、`src/diary/__init__.py`、`src/ui/demo_service.py`、`src/ui/demo_server.py`、`tests/test_diary.py`、`tests/test_ui_demo.py`。
- HTTP 路由：`POST /api/diaries`、`POST /api/diaries/create`、`POST /api/diaries/update`、`POST /api/diaries/delete`、`POST /api/diaries/rate`。
- 存储口径：当前为 `memory_only` 内存态演示，不直接写回 `data/diary_data.json`。
- 验证结果：`python -B tests/test_diary.py`、`python -B tests/test_ui_demo.py`、`python -B -m py_compile src/diary/diary_service.py src/diary/__init__.py src/ui/demo_service.py src/ui/demo_server.py` 均通过。

---

### 任务 7：日记中心 Web 页面

目标：
- 把任务 6 的日记管理能力接入浏览器。

建议修改范围：
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`
- `src/ui/demo_server.py`
- `tests/test_ui_demo.py`

实现内容：
- 增加日记中心页面或标签页。
- 保留全文检索入口。
- 增加创建/编辑表单。
- 增加评分输入。
- 增加图片、视频媒体占位展示字段。
- 增加删除按钮或演示入口。

依赖关系：
- 依赖任务 6。

完成标准：
- 浏览器中能完成一次日记创建或编辑，并能看到评分和媒体占位信息。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周日记中心Web页面记录.md`。
- 页面范围：`src/ui/static/index.html`、`src/ui/static/app.js`、`src/ui/static/styles.css`。
- 服务范围：`src/ui/demo_service.py`。
- 测试范围：`tests/test_ui_demo.py`。
- 已接入操作：全文检索、创建日记、载入编辑、更新所选日记、仅更新评分、快速评 5 分、删除日记。
- 展示字段：评分、目的地、创建时间、图片占位、视频占位、路线目标。
- 存储口径：沿用第 6 项 `memory_only`，页面操作不写回 `data/diary_data.json`。
- 验证结果：`node --check src\ui\static\app.js`、`python -B tests/test_ui_demo.py`、`python -B tests/test_diary.py`、`python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py` 均通过。

---

### 任务 8：AIGC 轻量演示入口

目标：
- 将 AIGC 从文档计划项变成 Web 可见、可触发的演示项。

建议修改范围：
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`
- `tests/test_ui_demo.py`

实现内容：
- 读取 `data/aigc_media_samples.json`。
- 增加输入表单：图片占位选择、文字描述、风格或模板选项。
- 返回模板化预览结果，例如分镜摘要、动画标题、关键帧说明、素材来源。
- 页面展示预览结果，明确这是第十一周轻量原型，第十二周继续增强。

依赖关系：
- 依赖成员 C 已提供的 AIGC 样例数据。

完成标准：
- 浏览器中能触发一次 AIGC 预览，并展示“图片占位 + 文字描述 -> 预览结果”。
- 测试能验证 AIGC API 返回统一 Response 结构。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周AIGC轻量演示入口记录.md`。
- 数据来源：`data/aigc_media_samples.json`。
- API：`POST /api/aigc/preview`。
- 页面入口：顶部导航和左侧标签页新增 `AIGC 演示`。
- 页面能力：样例选择、图片占位展示、文字描述输入、风格模板选择、预览时长输入、快捷样例按钮、分镜预览展示。
- 原型口径：`template_preview`，不调用真实 AIGC 模型。
- 验证结果：`node --check src\ui\static\app.js`、`python -B tests/test_ui_demo.py`、`python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py` 均通过。

---

### 任务 9：查询、推荐、路径主链路整理

目标：
- 保证已有第九周、第十周功能在新 Web 骨架下继续可演示。

建议修改范围：
- `src/ui/demo_service.py`
- `src/ui/static/app.js`
- `src/ui/static/index.html`
- `tests/test_search.py`
- `tests/test_recommend.py`
- `tests/test_ui_demo.py`

检查内容：
- 综合查询仍能返回可规划路线的结果。
- 场所查询仍支持类别过滤和距离排序。
- 美食推荐仍支持 Top-K、距离排序和可选菜系过滤。
- 查询结果仍能一键进入单目标路径规划。
- 路径结果仍展示地图高亮、关键步骤、距离和时间。

依赖关系：
- 与任务 3、任务 4、任务 5 相关。

完成标准：
- 旧功能不因页面结构升级而退化。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周查询推荐路径主链路整理记录.md`。
- 本阶段没有改业务实现，主要补充防回归测试。
- 新增测试：`tests/test_ui_demo.py` 中的 `test_demo_main_query_recommend_route_chains_remain_available`。
- 覆盖链路：综合查询 -> 单目标路径、场所查询 -> 距离排序 -> 单目标路径、美食推荐 -> 距离排序 -> 单目标路径、查询/推荐结果 -> 多目标路径。
- 验证结果：`python -B tests/test_ui_demo.py`、`python -B tests/test_search.py`、`python -B tests/test_recommend.py`、`python -B tests/test_routing.py`、`python -B tests/test_integration.py` 均通过。

---

### 任务 10：测试与回归收口

目标：
- 用测试证明第十一周新增能力可验收。

建议测试命令：

```text
py -3 -B tests/test_graph_load.py
py -3 -B tests/test_routing.py
py -3 -B tests/test_search.py
py -3 -B tests/test_recommend.py
py -3 -B tests/test_diary.py
py -3 -B tests/test_integration.py
py -3 -B tests/test_fulltext.py
py -3 -B tests/test_compress.py
py -3 -B tests/test_ui_demo.py
py -3 -B tests/test_course_requirements.py
```

成员 B 重点新增或更新：
- `tests/test_diary.py`：日记创建、编辑、删除、评分、媒体占位。
- `tests/test_ui_demo.py`：正式 Web bootstrap、站点切换状态、多目标路径、AIGC 预览。
- `tests/test_search.py`：确认查询链路没有被页面状态改造影响。
- `tests/test_recommend.py`：确认美食推荐链路没有被页面状态改造影响。

完成标准：
- 成员 B 相关测试通过。
- 如果全量测试中出现 A/C 非本模块问题，记录到工作陈述的阻塞或风险中。

当前状态：
- 已完成。
- 产出记录：`工作进度/第十一周/memberB第11周测试与回归收口记录.md`。
- 本机 `py -3 -B` 不可用，返回 `No installed Python found!`，本次正式回归统一使用 `python -B`。
- 已通过测试：`tests/test_graph_load.py`、`tests/test_routing.py`、`tests/test_search.py`、`tests/test_recommend.py`、`tests/test_diary.py`、`tests/test_integration.py`、`tests/test_fulltext.py`、`tests/test_compress.py`、`tests/test_ui_demo.py`、`tests/test_course_requirements.py`。
- 已通过语法检查：`node --check src\ui\static\app.js`、`python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py src/diary/__init__.py`。
- 结论：暂未发现成员 B 新增内容导致的回归失败，可以进入任务 11 工作内容陈述。

---

### 任务 11：第十一周工作内容陈述

目标：
- 按协作规范提交成员 B 本周工作说明。

建议文件：
- `工作进度/第十一周/memberB第11周工作内容陈述.md`

内容结构：
- 本周完成事项。
- 涉及文件。
- 可演示入口。
- 测试命令与结果。
- 当前阻塞。
- 下周计划。

完成标准：
- 能清楚说明第十一周成员 B 如何支撑第 13 周正式产品冻结。

当前状态：
- 已完成。
- 产出文件：`工作进度/第十一周/memberB第11周工作内容陈述.md`。
- 内容覆盖：本周完成事项、涉及文件、可演示入口、测试命令与结果、当前阻塞与风险、下周计划、完成判定。
- 结论：成员 B 第十一周任务已达到可提交状态。

---

## 4. 建议执行路线

推荐按以下顺序推进：

1. 任务 1：启动对齐与接口边界确认。
2. 任务 2：跑当前基线测试，记录修改前状态。
3. 任务 3：正式 Web 主入口骨架。
4. 任务 4：站点状态与统一页面反馈。
5. 任务 5：多目标路径业务接入。
6. 任务 6：日记管理业务接口。
7. 任务 7：日记中心 Web 页面。
8. 任务 8：AIGC 轻量演示入口。
9. 任务 9：查询、推荐、路径主链路整理。
10. 任务 10：测试与回归收口。
11. 任务 11：第十一周工作内容陈述。

这样安排的原因：

- 先跑基线测试，可以明确修改前状态，避免后续定位问题时混淆原有失败和新增回归。
- 先做 Web 骨架和状态管理，可以避免后续多目标、日记、AIGC 各自堆临时页面。
- 多目标路径已有 A 侧接口，提前接入可以尽早暴露字段展示和不可达提示问题。
- 日记 CRUD 是成员 B 本周最明确的硬任务，适合在主入口稳定后接入页面。
- AIGC 轻量演示依赖 C 的样例数据，目前数据已存在，可以在中后段补入。
- 最后统一做测试和工作陈述，避免文档与实际代码不一致。

---

## 5. 需要接入别人内容的点

### 5.1 依赖成员 A

- 多目标路径接口 `query_multi_target(...)`。
- 路径结果字段：访问顺序、总距离、总时间、分段结果、关键步骤。
- 不可达路径时的错误信息口径。

当前判断：
- 远端代码已经具备多目标路径基础能力，本周可以先接入。
- 若展示字段不足，只做追加字段需求记录，不直接改 A 的核心路径算法。

### 5.2 依赖成员 C

- `data/users.json` 用户样例。
- `data/diary_data.json` 日记样例。
- `data/aigc_media_samples.json` AIGC 媒体样例。
- 课程硬指标核验脚本 `tests/test_course_requirements.py`。

当前判断：
- 上述基础数据和核验脚本已在远端存在，本周成员 B 可以直接读取并接入 UI。
- 若后续样例字段调整，需要同步更新 UI 解析逻辑和测试。

### 5.3 别人需要接入成员 B 的点

- Web 主入口和导航结构会成为第 13 周正式产品入口，A/C 后续演示能力需要接到这里。
- 日记 CRUD 和 AIGC 页面会使用 C 的数据样例，C 需要确认字段含义。
- 多目标路径展示会暴露 A 的路径结果，A 需要确认字段冻结口径。

---

## 6. 本周完成判定

成员 B 第十一周完成的最低标准：

1. Web 主入口具备正式产品骨架：首页、站点、导航、帮助、状态提示。
2. 日记中心具备查询、创建、编辑、删除、评分和媒体占位展示入口。
3. 多目标路径在浏览器中可触发，并展示访问顺序、总距离、总时间和关键步骤。
4. AIGC 轻量演示在浏览器中可触发，并展示预览结果。
5. 成员 B 相关测试更新并通过。
6. `memberB第11周工作内容陈述.md` 完成。

如果以上 6 项完成，可以认为成员 B 第十一周主要任务达到可提交状态。

当前整体判断：

- 以上 6 项均已完成。
- 成员 B 第十一周主要任务已达到可提交状态。
