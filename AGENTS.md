# AGENTS.md

## Project Context

This repository is a data structure course design project for an intelligent campus/scenic-area guide system. The current experimental branch for map work is:

```text
experiment/map-plan-b
```

The map experiment is intentionally staged. Do not attempt the full real-road-map rewrite in one pass.

Primary implementation references:

```text
docs/地图方案B第一阶段Agent任务说明.md
docs/地图方案B真实地图层总路线计划.md
docs/references/map-plan-b/README.md
```

Local Leaflet runtime assets are already vendored here:

```text
src/ui/static/vendor/leaflet/
```

## Mandatory Startup Checks

Before modifying code, run:

```powershell
git status --short --branch
git branch --show-current
```

Expected branch:

```text
experiment/map-plan-b
```

If the branch is not `experiment/map-plan-b`, stop and report the mismatch before making changes.

## Dirty Worktree Rules

The worktree may contain unrelated untracked files, especially under:

```text
scripts/
工作进度/
```

Do not stage, commit, delete, move, or rewrite unrelated untracked files unless explicitly instructed.

When committing map-plan work, stage only files that are part of the current task.

## Map Plan B First-Stage Scope

The first-stage implementation scope is only:

1. Add a lightweight Leaflet + GeoJSON renderer.
2. Preserve the existing SVG map as `simple_svg` fallback.
3. Add `GET /api/map/geojson?site_id=PKU`.
4. Convert existing outdoor nodes and edges into a GeoJSON `FeatureCollection`.
5. Extend `/api/bootstrap` with `map_renderer` and `map_capabilities` without breaking old fields.
6. Load Leaflet from local vendored files, not as CDN-only dependencies.
7. Render current nodes and roads in Leaflet.
8. Fall back to SVG if Leaflet or GeoJSON loading fails.

Out of scope for first stage:

1. Do not use OSMnx.
2. Do not call Overpass.
3. Do not download or import real OSM road data.
4. Do not add real road `geometry` to `data/sites/PKU/outdoor.json`.
5. Do not rewrite routing algorithms.
6. Do not rewrite graph loader semantics.

## Stable Contracts

Do not break these endpoints or existing response fields:

```text
GET /api/bootstrap
POST /api/search/scenic
POST /api/search/places
POST /api/recommend/catering
POST /api/diaries/fulltext
POST /api/route
POST /api/route/multi
```

When extending responses, add fields only. Do not remove, rename, or change the meaning of existing fields.

## Expected Files for First-Stage Code Changes

Likely files:

```text
src/ui/demo_service.py
src/ui/demo_server.py
src/ui/static/index.html
src/ui/static/app.js
src/ui/static/styles.css
tests/
```

Avoid modifying unrelated modules.

## GeoJSON Requirements

GeoJSON output must use RFC 7946 coordinate order:

```text
[lng, lat]
```

Node features:

1. Geometry type: `Point`.
2. Properties must include `kind=node`, `id`, `name`, `category`, and `category_label`.

Edge features:

1. Geometry type: `LineString`.
2. Properties must include `kind=edge`, `from`, `to`, `name`, `edge_type`, and `distance_m`.
3. In the first stage, if no edge geometry exists, generate a two-point `LineString` from the source node and target node locations.

## Frontend Renderer Rules

Keep the map rendering entrypoint stable. Recommended structure:

```text
renderMap()
renderSvgMap()
renderLeafletMap()
ensureLeafletMap()
syncLeafletRouteLayer()
fallbackToSvgMap()
```

Requirements:

1. `renderMap()` should decide between `simple_svg` and `leaflet_geo`.
2. SVG behavior must remain available and usable.
3. Leaflet initialization failure must not break the page.
4. Existing route and focus state should continue to update the visible map.
5. Current-stage route highlighting may use existing `mappable_path_node_ids`; true edge-geometry route stitching is a later stage.

## Sub-Agent Policy

Sub-agents may be used only when explicitly allowed by the user in the session.

Recommended use:

1. Use explorer sub-agents for read-only analysis of current map rendering, API contracts, or test structure.
2. Use at most one worker for a very narrow and disjoint write scope, such as tests only.
3. The main agent should own integration changes across `demo_service.py`, `demo_server.py`, and frontend files.

Avoid:

1. Do not assign overlapping frontend files to multiple workers.
2. Do not let multiple workers edit the same files.
3. Do not outsource the critical integration path if the main agent depends on it immediately.

## Verification

Run the strongest feasible verification before final response.

Preferred:

```powershell
python -m pytest
```

At minimum, verify the UI server and key endpoints, including:

```text
GET /api/bootstrap
GET /api/map/geojson?site_id=PKU
POST /api/route
POST /api/route/multi
```

If a command cannot be run or fails, report:

1. The exact command.
2. The failure reason.
3. Whether the failure is related to the current changes.
4. The safest next action.

## Commit Guidance

Use focused commits. Suggested commit messages:

```text
feat: add map geojson endpoint
feat: add leaflet geojson map renderer
test: cover map geojson endpoint
```

For the whole first-stage implementation, this is acceptable if the change is cohesive:

```text
feat: add leaflet geojson map experiment
```

Before committing, run:

```powershell
git status --short
git diff --cached --name-status
```

Confirm no unrelated untracked files are staged.

## Stop Conditions

Stop and report instead of expanding the task if:

1. The branch is not `experiment/map-plan-b`.
2. Bootstrap compatibility breaks.
3. Existing SVG map cannot be restored.
4. Route endpoints require core algorithm rewrites.
5. Leaflet integration forces unrelated changes in search, recommend, diary, graph, or routing modules.

