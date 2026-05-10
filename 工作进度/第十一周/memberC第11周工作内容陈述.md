# memberC 第11周工作内容陈述

> 角色：Member C（数据、检索、压缩、测试与文档负责人）  
> 周期：2026-05-11 至 2026-05-17

---

## 1. 本周完成事项

1. 补齐课程要求中的 `>=10` 用户样例，新增 `data/users.json`，并将 `data/diary_data.json` 的独立 `author_id` 调整到 10 个。
2. 补齐日记媒体占位和 AIGC 轻量演示样例，新增 `data/aigc_media_samples.json`，提供“图片占位 + 文字描述 -> 预览占位”的接入数据。
3. 扩展 `data/成员Cdata/scenic_spots.json` 到 208 条推荐 / 查询对象，用于课程 `200+` 对象规模核验。
4. 扩展 PKU 标准分层图数据，当前合计 58 个节点、200 条边，服务设施口径节点 53 个。
5. 新增并升级 `tests/test_course_requirements.py`，将用户数、日记作者数、200+ 对象、50+ 服务设施、200+ 边数纳入强断言。
6. 同步更新 `docs/课程要求覆盖清单.md`、`docs/数据字典.md`、`docs/项目代码骨架与职责划分.md` 和课程硬指标核验记录。

---

## 2. 涉及文件

- `data/users.json`
- `data/diary_data.json`
- `data/aigc_media_samples.json`
- `data/成员Cdata/scenic_spots.json`
- `data/sites/PKU/outdoor.json`
- `tests/test_course_requirements.py`
- `docs/课程要求覆盖清单.md`
- `docs/数据字典.md`
- `docs/项目代码骨架与职责划分.md`
- `工作进度/第十一周/memberC第11周课程硬指标核验记录.md`

---

## 3. 测试命令

```powershell
python -B tests/test_course_requirements.py
python -B tests/test_graph_load.py
python -B tests/test_routing.py
python -B tests/test_search.py
python -B tests/test_recommend.py
python -B tests/test_ui_demo.py
python -B tests/test_integration.py
python -B tests/test_diary.py
python -B tests/test_fulltext.py
python -B tests/test_compress.py
```

---

## 4. 当前阻塞

- AIGC / 媒体占位样例已经具备，但 Web 可见入口和预览展示依赖 Member B 接入。
- 200 条边数据已经可加载和测试，正式性能验证、典型路径性能记录依赖 Member A 补充。
- 扩展对象池已达 208 条，但多数对象暂不映射校园图，后续若进入 Web 默认推荐链路，需要 Member B 确认数据源切换策略。

---

## 5. 下周计划

1. 配合 Member A 对 200+ 边规模下的路径规划做性能验证。
2. 配合 Member B 将媒体占位和 AIGC 样例接入 Web 日记中心。
3. 继续优化扩展对象真实性、分类覆盖和最终验收材料。
4. 将课程要求核验脚本作为第 12 周全量联调的固定入口。

---

## 6. 可演示入口

- 课程硬指标核验：`python -B tests/test_course_requirements.py`
- Web 主入口：`python -m src.ui.demo_server`
- 默认地址：`http://127.0.0.1:8765`
