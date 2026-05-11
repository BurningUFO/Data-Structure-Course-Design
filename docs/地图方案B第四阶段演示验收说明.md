# 地图方案 B 第四阶段演示验收说明

## 阶段定位

M4 当前按演示收尾处理，只做视觉包装、演示可控性和验收说明，不继续扩大真实道路数据、图结构语义或路由算法改动。

本阶段保留既有能力：

1. `leaflet_geo` 作为默认地图实验层。
2. `simple_svg` 作为可现场切换的稳定 fallback。
3. `/api/map/geojson?site_id=PKU` 输出当前室外图节点和边。
4. `/api/route` 与 `/api/route/multi` 继续返回 `route_geojson` 和 `route_geometry_stats` 供前端高亮。

## 启动与查看

在仓库根目录启动本地演示服务：

```powershell
py -B -m src.ui.demo_server
```

浏览器访问：

```text
http://127.0.0.1:8765
```

如果当前环境没有 `py` 启动器，可用同一 Python 环境执行：

```powershell
python -B -m src.ui.demo_server
```

## 演示控制

主界面地图区新增固定控制：

1. `Leaflet` / `SVG` 双渲染器切换，用于展示实验层和稳定简图对比。
2. `演示单目标`，固定从北大西门到图书馆，展示单目标路线高亮。
3. `演示多目标`，固定从北大西门访问图书馆和食堂并返回起点，展示多段路线高亮。
4. `清空路线`，保留当前渲染器，只重置路线状态。

地图区状态条展示：

1. 当前渲染器。
2. GeoJSON 节点、道路和 geometry 覆盖统计。
3. 当前路线的贴路段数、总室外段数和 fallback 段数。

地图图例解释：

1. 普通道路：低权重底层道路，避免抢当前路线。
2. 当前路线：双层高亮线，外层半透明描边、内层亮色路径。
3. 节点高亮：起点、终点、访问点或当前定位节点。
4. fallback 直线段：道路 geometry 未覆盖时用 from/to 节点坐标直连，数量会在状态条、caption 或路线摘要中说明。

geometry 覆盖率含义：

1. GeoJSON 道路覆盖率 = 带真实 `geometry` 的道路数 / 可渲染道路数。
2. 路线覆盖率 = 当前路线中使用真实 geometry 的室外段数 / 当前路线室外段总数。
3. fallback 段不是算法失败，只表示该边暂未补充道路折线，前端用直线兜底保证演示链路不断。

## 验收口径

现场验收时按以下顺序确认：

1. 打开首页并进入主要网站，默认地图为 Leaflet GeoJSON 实验层。
2. 点击 `SVG`，确认能切到原稳定简图；再点击 `Leaflet`，确认能切回实验层。
3. 点击 `演示单目标`，确认路径摘要、步骤列表和地图高亮同步更新。
4. 点击 `演示多目标`，确认多段路线、高亮和访问顺序同步更新。
5. 打开帮助说明，确认能解释 GeoJSON 坐标顺序为 `[lng, lat]`。
6. 说明 fallback 策略：Leaflet 或 GeoJSON 加载失败时回到 `simple_svg`，缺失 edge geometry 时用 from/to 直线段兜底。

## 当前限制

方案 B 当前是课程演示用的准真实地图实验层，不是完整商业地图：

1. 不接入 OSMnx、Overpass 或在线商业地图服务。
2. 不保证每条校园道路都有完整 geometry；未覆盖道路继续 fallback。
3. 不改变路径算法和图加载语义，路线仍由现有图结构计算。
4. `simple_svg` 保留为安全回退，Leaflet 资源或 GeoJSON 请求异常时前端会自动切回 SVG 简图。

## 不变约束

本阶段不修改：

1. `data/sites/PKU/outdoor.json` 的道路数据。
2. `src/routing/router.py` 的路径算法。
3. `src/graph/graph.py` 和 `src/graph/loader.py` 的图结构语义。
4. 搜索、推荐、日记、AIGC 的业务逻辑。

## 建议验证命令

```powershell
py -m pytest tests/test_ui_demo.py
py -m pytest
```
