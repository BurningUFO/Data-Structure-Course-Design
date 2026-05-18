# 地图方案 B M26D THU 试点校回归与问题清单

## 范围

本记录只覆盖 M26D：对试点校 `THU` 清华大学完成 M26A-M26C 后的主链路做回归验证，并沉淀后续批量扩站风险、修复建议和复制注意事项。

本阶段未新增功能，未进入 M27，未处理其他校园，未处理室内模板，未更新 `docs/地图方案B_M24-M32三层Agent执行状态台账.md`。

## 启动检查

| 命令 | 结果 |
| --- | --- |
| `git status --short --branch` | 当前分支为 `experiment/map-plan-b`，工作区存在既有未提交/未跟踪文件。 |
| `git branch --show-current` | `experiment/map-plan-b` |

## 回归验证结果

### 测试集

| 命令 | 结果 |
| --- | --- |
| `python -m pytest` | 退出码 1，当前 shell 下 `python` 无可见输出；未作为有效解释器继续使用。 |
| `py -m pytest -q tests/test_ui_demo.py::test_m26b_thu_backend_main_chain_is_available_without_frontend_switch tests/test_ui_demo.py::test_m26c_thu_frontend_switch_contract_and_leaflet_data` | 2 passed。 |
| `py -m pytest` | 144 passed in 28.30s。 |

说明：本地 `py` 启动器解析到 Python 3.13.1，后续烟测统一使用 `py`。

### API 烟测

临时端口：`8897`，脚本启动并自动清理 demo server。覆盖 `THU` 与 `PKU`：

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/map/geojson`
- `GET /api/map/osm-layers`
- `POST /api/search/scenic`
- `POST /api/search/places`
- `POST /api/recommend/catering`
- `POST /api/route`
- `POST /api/route/multi`

| 站点 | 结果摘要 |
| --- | --- |
| `THU` | health/bootstrap/GeoJSON/OSM 降级、综合查询、场所查询、美食推荐、单目标路线、多目标路线全部成功。GeoJSON：22 nodes、21 edges、43 features、21 fallback edges。查询首命中：`library`、`restroom_main`、`canteen`。`gate_west -> library` 路线 2785.31m，多目标 `library,canteen` 4000.04m。 |
| `PKU` | 同一 API 矩阵全部成功。GeoJSON：1090 nodes、1274 edges、2364 features、0 fallback edges，OSM 本地图层 3 个可用。`gate_north -> library` 路线 341.45m，多目标 1020.45m。 |

### 前端烟测

临时端口：`8898`，使用 Playwright CLI。检查结果：

1. 页面可加载，控制台 warning/error 为 0。
2. 站点切换器可选择 `THU`，其他未接入校园仍 disabled。
3. 切到 `THU` 后：
   - 标题为 `清华大学 导览演示台`。
   - Leaflet 地图可见。
   - 地图状态为 `地点 15 · 道路 21 · 线形覆盖 0%`。
   - 起点/目标选项来自 THU，包含 `gate_north/gate_west/library/canteen` 等。
4. 在 UI 中规划 `THU` 默认起点到 `library`：
   - 路线成功，`site_id=THU`。
   - 路径节点：`gate_north -> road_zijing_axis -> road_xuetang_south -> library`。
   - 距离 1163.87m。
5. 切回 `PKU` 后：
   - 标题恢复为 `北京大学 导览演示台`。
   - 地图状态恢复为 `地点 111 · 道路 1274 · 线形覆盖 100%`。
   - 路线状态重置为 `路线未规划`。
   - 起点/目标选项恢复为 PKU 数据，未发现 THU 目标残留。

浏览器网络记录中，部分 OpenStreetMap 外部瓦片请求在切换过程中出现 `net::ERR_ABORTED`，但本地 GeoJSON、OSM 层接口和路线叠加均正常；这属于外部瓦片依赖/切换取消风险，不影响 M26D 主链路通过。

## 风险点与修复建议

1. `THU` 仍标记为 `is_available=false`、`data_status=backend_ready`。前端已允许 `backend_ready` 作为试点可演示状态，但进入 M27X/M27Y 前应统一状态语义，避免批量扩站时误把占位校当作可演示校。
2. `THU` 的 GeoJSON 线形覆盖为 0%，21 条边全部是端点 fallback 直线。当前 M26D 可接受，但后续复制时必须明确“可导航”不等于“真实道路几何已完成”，不要把该状态包装成真实路网。
3. `THU` 暂无本地 OSM 上下文图层，`/api/map/osm-layers?site_id=THU` 正常返回空图层。后续若接入真实地图层，应放到对应离线数据阶段，不要在运行时调用 OSMnx、Overpass 或外部抓取接口。
4. 查询和推荐依赖每校 `outdoor.json` 中的标准 category 与核心 POI。扩到新校时若缺少 `education/restroom/catering` 等演示类别，会导致主链路空结果，应在单校复制前按 M25D 清单强制补齐。
5. UI 默认起点会按当前站点自动解析；THU 当前默认是 `gate_north`，而部分 API 烟测显式使用 `gate_west`。后续回归脚本应固定起点，避免默认起点调整造成误判。
6. THU 当前未声明室内能力。后续文档、bootstrap 文案和验收口径不要把 THU 标为室内可用，直到 M29/M30 类阶段补齐室内注册、入口和室内图。
7. 本地 `python` 命令在当前 shell 下不可用或无输出失败，`py` 可正常执行。后续自动化验证应优先记录实际可用解释器，避免同一命令在不同 shell 下产生假失败。
8. Playwright CLI 会生成 `.playwright-cli/`，临时服务日志会生成 `.codex_tmp/`。这些目录应在验证后清理，不能纳入提交。

## 批量扩站复制注意事项

1. 每校只在当前阶段允许的目录和注册项内修改；不要顺手改 PKU、其他校园、室内模板或全局算法。
2. 每个新校园至少跑一次同样的 API 矩阵：health、bootstrap、GeoJSON、OSM 降级、综合查询、场所查询、餐饮推荐、单目标路线、多目标路线。
3. 所有 POST 请求体必须显式带 `site_id`，并在响应中检查结果项 `site_id`，防止串校。
4. 对中文关键词做 PowerShell 烟测时使用 `json.dumps(..., ensure_ascii=True)` 或 Unicode escape，避免请求体编码被 shell 干扰。
5. 浏览器检查前先确认端口是否被旧服务占用；不确定时使用临时端口。结束时按准确 PID 清理服务，避免用过宽的 CommandLine 匹配误伤当前 shell。
6. 前端复制验收必须检查双向切换：目标校 -> PKU，并确认路线状态、地图数据、起点/目标选项都被重置。

## 结论

`THU` 作为 M26 试点校的室外主链路已通过回归：可切换、可显示 Leaflet GeoJSON、可综合查询、可场所查询、可美食推荐、可单目标和多目标路径规划；`PKU` 既有 API、GeoJSON/OSM 层和前端切换未回退。后续可进入由上层调度的 M27X/M27Y，但本阶段不执行。
