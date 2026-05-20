# 地图方案 B M32B UI 冒烟与演示路径清单

## 1. 范围

- 阶段：`M32B` 多校园 UI 冒烟、截图与演示路径整理。
- 日期：2026-05-20。
- 站点范围：20 个扩展校园，不包含 PKU 基线站点。
- 执行原则：不新增运行时功能，不修改核心架构，不调用 OSMnx、Overpass、外部网络或 web search。
- 产物边界：本阶段只固化 UI 合同、20 校演示路线与截图索引；`output/` 下截图材料保持为未跟踪验证产物，不纳入本次代码提交范围。

## 2. UI 冒烟合同

| 区域 | 冒烟点 | 结论 |
| --- | --- | --- |
| 全局工具栏 | `site-selector` 可切换 20 校；`global-start-node`、`user-selector` 和 `interest-tags` 随站点数据可用 | 通过 |
| 功能页签 | 综合查询、场所查询、美食推荐、导航规划、日记中心、AIGC 演示、帮助说明入口存在 | 通过 |
| 地图面板 | `leaflet_geo` 与 `simple_svg` 两种渲染按钮存在，Leaflet 使用本地 `/vendor/leaflet/` 资源 | 通过 |
| 地图状态 | GeoJSON、路线、渲染器、底图和本地 OSM 状态标签可显示 | 通过 |
| 快捷演示 | 去图书馆、图书馆 + 食堂、清空路线三个地图快捷动作存在 | 通过 |
| 路线结果 | 路径摘要、路径步骤、地图高亮和室内导航面板入口存在 | 通过 |
| 兜底能力 | `simple_svg` fallback 保留；Leaflet 或 GeoJSON 失败时前端仍可回退简图 | 通过 |

## 3. 20 校演示路线与截图索引

| SITE_ID | 校园 | 单目标演示路线 | 多目标演示路线 | 代表性室内建筑 | 截图索引 |
| --- | --- | --- | --- | --- | --- |
| `THU` | 清华大学 | 清华大学北区入口 -> 清华大学图书馆 | 清华大学图书馆 + 桃李园 | 清华大学图书馆、第三教室楼 | `output/playwright/m32b_ui_smoke/THU_ui_smoke.png` |
| `WHU` | 武汉大学 | 武汉大学北侧湖滨入口 -> 武汉大学图书馆总馆 | 武汉大学图书馆总馆 + 桂园食堂 | 武汉大学图书馆总馆、武汉大学法学院 | `output/playwright/m32b_ui_smoke/WHU_ui_smoke.png` |
| `XMU` | 厦门大学 | 厦门大学大南校门 -> 厦门大学图书馆 | 厦门大学图书馆 + 厦门大学芙蓉餐厅 | 厦门大学图书馆、厦门大学南强二教学楼 | `output/playwright/m32b_ui_smoke/XMU_ui_smoke.png` |
| `ZJU` | 浙江大学 | 浙江大学紫金港校区北门 -> 浙江大学紫金港图书信息中心 | 浙江大学紫金港图书信息中心 + 浙江大学紫金港临湖餐厅 | 浙江大学紫金港图书信息中心、浙江大学紫金港东教学楼 | `output/playwright/m32b_ui_smoke/ZJU_ui_smoke.png` |
| `NJU` | 南京大学 | 南京大学仙林校区北门 -> 南京大学杜厦图书馆 | 南京大学杜厦图书馆 + 南京大学仙林校区九食堂 | 南京大学杜厦图书馆、南京大学仙林教学楼 | `output/playwright/m32b_ui_smoke/NJU_ui_smoke.png` |
| `FDU` | 复旦大学 | 复旦大学邯郸校区北门 -> 复旦大学文科图书馆 | 复旦大学文科图书馆 + 复旦大学邯郸校区南区食堂 | 复旦大学文科图书馆、复旦大学第三教学楼 | `output/playwright/m32b_ui_smoke/FDU_ui_smoke.png` |
| `SJTU` | 上海交通大学 | 上海交通大学闵行校区北门 -> 上海交通大学闵行校区图书馆 | 上海交通大学闵行校区图书馆 + 上海交通大学闵行校区第一餐饮大楼 | 上海交通大学闵行校区图书馆、上海交通大学东中院教学楼 | `output/playwright/m32b_ui_smoke/SJTU_ui_smoke.png` |
| `TONGJI` | 同济大学 | 同济大学四平路校区北门 -> 同济大学四平路校区图书馆 | 同济大学四平路校区图书馆 + 同济大学学苑食堂 | 同济大学四平路校区图书馆、同济大学四平路校区教学楼 | `output/playwright/m32b_ui_smoke/TONGJI_ui_smoke.png` |
| `SEU` | 东南大学 | 东南大学九龙湖校区北门 -> 东南大学李文正图书馆 | 东南大学李文正图书馆 + 东南大学九龙湖校区桃园食堂 | 东南大学李文正图书馆、东南大学九龙湖校区教学楼群 | `output/playwright/m32b_ui_smoke/SEU_ui_smoke.png` |
| `SYSU` | 中山大学 | 中山大学广州校区南校园北门 -> 中山大学广州校区南校园图书馆 | 中山大学广州校区南校园图书馆 + 中山大学南校园西区食堂 | 中山大学广州校区南校园图书馆、中山大学第一教学楼 | `output/playwright/m32b_ui_smoke/SYSU_ui_smoke.png` |
| `SCU` | 四川大学 | 四川大学望江校区北门 -> 四川大学望江校区图书馆 | 四川大学望江校区图书馆 + 四川大学望江校区学生食堂 | 四川大学望江校区图书馆、四川大学望江校区基础教学楼 | `output/playwright/m32b_ui_smoke/SCU_ui_smoke.png` |
| `HNU` | 湖南大学 | 湖南大学岳麓山校区北门 -> 湖南大学图书馆 | 湖南大学图书馆 + 湖南大学德智园学生食堂 | 湖南大学图书馆、湖南大学教学楼群 | `output/playwright/m32b_ui_smoke/HNU_ui_smoke.png` |
| `SDU` | 山东大学 | 山东大学中心校区北门 -> 山东大学中心校区图书馆 | 山东大学中心校区图书馆 + 山东大学中心校区学生食堂 | 山东大学中心校区图书馆、山东大学中心校区教学楼群 | `output/playwright/m32b_ui_smoke/SDU_ui_smoke.png` |
| `HUST` | 华中科技大学 | 华中科技大学主校区北门 -> 华中科技大学图书馆 | 华中科技大学图书馆 + 华中科技大学百景园食堂 | 华中科技大学图书馆、华中科技大学东九教学楼 | `output/playwright/m32b_ui_smoke/HUST_ui_smoke.png` |
| `SCUT` | 华南理工大学 | 华南理工大学五山校区北门 -> 华南理工大学五山校区图书馆 | 华南理工大学五山校区图书馆 + 华南理工大学五山校区学生食堂 | 华南理工大学五山校区图书馆、华南理工大学五山校区教学楼群 | `output/playwright/m32b_ui_smoke/SCUT_ui_smoke.png` |
| `OUC` | 中国海洋大学 | 中国海洋大学崂山校区北门 -> 中国海洋大学崂山校区图书馆 | 中国海洋大学崂山校区图书馆 + 中国海洋大学崂山校区学生食堂 | 中国海洋大学崂山校区图书馆、中国海洋大学崂山校区教学楼群 | `output/playwright/m32b_ui_smoke/OUC_ui_smoke.png` |
| `SUDA` | 苏州大学 | 苏州大学天赐庄校区北门 -> 苏州大学天赐庄校区图书馆 | 苏州大学天赐庄校区图书馆 + 苏州大学天赐庄校区学生食堂 | 苏州大学天赐庄校区图书馆、苏州大学天赐庄校区教学楼群 | `output/playwright/m32b_ui_smoke/SUDA_ui_smoke.png` |
| `HIT` | 哈尔滨工业大学 | 哈尔滨工业大学一校区北门 -> 哈尔滨工业大学一校区图书馆 | 哈尔滨工业大学一校区图书馆 + 哈尔滨工业大学一校区学生食堂 | 哈尔滨工业大学一校区图书馆、哈尔滨工业大学正心楼与教学楼群 | `output/playwright/m32b_ui_smoke/HIT_ui_smoke.png` |
| `YNU` | 云南大学 | 云南大学呈贡校区北门 -> 云南大学呈贡校区图书馆 | 云南大学呈贡校区图书馆 + 云南大学呈贡校区学生食堂 | 云南大学呈贡校区图书馆、云南大学呈贡校区教学楼群 | `output/playwright/m32b_ui_smoke/YNU_ui_smoke.png` |
| `HZAU` | 华中农业大学 | 华中农业大学狮子山校区北门 -> 华中农业大学图书馆 | 华中农业大学图书馆 + 华中农业大学博园食堂 | 华中农业大学图书馆、华中农业大学教学楼群 | `output/playwright/m32b_ui_smoke/HZAU_ui_smoke.png` |

## 4. 自动化验证

- 新增专项：`tests/test_m32b_ui_smoke.py`。
- 静态 UI 合同：解析 `src/ui/static/index.html`，检查站点切换、全功能页签、地图渲染切换、本地 Leaflet 资源、路线摘要与室内面板等关键 DOM 入口。
- 前端脚本合同：检查 `src/ui/static/app.js` 保留 `loadSiteBootstrap()`、`renderMap()`、`renderSvgMap()`、`renderLeafletMap()`、`ensureLeafletMap()`、`syncLeafletRouteLayer()` 和 `fallbackToSvgMap()` 等稳定入口。
- 20 校数据链路：通过临时端口 HTTP 服务逐校请求 bootstrap、GeoJSON、单目标路线和多目标路线，确认 UI 所需数据、预设、控件、室内建筑与路线高亮数据均可用。
- 截图结果索引：读取既有 `output/playwright/m32b_ui_smoke/m32b_ui_smoke_results.json` 作为人工/浏览器截图材料索引来源；该目录仍按脏工作区规则保持未跟踪，不暂存、不提交。

## 5. 结论

- 20 个扩展校园均具备可演示的站点切换、Leaflet 地图、综合查询、附近查询、美食推荐、单目标路线、多目标路线和室内建筑入口。
- M32B 未发现需要进入 M32C 前先修复的 UI 阻塞。
- 后续 M32C 可直接引用本清单的 20 校代表性建筑、演示路线和截图索引，收口课程答辩材料与扩站说明。
