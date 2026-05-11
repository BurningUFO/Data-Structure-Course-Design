# 地图方案 B 第一阶段 Agent 任务说明

## 任务目标

只实现地图方案 B 的第一阶段：Leaflet + GeoJSON 轻量接入。

本阶段目标不是完成真实路网抽取，也不是补齐道路 `geometry`，而是先打通稳定的双渲染器架构：

1. 当前 SVG 地图继续可用。
2. 新增 Leaflet 地图渲染器。
3. 后端能把现有室外节点和边输出为 GeoJSON。
4. 前端能用 GeoJSON 在 Leaflet 上显示节点和道路。
5. Leaflet 失败时自动回退到原 SVG 地图。

## 明确范围

本阶段允许修改：

1. `src/ui/demo_service.py`
2. `src/ui/demo_server.py`
3. `src/ui/static/index.html`
4. `src/ui/static/app.js`
5. `src/ui/static/styles.css`
6. 必要的测试文件
7. 必要的文档说明

本阶段不应修改：

1. `src/routing/router.py` 的核心路径算法
2. `src/graph/graph.py` 和 `src/graph/loader.py` 的图结构语义
3. 搜索、推荐、日记、压缩模块的业务逻辑
4. `data/sites/PKU/outdoor.json` 的真实数据内容，除非只是补充无行为影响的字段说明

## 不允许破坏的稳定链路

以下接口和功能必须保持兼容：

1. `GET /api/bootstrap`
2. `POST /api/search/scenic`
3. `POST /api/search/places`
4. `POST /api/recommend/catering`
5. `POST /api/diaries/fulltext`
6. `POST /api/route`
7. `POST /api/route/multi`
8. 原 SVG 地图显示与路径高亮
9. 查询结果中的“地图定位”和“从当前起点规划路线”
10. 站点切换后的状态重置

如果新增字段，应只做向后兼容扩展，不能删除旧字段或改变旧字段含义。

## 后端要求

### Bootstrap 扩展

在 `/api/bootstrap` 返回中增加地图能力声明，建议结构：

```json
{
  "map_renderer": "simple_svg",
  "map_capabilities": {
    "renderers": ["simple_svg", "leaflet_geo"],
    "default_renderer": "simple_svg",
    "geojson_endpoint": "/api/map/geojson",
    "fallback_renderer": "simple_svg"
  }
}
```

要求：

1. 默认渲染器可以先保持 `simple_svg`，保证稳定。
2. 前端可以通过常量或 UI 开关切换到 `leaflet_geo`。
3. 不得移除原有 `map.nodes`、`map.edges`、`map.bounds` 等字段。

### 新增 GeoJSON 接口

新增：

```text
GET /api/map/geojson?site_id=PKU
```

返回：

```json
{
  "success": true,
  "site_id": "PKU",
  "geojson": {
    "type": "FeatureCollection",
    "features": []
  },
  "stats": {
    "node_feature_count": 0,
    "edge_feature_count": 0,
    "fallback_edge_count": 0
  }
}
```

Feature 规则：

1. 节点输出为 `Point`。
2. 边输出为 `LineString`。
3. GeoJSON 坐标必须为 `[lng, lat]`。
4. 当前阶段没有 edge `geometry` 时，用 `from/to` 节点坐标生成两点 LineString。
5. Feature properties 至少包含 `kind`，节点为 `node`，边为 `edge`。
6. 边 properties 至少包含 `from`、`to`、`name`、`edge_type`、`distance_m`。
7. 节点 properties 至少包含 `id`、`name`、`category`、`category_label`。

## 前端要求

### 资源引用

使用本地 Leaflet 资源：

```text
src/ui/static/vendor/leaflet/leaflet.css
src/ui/static/vendor/leaflet/leaflet.js
```

不要依赖 CDN 作为唯一运行来源。

### 渲染器结构

建议拆分：

```text
renderMap()
renderSvgMap()
renderLeafletMap()
ensureLeafletMap()
syncLeafletBaseLayers()
syncLeafletRouteLayer()
fallbackToSvgMap()
```

要求：

1. `renderMap()` 作为入口，根据当前渲染器选择 SVG 或 Leaflet。
2. SVG 逻辑必须保留，最好迁移到 `renderSvgMap()`。
3. Leaflet 初始化失败时调用 SVG fallback。
4. 切换站点、查询、清空路线、规划路线时，Leaflet 图层状态必须同步。
5. 当前阶段路线高亮可先复用现有 `mappable_path_node_ids` 生成 LineString，真实贴路留到第二阶段。

### UI 行为

最低要求：

1. Leaflet 地图可拖动、缩放。
2. 道路以线图层显示。
3. 节点以圆点或 marker 显示。
4. 节点点击可展示名称和类别。
5. 道路点击可展示名称和距离。
6. 地图 caption 能提示当前是“真实地图实验模式”或“SVG 简图模式”。
7. 若 GeoJSON 加载失败，显示错误提示并回退 SVG。

## 测试与验证

至少完成以下验证。

### 后端 smoke check

运行：

```powershell
python -B -m src.ui.demo_server
```

手动或脚本检查：

```text
GET http://127.0.0.1:8765/api/bootstrap
GET http://127.0.0.1:8765/api/map/geojson?site_id=PKU
POST http://127.0.0.1:8765/api/route
POST http://127.0.0.1:8765/api/route/multi
```

### 自动测试

如果项目测试可运行，执行：

```powershell
python -m pytest
```

如果完整测试受环境影响，至少新增或运行最小测试，覆盖：

1. `/api/map/geojson` 返回 `FeatureCollection`。
2. GeoJSON 坐标顺序是 `[lng, lat]`。
3. 节点和边 feature 数量大于 0。
4. 缺失 geometry 的边能 fallback 成两点 LineString。
5. `/api/bootstrap` 保留旧字段并增加新能力字段。

## 提交要求

第一阶段建议拆成两个 commit：

1. `feat: add map geojson endpoint`
2. `feat: add leaflet map renderer fallback`

如果代码量很小，也可以合并为：

```text
feat: add leaflet geojson map experiment
```

提交前必须确认：

1. `git status --short` 中没有误加入无关周报、脚本或临时文件。
2. `src/ui/static/vendor/leaflet/` 已经存在，不重复下载 Leaflet。
3. 原 SVG 地图仍可用。
4. 失败回退路径明确。

## 停止条件

如果出现以下情况，应停止继续扩大改动范围：

1. Leaflet 初始化导致原页面主功能不可用。
2. `/api/bootstrap` 兼容性被破坏。
3. 路线规划接口返回结构被改坏。
4. 需要大规模改动 `router.py` 或图结构才能继续。
5. 真实底图瓦片加载不稳定且没有 fallback。

出现停止条件时，优先保留后端 GeoJSON 接口和 SVG fallback，不继续接 OSMnx、Overpass 或真实道路 geometry。

