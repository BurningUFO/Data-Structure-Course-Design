# memberB 第11周工作内容陈述

> 角色：Member B（查询、排序、推荐、业务交互与 Web 主入口负责人）
> 周期：2026-05-11 至 2026-05-17
> 阶段定位：第 13 周正式产品入口骨架与业务链路收口阶段

---

## 1. 本周完成事项

1. 完成第十一周启动对齐，明确成员 B 本周负责范围：Web 主入口、站点状态、查询推荐路径展示、日记管理、AIGC 轻量演示和测试收口。
2. 记录修改前基线测试状态，确认当前本机 `py -3 -B` 不可用，统一改用 `python -B` 执行测试。
3. 将 `src/ui/` 从第十周临时演示页升级为正式 Web 主入口骨架，补齐首页、站点选择、主导航、功能卡片和帮助说明。
4. 完成站点状态与统一页面反馈，支持站点切换后重置结果、路径、地图高亮和表单状态。
5. 接入成员 A 的多目标路径接口 `query_multi_target(...)`，Web 中可展示访问顺序、总距离、总时间、分段摘要和关键路径步骤。
6. 补齐日记管理业务接口，支持创建、编辑、删除、评分、图片占位和视频占位字段。
7. 将日记管理接口接入 Web 日记中心，浏览器中可完成全文检索、创建、载入编辑、更新、评分、删除和从日记目的地进入路线规划。
8. 接入成员 C 提供的 `data/aigc_media_samples.json`，完成 AIGC 轻量演示入口，支持“图片占位 + 文字描述 -> 模板化分镜预览”。
9. 整理查询、推荐、路径主链路，补充防回归测试，确认综合查询、场所查询、美食推荐结果仍可进入单目标和多目标路径。
10. 完成第十一周测试与回归收口，全部建议测试脚本和语法检查均通过。

---

## 2. 涉及文件

代码：

- `src/diary/__init__.py`
- `src/diary/diary_service.py`
- `src/ui/demo_server.py`
- `src/ui/demo_service.py`
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`

测试：

- `tests/test_diary.py`
- `tests/test_ui_demo.py`

第十一周成员 B 过程文档：

- `工作进度/第十一周/memberB第11周任务推进清单.md`
- `工作进度/第十一周/memberB第11周接口边界确认记录.md`
- `工作进度/第十一周/memberB第11周基线测试记录.md`
- `工作进度/第十一周/memberB第11周Web主入口骨架记录.md`
- `工作进度/第十一周/memberB第11周站点状态与统一反馈记录.md`
- `工作进度/第十一周/memberB第11周多目标路径接入记录.md`
- `工作进度/第十一周/memberB第11周日记管理业务接口记录.md`
- `工作进度/第十一周/memberB第11周日记中心Web页面记录.md`
- `工作进度/第十一周/memberB第11周AIGC轻量演示入口记录.md`
- `工作进度/第十一周/memberB第11周查询推荐路径主链路整理记录.md`
- `工作进度/第十一周/memberB第11周测试与回归收口记录.md`
- `工作进度/第十一周/memberB第11周工作内容陈述.md`

---

## 3. 可演示入口

启动 Web：

```powershell
python -B -m src.ui.demo_server
```

浏览器访问：

```text
http://127.0.0.1:8765
```

可演示功能：

1. 首页查看当前站点、地图节点数、可规划目标数和日记样本数。
2. 综合查询中搜索 `图书馆`，从结果进入单目标路径规划。
3. 场所查询中搜索 `洗手间`，查看按真实路径距离排序的结果。
4. 美食推荐中查看餐饮 Top-K 和距离排序结果。
5. 导航规划中选择多个目标点，展示多目标路径访问顺序、总距离、总时间和分段步骤。
6. 日记中心中执行全文检索，并从日记目的地进入路线规划。
7. 日记中心中创建、编辑、评分、删除一条内存态日记，并查看图片 / 视频媒体占位。
8. AIGC 演示中选择样例，输入文字描述，生成模板化分镜预览。

---

## 4. 测试命令与结果

当前环境未识别 `py` 启动器，`py -3 -B tests/test_ui_demo.py` 返回：

```text
No installed Python found!
```

因此本周正式测试统一使用 `python -B`。

已通过：

```powershell
python -B tests/test_graph_load.py
python -B tests/test_routing.py
python -B tests/test_search.py
python -B tests/test_recommend.py
python -B tests/test_diary.py
python -B tests/test_integration.py
python -B tests/test_fulltext.py
python -B tests/test_compress.py
python -B tests/test_ui_demo.py
python -B tests/test_course_requirements.py
```

语法检查已通过：

```powershell
node --check src\ui\static\app.js
python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py src/diary/__init__.py
```

关键测试结论：

- `tests/test_ui_demo.py` 覆盖 Web bootstrap、站点状态、多目标路径、日记管理、日记中心、AIGC 预览和查询推荐路径主链路。
- `tests/test_diary.py` 覆盖日记创建、编辑、评分、删除、媒体占位和全文检索。
- `tests/test_search.py` 和 `tests/test_recommend.py` 确认原有查询推荐链路没有退化。
- `tests/test_integration.py` 确认查询、推荐、路径、日记、全文检索和压缩主链路联调通过。

---

## 5. 当前阻塞与风险

当前没有发现成员 B 新增内容导致的回归失败。

需要说明的产品口径：

1. 日记管理当前为 `memory_only` 内存态演示，不写回 `data/diary_data.json`，刷新服务后恢复标准样例数据。
2. AIGC 当前为 `template_preview` 轻量原型，不调用真实生成模型。
3. 当前 Web 主入口主要服务第十一周产品骨架和第十三周正式入口冻结，后续还需要继续做页面细节、错误提示和展示体验优化。

协作依赖：

1. 成员 A 后续如果调整路径字段，需要保持追加字段方式，避免破坏当前 Web 展示使用的 `visit_order`、`total_distance_m`、`estimated_time_s`、`leg_results` 和 `segments`。
2. 成员 C 后续如果调整日记或 AIGC 样例字段，需要同步通知成员 B 更新 UI 解析和测试断言。

---

## 6. 下周计划

1. 配合第十二周任务继续完善 Web 主入口，把当前第十一周骨架推进到更接近正式产品页面。
2. 若课程要求需要持久化日记管理，基于当前接口增加受控写回或临时用户数据文件。
3. 如果 AIGC 需要更真实的演示效果，在当前 `template_preview` 结构上扩展更多模板、样例和预览字段。
4. 继续维护查询、推荐、路径、日记和 AIGC 的回归测试，避免第十二周新增功能破坏主链路。

---

## 7. 完成判定

成员 B 第十一周任务已经达到可提交状态：

- Web 主入口骨架完成。
- 站点状态与统一反馈完成。
- 多目标路径 Web 接入完成。
- 日记管理业务接口完成。
- 日记中心 Web 页面完成。
- AIGC 轻量演示入口完成。
- 查询推荐路径主链路整理完成。
- 测试与回归收口完成。
- 工作内容陈述完成。
