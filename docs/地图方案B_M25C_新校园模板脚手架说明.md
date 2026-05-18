# 地图方案 B M25C 新校园模板脚手架说明

## 范围

本文只记录 M25C 产物：`scripts/scaffold_new_campus.py`。该脚本把 M25A/M25B 中沉淀出的 PKU 兼容契约转成可复用的新校园脚手架。

本阶段不创建任何具体真实校园数据，不修改 `data/global_sites.json`，不进入 M25D、M26 或后续阶段。

## 脚本用途

脚本可在指定 `data_root` 下生成：

1. `sites/<SITE_ID>/outdoor.json` 初始室外图结构。
2. `sites/<SITE_ID>/geo/` 下的空 GeoJSON / OSM 匹配占位文件。
3. `geo/indoor_building_registry.json` 与 `geo/indoor_template_catalog.json`。
4. 可选的单建筑 `indoor_*.json` 室内模板占位。
5. `global_sites_entry.json`，供后续阶段人工合并到 `data/global_sites.json`。

脚本默认拒绝覆盖已有文件；只有显式传入 `--overwrite` 才会覆盖。

## dry-run 示例

```powershell
py scripts/scaffold_new_campus.py `
  --site-id TEMPLATE `
  --site-name "Template Campus" `
  --location "Replace with city or address" `
  --center-lat 0 `
  --center-lng 0 `
  --data-root .codex_tmp/m25c-data `
  --with-indoor-placeholder `
  --dry-run
```

## 后续使用口径

后续 M26/M27 单校扩展时，应先用真实 `SITE_ID`、站点名和已核验中心坐标生成脚手架，再替换节点名称、坐标、边距离、POI 文案和室内入口映射。

生成的 `global_sites_entry.json` 只是合并片段；只有在 `outdoor.json` 已具备可加载、可查询、可路由的最小数据后，才应并入 `data/global_sites.json`。
