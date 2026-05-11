# memberB第11周测试与回归收口记录

## 1. 任务定位

第 10 项目标是用测试证明第十一周成员 B 新增能力可验收，同时确认第九周、第十周已有查询、推荐、路径、日记、全文检索和压缩链路没有因为 Web 骨架升级而退化。

## 2. 执行口径

推进清单中的建议命令为 `py -3 -B ...`。

当前本机环境中 `py -3 -B tests/test_ui_demo.py` 返回：

```text
No installed Python found!
```

因此本次正式回归统一使用：

```text
python -B <test_script>
```

前端脚本使用：

```text
node --check src\ui\static\app.js
```

Python 服务模块语法检查使用：

```text
python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py src/diary/__init__.py
```

## 3. 测试结果汇总

全部通过：

- `python -B tests/test_graph_load.py`
- `python -B tests/test_routing.py`
- `python -B tests/test_search.py`
- `python -B tests/test_recommend.py`
- `python -B tests/test_diary.py`
- `python -B tests/test_integration.py`
- `python -B tests/test_fulltext.py`
- `python -B tests/test_compress.py`
- `python -B tests/test_ui_demo.py`
- `python -B tests/test_course_requirements.py`
- `node --check src\ui\static\app.js`
- `python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py src/diary/__init__.py`

## 4. 重点覆盖内容

图加载：

- 标准 PKU 分层图可加载。
- 当前标准图规模为 58 个节点。

路径：

- 单目标路径可用。
- 跨层路径可用。
- 多目标路径可用。
- 不可达节点能返回失败信息。

查询：

- 精确查询、模糊查询、同义词/缩写匹配可用。
- 标准站点数据查询可用。
- 场所查询距离排序可用。
- 缺失节点、不可达距离、距离接口异常状态可被识别。

推荐：

- Top-K 排序可用。
- 按热度、评分、距离排序可用。
- 美食推荐和菜系过滤可用。

日记：

- 标准日记数据加载可用。
- 标题、目的地、热度、评分排序可用。
- 全文检索可用。
- 创建、编辑、评分、删除的内存态管理流程可用。
- 图片/视频媒体占位字段可保留。

Web 主入口：

- Bootstrap、站点状态、统一反馈可用。
- 综合查询、场所查询、美食推荐、路径规划、日记中心、AIGC 演示均可进入。
- 查询/推荐结果可继续进入单目标路径。
- 查询/推荐结果可组合进入多目标路径。
- AIGC 轻量预览返回模板化分镜结构。

课程硬指标：

- 用户样例数量满足当前脚本检查。
- 日记作者数量满足当前脚本检查。
- AIGC 媒体占位样例存在。
- 必需课程文档存在。
- 第十二周规模差距快照可输出。

## 5. 风险与备注

当前没有发现成员 B 新增内容导致的测试失败。

需备注的环境问题：

- `py -3 -B` 在当前本机不可用，后续复现建议使用 `python -B`。

需备注的产品口径：

- 日记管理仍为 `memory_only`，不写回 `data/diary_data.json`。
- AIGC 演示仍为 `template_preview`，不调用真实生成模型。

## 6. 结论

第 10 项测试与回归收口完成。

当前第十一周成员 B 已完成的 Web 骨架、站点反馈、多目标路径、日记管理、日记中心、AIGC 轻量演示和查询推荐路径主链路均通过回归验证，可以进入第 11 项工作内容陈述。
