# 地图方案 B 最终交付说明

## 1. 交付基线

- 当前分支：`experiment/map-plan-b`
- 当前阶段：`M32C` 课程答辩材料与扩站说明收口。
- 站点范围：`PKU` 基线站点 + 20 个扩展校园，共 21 个可用站点。
- 启动命令：`py -m src.ui.demo_server`
- 默认访问地址：`http://127.0.0.1:8765`
- 最终验证命令：`py -m pytest -q`

## 2. 当前可演示能力

| 模块 | 能力 | 演示方式 |
| --- | --- | --- |
| 多校园 | 站点选择器切换 `PKU`、`THU`、`WHU` 等 21 个站点 | 切换后地图、候选点、查询、推荐、路线均使用当前 `site_id` |
| 室外地图 | Leaflet + GeoJSON，保留 `simple_svg` fallback | 展示节点、道路、路线高亮和本地 Leaflet 资源 |
| 室内导航 | 每个扩展校园 5 个室内建筑入口 | 从图书馆等建筑进入楼层平面图和室内路线视图 |
| 路线规划 | 步行、自行车、混合交通；距离/时间两类策略 | 演示校门到图书馆、图书馆到食堂、室内目标路线 |
| 多目标路线 | 支持多个目标串联 | 演示“校门 -> 图书馆 -> 食堂” |
| 查询推荐 | 综合查询、查附近、餐饮推荐、兴趣推荐 | 切换用户和兴趣偏好，展示本校化结果与推荐理由 |
| 日记与离线能力 | 保留全文检索、日记推荐和哈夫曼压缩模块 | 作为课程要求覆盖项展示 |

## 3. M32 验收结果

| 阶段 | 产物 | 结论 |
| --- | --- | --- |
| `M31D` | `docs/地图方案B_M31D_20校推荐附近交通总回归.md`、`tests/test_m31d_regression.py` | 20 校交通、附近、兴趣推荐总回归通过 |
| `M32A` | `docs/地图方案B_M32A_API回归测试清单.md`、`tests/test_m32a_api_regression.py` | 21 站点核心 API 回归通过 |
| `M32B` | `docs/地图方案B_M32B_UI冒烟与演示路径清单.md`、`docs/M32B_UI_smoke_screenshots_demo_routes_report.md`、`tests/test_m32b_ui_smoke.py` | 20 校 UI 冒烟、演示路径和截图索引通过 |
| `M32C` | `docs/地图方案B_M32C_课程答辩材料与扩站说明.md`、`docs/地图方案B_M32_多校园总验收收口报告.md` | 答辩材料、扩站说明和最终交付说明已收口 |

## 4. 答辩演示脚本

1. 介绍项目定位：面向校园/景区的智能导览、查询推荐和室内外一体化路线。
2. 展示系统架构：`data/global_sites.json` 注册站点，`data/sites/<SITE_ID>/` 存放每校分层图数据，`DemoUIService(site_id)` 负责站点隔离。
3. 讲解课程算法：分层图、Dijkstra、状态压缩 DP、Top-K 排序、倒排索引和哈夫曼压缩。
4. 演示 PKU 基线：Leaflet 地图、路线规划、室内楼层和多目标路线。
5. 演示 20 校扩展：切换 `THU`、`WHU`、`HZAU`，重复查询、推荐、路线和室内入口。
6. 展示验收材料：打开 M31D/M32A/M32B/M32C 文档，说明 `py -m pytest -q` 全量回归。

## 5. 现场演示建议

- 演示前先执行 `netstat -ano | findstr :8765`，避免浏览器命中旧服务。
- 若端口空闲，执行 `py -m src.ui.demo_server` 并打开 `http://127.0.0.1:8765`。
- 优先展示 `PKU`、`THU`、`WHU`、`HZAU` 四个站点，兼顾基线真实地图、首批试点、景观校园和最后一所扩展校。
- 每个扩展校固定演示“校门 -> 图书馆 -> 食堂”，再进入图书馆室内视图。
- 截图材料索引见 `docs/M32B_UI_smoke_screenshots_demo_routes_report.md`；截图目录 `output/` 是未跟踪验证产物，不作为代码提交内容。

## 6. 课程覆盖索引

| 课程点 | 对应模块 |
| --- | --- |
| 图结构 | `src/graph/loader.py`、`data/sites/<SITE_ID>/outdoor.json`、`data/sites/<SITE_ID>/indoor_*.json` |
| 最短路径 | `src/routing/router.py` 的 Dijkstra 路线查询 |
| 多目标规划 | `/api/route/multi` 与 `query_multi_target` |
| 排序与推荐 | `src/search/`、`src/recommend/`、兴趣推荐和餐饮推荐 |
| 全文检索 | `src/diary/`、`src/compress/fulltext.py` 的倒排索引能力 |
| 数据压缩 | `src/compress/huffman.py` 的哈夫曼编码实现 |
| 工程测试 | `tests/test_m31d_regression.py`、`tests/test_m32a_api_regression.py`、`tests/test_m32b_ui_smoke.py` 与全量 pytest |

## 7. 后续边界

- M32C 不新增功能，只做最终文档、答辩材料和扩站说明收口。
- 运行时 UI/API 不直接调用 OSMnx、Overpass 或外部地图服务。
- 后续若继续提升 20 校真实道路几何覆盖，应使用离线准备脚本产出本地文件，并放入 `data/sites/<SITE_ID>/geo/` 后再接入。
- 不删除、不移动、不暂存无关未跟踪文件，尤其是 `scripts/`、`工作进度/`、`.codex_tmp/`、`.playwright-cli/`、`output/` 和 `data/sites/PKU/geo/pku_poi_overpass_raw.json`。

