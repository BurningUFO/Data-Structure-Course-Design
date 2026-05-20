# 地图方案 B M32A API 回归测试清单

## 1. 范围

- 阶段：`M32A` 多校园 API 回归与测试清单。
- 日期：2026-05-20。
- 站点范围：`PKU` 基线站点 + 20 个扩展校园，共 21 个可用站点。
- 执行原则：不新增功能，不调用 OSMnx、Overpass 或外部网络；仅固化 API 回归矩阵、补充测试并记录结论。

## 2. 覆盖站点

| 类别 | SITE_ID |
| --- | --- |
| 基线站点 | `PKU` |
| 20 校扩展站点 | `THU`, `WHU`, `XMU`, `ZJU`, `NJU`, `FDU`, `SJTU`, `TONGJI`, `SEU`, `SYSU`, `SCU`, `HNU`, `SDU`, `HUST`, `SCUT`, `OUC`, `SUDA`, `HIT`, `YNU`, `HZAU` |

## 3. API 回归矩阵

| 接口 | 请求方式 | 回归断言 | 结论 |
| --- | --- | --- | --- |
| `/api/bootstrap?site_id=<SITE_ID>` | GET | 返回当前 `site.id`；站点为 `available`；站点列表包含 PKU + 20 校；`map_renderer=leaflet_geo`；保留 `map_capabilities.geojson_endpoint` 与 `indoor_map_endpoint`；室内导航可用 | 通过 |
| `/api/map/geojson?site_id=<SITE_ID>` | GET | 返回 `FeatureCollection`；节点、边和总 feature 数均大于 0；`stats.feature_count` 与实际 features 数一致；`site_id` 隔离正确 | 通过 |
| `/api/search/scenic` | POST | 使用当前站点默认用户做兴趣排序；返回成功且结果非空；结果 `site_id` 全部等于当前站点；兴趣上下文用户 ID 不串站 | 通过 |
| `/api/search/places` | POST | 按当前站点默认起点查询 `education`；返回成功且结果非空；响应 filters 与结果 `site_id` 均锁定当前站点 | 通过 |
| `/api/recommend/catering` | POST | 按当前站点默认起点查询餐饮推荐；返回成功且结果非空；响应 filters 与结果 `site_id` 均锁定当前站点 | 通过 |
| `/api/route` | POST | 默认起点到 `library`，`mixed + shortest_time`；返回成功；`site_id`、目标点和路线 GeoJSON 契约稳定 | 通过 |
| `/api/route/multi` | POST | 默认起点串联 `library`、`canteen`，不返程；返回成功；`route_type=multi_target`；目标顺序保持稳定 | 通过 |
| `/api/map/indoor?site_id=<SITE_ID>&building_id=<BUILDING>&floor=<FLOOR>` | GET | 每站取第一个支持室内导航的建筑默认楼层；返回 `svg_floorplan`；节点与边非空；`building_id`、`site_id` 正确 | 通过 |
| `/api/route` 室内目标 | POST | 默认起点到图书馆室内目标，`walk + shortest_time`；返回成功；响应包含 `indoor_route_views` 与室内可视图入口 | 通过 |
| `/api/route/multi` 室内目标 | POST | 默认起点串联 `library` 和图书馆室内目标；返回成功；多目标路线包含室内路线视图 | 通过 |

## 4. 逐站点回归结果

| 站点 | 室外 GeoJSON 节点/边 | 室内建筑数 | 室外路线 | 室内路线 | 查询/推荐 |
| --- | ---: | ---: | --- | --- | --- |
| `PKU` | 1090/1274 | 20 | 通过 | 通过 | 通过 |
| `THU` | 25/24 | 5 | 通过 | 通过 | 通过 |
| `WHU` | 31/33 | 5 | 通过 | 通过 | 通过 |
| `XMU` | 33/34 | 5 | 通过 | 通过 | 通过 |
| `ZJU` | 32/37 | 5 | 通过 | 通过 | 通过 |
| `NJU` | 44/47 | 5 | 通过 | 通过 | 通过 |
| `FDU` | 38/41 | 5 | 通过 | 通过 | 通过 |
| `SJTU` | 36/40 | 5 | 通过 | 通过 | 通过 |
| `TONGJI` | 38/43 | 5 | 通过 | 通过 | 通过 |
| `SEU` | 38/45 | 5 | 通过 | 通过 | 通过 |
| `SYSU` | 38/41 | 5 | 通过 | 通过 | 通过 |
| `SCU` | 37/41 | 5 | 通过 | 通过 | 通过 |
| `HNU` | 38/42 | 5 | 通过 | 通过 | 通过 |
| `SDU` | 38/42 | 5 | 通过 | 通过 | 通过 |
| `HUST` | 40/44 | 5 | 通过 | 通过 | 通过 |
| `SCUT` | 41/45 | 5 | 通过 | 通过 | 通过 |
| `OUC` | 41/44 | 5 | 通过 | 通过 | 通过 |
| `SUDA` | 41/48 | 5 | 通过 | 通过 | 通过 |
| `HIT` | 41/45 | 5 | 通过 | 通过 | 通过 |
| `YNU` | 41/45 | 5 | 通过 | 通过 | 通过 |
| `HZAU` | 41/46 | 5 | 通过 | 通过 | 通过 |

## 5. 自动化测试

- 新增专项：`tests/test_m32a_api_regression.py`。
- 启动方式：测试内使用 `ThreadingHTTPServer(("127.0.0.1", 0), build_handler(DemoUIService("PKU")))` 启动临时端口，避免命中 8765 旧进程。
- 覆盖方式：通过真实 HTTP GET/POST 调用核心 API，而不是仅调用服务层函数。
- 额外隔离检查：循环 21 个站点后再次请求 `PKU` bootstrap，确认站点切换后 PKU 仍返回自身数据。

## 6. 结论与风险

- 结论：PKU 与 20 个扩展校园的核心 API 契约保持稳定，站点切换、查询、推荐、室外导航、室内地图和室内导航接口均通过 M32A 回归。
- 当前阶段未发现需进入 M32B/M32C 的 API 阻塞问题。
- 既有差异说明：PKU 使用更完整的本地 OSM 派生数据，因此 GeoJSON 节点/边数量显著高于 20 个扩展校园；这属于当前数据形态差异，不是 M32A 回归失败。
- 非本阶段范围：UI 冒烟、截图、演示路径整理和答辩材料收口留给 M32B/M32C，不在本清单扩展。
