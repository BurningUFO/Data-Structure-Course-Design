# 地图方案 B M7：真实瓦片底图接入记录

## 1. 本阶段范围

M7 只把 Leaflet 真实瓦片底图接入现有 `leaflet_geo` 渲染器，并保留无底图和 `simple_svg` 回退。

本阶段没有修改：

1. 路由算法。
2. graph loader 语义。
3. `data/sites/PKU/outdoor.json` 中的 route geometry 数据。
4. 搜索、推荐、日记、压缩等非地图模块。
5. OSMnx、Overpass 或任何运行时路网下载流程。

## 2. 底图模式

前端新增 Leaflet 底图模式：

1. `real_map`：使用 Leaflet `L.tileLayer(...)` 加载真实瓦片底图。
2. `none`：移除外部瓦片 layer，仅显示本地空白底图和项目 GeoJSON 图层。

普通道路、节点和路线高亮仍由项目本地 GeoJSON 驱动，叠加在底图上方。路线高亮增加白色描边和高对比橙色主线，以便在真实底图上仍可辨认。

## 3. 底图来源与 attribution

当前演示底图使用 OpenStreetMap 标准瓦片：

```text
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

Leaflet tile layer 显示 attribution：

```text
© OpenStreetMap contributors
```

页面状态条和 caption 同时说明当前底图模式、底图来源、网络依赖，以及“项目道路、节点和路线来自本地 GeoJSON”。

## 4. 合规限制

OpenStreetMap 标准瓦片只适合低频课程演示，不适合作为无约束生产依赖。长期生产应改用合规瓦片服务、商业瓦片服务，或自托管瓦片服务。

本仓库不下载、不缓存、不提交外部瓦片。原因：

1. OSM 标准瓦片策略禁止批量下载、预取或离线打包。
2. 仓库内固化瓦片会带来授权、更新和体积问题。
3. M7 的目标只是验证真实底图展示，不承担离线地图数据交付。

## 5. 网络失败与回退

当 `real_map` 瓦片请求失败时：

1. Leaflet map 不回退到 SVG。
2. tile layer 只标记底图加载异常。
3. 本地 GeoJSON 道路、节点和路线高亮继续显示。
4. 用户可切换到 `none` 无底图模式进行弱网演示。

当 Leaflet 运行库、Leaflet 容器或 GeoJSON 请求异常时，前端继续调用 `fallbackToSvgMap()`，回退到 `simple_svg` 稳定简图。

## 6. 后续阶段边界

M8 才处理 OSM-derived roads / buildings / water / landuse 的离线抽取和本地化。M9 才处理课程图 edge 与 OSM 道路线形匹配。M7 不做这两类工作。
