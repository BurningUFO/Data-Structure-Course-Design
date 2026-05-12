# 地图方案 B M8：离线 OSM 数据抽取与本地化记录

## 1. 本阶段范围

M8 在 M7 真实瓦片底图基础上增加本地 OSM 派生图层，目标是让 Leaflet 地图在运行时可以从仓库本地读取 roads / buildings / water / landuse GeoJSON。

本阶段没有修改：

1. 路由算法。
2. graph loader 语义。
3. 课程图 edge 与 OSM 道路线形匹配逻辑。
4. `data/sites/PKU/outdoor.json` 的课程图节点、边和 route geometry。
5. 搜索、推荐、日记、压缩等非地图模块。

M9 才处理课程图 edge 到 OSM geometry 的匹配。本阶段 OSM roads 只作为地图上下文图层展示，不作为 routing authority。

## 2. 数据文件

本地数据目录：

```text
data/sites/PKU/geo/
```

文件清单：

| 文件 | 内容 | 当前 feature 数 |
| --- | --- | --- |
| `osm_roads_raw.geojson` | Overpass 抽取的 PKU 周边 OSM highway 原始 GeoJSON | 505 |
| `osm_roads_simplified.geojson` | 用轻量 Douglas-Peucker 逻辑简化后的 roads 展示图层 | 505 |
| `osm_buildings.geojson` | OSM building polygon 图层 | 353 |
| `osm_water_landuse.geojson` | OSM water / waterway / grass / forest / meadow / recreation_ground / village_green / park / garden 图层 | 74 |
| `osm_extract_metadata.json` | 数据来源、查询条件、抽取日期、license、统计和运行时策略 | - |

所有 GeoJSON 坐标均按 RFC 7946 使用 `[lng, lat]` 顺序。

## 3. 数据来源

数据来源为 OpenStreetMap，通过 Overpass API 在准备阶段一次性抽取并保存到仓库本地文件。

抽取日期：

```text
2026-05-12
```

Overpass endpoint：

```text
https://overpass-api.de/api/interpreter
```

抽取范围：

```text
south=39.987
west=116.3005
north=39.997
east=116.3165
```

查询条件记录在：

```text
data/sites/PKU/geo/osm_extract_metadata.json
```

本次数据状态：

```text
formal_osm_overpass_extract
```

这不是手工样例数据；它是一次真实 OSM / Overpass 抽取结果。若未来网络不可用，也可以按 M8 goal 中的备选策略 B 替换为最小本地样例，但需要同步更新 metadata。

## 4. License / Attribution

OSM 数据 license：

```text
Open Database License (ODbL) 1.0
```

页面和 metadata 使用 attribution：

```text
© OpenStreetMap contributors
```

版权说明链接：

```text
https://www.openstreetmap.org/copyright
```

本仓库没有下载或提交外部瓦片。M8 只提交本地 OSM 派生 GeoJSON。

## 5. 运行时行为

新增后端接口：

```text
GET /api/map/osm-layers?site_id=PKU
```

返回结构包含：

1. `layers.roads`
2. `layers.buildings`
3. `layers.water_landuse`
4. `metadata`
5. `stats`
6. `warnings`

Web UI 运行时只读取 `data/sites/PKU/geo/` 下的本地文件，不调用 OSMnx 或 Overpass。若某个本地文件缺失，接口仍返回 `success=true`、该图层为空，并在 `warnings` / `stats.missing_files` 中说明；`/api/bootstrap`、`/api/map/geojson`、`/api/route`、`/api/route/multi` 不受影响。

## 6. 前端图层

Leaflet 图层顺序：

1. tile basemap
2. water / landuse
3. buildings
4. OSM roads
5. 项目 roads
6. 项目 nodes
7. route overlay

地图工具栏新增本地 OSM 图层开关：

1. `OSM 道路`
2. `建筑`
3. `水域/绿地`

默认开启三个本地图层。样式保持克制，项目道路、节点和路线高亮仍比 OSM 上下文图层更醒目。无底图模式下，本地 OSM 图层仍可显示在 Leaflet 空白底图上。

## 7. 已知限制

1. OSM 数据完整性取决于 OpenStreetMap 社区数据，可能缺少部分校园内部道路、建筑轮廓或地物名称。
2. 本阶段没有把课程图 edge 匹配到 OSM road geometry；路线高亮仍来自课程图的 `route_geojson` / fallback line。
3. `osm_roads_simplified.geojson` 只用于展示上下文，不用于计算路径。
4. 抽取范围覆盖 PKU 周边演示区域，不代表完整北京大学或更大城市区域。
5. 若未来替换数据，需重新验证坐标顺序、feature 类型、license attribution 和 UI 图层顺序。

## 8. 替换数据方式

替换为新的 OSM 数据时：

1. 使用 Overpass 或 OSMnx 在准备阶段抽取数据，不要在 Web UI 请求时实时联网。
2. 输出或转换为 GeoJSON `FeatureCollection`。
3. 保持文件名：
   - `osm_roads_raw.geojson`
   - `osm_roads_simplified.geojson`
   - `osm_buildings.geojson`
   - `osm_water_landuse.geojson`
   - `osm_extract_metadata.json`
4. 确认所有坐标顺序为 `[lng, lat]`。
5. 更新 `osm_extract_metadata.json` 的 `extracted_at`、bbox、查询条件、feature 统计和 data status。
6. 运行：

```powershell
py -m pytest tests/test_ui_demo.py
py -m pytest
```

7. 启动 demo server，检查 `/api/map/osm-layers?site_id=PKU` 和浏览器图层显示。

## 9. 验收说明

M8 验收重点：

1. 本地 GeoJSON 文件存在且可解析。
2. `/api/map/osm-layers?site_id=PKU` 返回三类本地图层和统计。
3. Leaflet 可切换 OSM roads / buildings / water_landuse 图层。
4. 项目 route overlay 仍在最上层。
5. `simple_svg` fallback 保持可用。
6. OSM 数据来源、license、抽取日期和替换方式已有文档记录。

本阶段完成时已验证：

1. `py -m pytest`：106 passed。
2. API smoke check：`/api/bootstrap`、`/api/map/geojson?site_id=PKU`、`/api/map/osm-layers?site_id=PKU`、`/api/route`、`/api/route/multi` 均成功。
3. `/api/map/osm-layers?site_id=PKU` 返回 roads 505、buildings 353、water_landuse 74。
4. Playwright 浏览器检查确认 Leaflet、本地 OSM 图层开关、无底图模式、单目标路线高亮和 `simple_svg` fallback 可用；OSM roads 图层可从 3 层开启切到 2 层开启，再切回 3 层开启。
