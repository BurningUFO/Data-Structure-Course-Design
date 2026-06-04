# memberC 第13周冻结版课程核验与回归记录

> 核验补记日期：2026-06-04  
> 冻结周范围：2026-05-25 至 2026-05-31  
> 角色：Member C（数据、检索、压缩、测试与文档负责人）  
> 主题：第 13 周冻结版课程核验与回归记录

---

## 1. 文档目的

本文档用于补齐第 13 周正式产品冻结版的课程核验书面证据，和《课程要求覆盖清单》《数据字典》《评价和改进意见》以及第 11-13 周周材料保持同一口径。记录范围以当前仓库实际可核验结果为准，不把历史最低达标快照误写为当前系统规模，也不扩大 AIGC、日记管理和扩展对象导航的能力承诺。

本次补记前，`tests/test_course_requirements.py` 已将本文档列为第 13 周冻结证据链的必备文件。补记前执行 `python3 tests/test_course_requirements.py` 时，用户样例与 AIGC 样例检查已通过，但文档存在性检查因缺少本文档失败。因此本记录的直接目标是消除缺失文档问题，并保留本次实际复核到的冻结版数据和测试结果。

---

## 2. 本周冻结版范围说明

第 13 周冻结版定位为正式产品冻结周，后续第 14-15 周只做体验优化、验收材料润色和反馈收口，不再新增课程硬功能或推翻接口结构。本记录采用以下边界：

1. Web 主入口、综合查询、导航规划、场所与美食、日记中心、AIGC 预览和帮助说明保持冻结版结构。
2. 路线规划仍以当前 PKU 深度导航图为运行时权威图，支持单目标、多目标、跨层室内外衔接和交通方式策略。
3. 扩展推荐 / 查询对象池用于满足 `200+` 景区 / 校园 / 推荐对象规模口径，其中仅部分对象映射到 PKU 路由节点，不承诺 208 个扩展对象全部支持深度导航。
4. 日记新增、编辑、评分、删除为轻量演示口径；当前测试确认 CRUD 主流程可用，但不把它描述为完整生产级持久化系统。
5. AIGC 能力采用模板化 / 样例化预览口径，当前已有 JPG 首帧和 GIF 分镜静态资源；实时生成在无密钥或失败时按模板预览回退，不描述为稳定外部模型服务。

---

## 3. 课程硬指标核验结果

| 课程指标 | 当前仓库可验证结果 | 结论 | 口径说明 |
|----------|--------------------|------|----------|
| 系统用户数 `>=10` | `data/users.json` 共 `70` 个用户 | 达标 | 本次由脚本直接统计；日记作者 `author_id` 均属于用户集合 |
| 日记作者数 `>=10` | `data/diary_data.json` 独立作者 `70` 个 | 达标 | 日记总数为 `132`，具备多用户浏览 / 推荐样例 |
| 景区与校园数量 `>=200` | `data/成员Cdata/scenic_spots.json` 扩展对象 `208` 条 | 达标 | 当前采用“1 个深度导航核心站点 PKU + 200+ 扩展推荐 / 查询对象池”口径 |
| 扩展对象可路由映射 | `mapped_extension_objects=5` | 可演示但有限 | 仅作为推荐对象进入路径规划的稳定桥接样例，不扩大为全量导航承诺 |
| 建筑物 / 室内导航 | `indoor_building_registry.json` 登记 `20` 栋建筑，`indoor_*.json` 文件 `20` 份 | 达标 | 注册表对应室内图文件无缺失 |
| 服务设施种类 | PKU 节点分类 `16` 类 | 达标 | 覆盖餐饮、购物、运动、洗手间、停车、服务、宿舍、教学、地标、道路等类别 |
| 服务设施数量 | 服务设施口径节点 `1397` 个 | 达标 | 按 `tests/test_course_requirements.py` 的 `SERVICE_CATEGORY_SET` 口径统计 |
| 道路图边数 `>=200` | PKU 分层图边 `3550` 条 | 达标 | 第 11 周 `200` 边为历史最低基准，当前以全量快照为准 |
| PKU 节点规模 | PKU 分层图节点 `1565` 个 | 达标 | 当前冻结版数据字典和覆盖清单均采用该快照 |
| 媒体占位 | 带图片日记 `4` 篇 | 达标 | `tests/test_course_requirements.py` 补文档前已确认该项通过 |
| AIGC 样例 | `data/aigc_media_samples.json` 共 `3` 条，状态均为 `ready` | 达标 | JPG / GIF 静态资源均实际存在，无缺失路径 |

---

## 4. 已执行的测试 / 回归清单

| 命令 | 本次结果 | 覆盖说明 |
|------|----------|----------|
| `python3 tests/test_course_requirements.py`（补文档前） | 失败 | 失败原因为缺少 `工作进度/第十三周/memberC第13周冻结版课程核验与回归记录.md`；在失败前已输出 `users=70`、`diary_authors=70`、`samples=3`、`media_diaries=4` |
| `python3 tests/test_routing.py` | 通过 | `83` 个路径规划单元测试通过，覆盖单目标、多目标、策略和异常输入 |
| `python3 tests/test_search.py` | 通过 | 检索、类别过滤、模糊查询、真实路径距离排序和场所查询主链路通过 |
| `python3 tests/test_recommend.py` | 通过 | 热度、评分、Top-K、距离、美食过滤和兴趣推荐排序通过 |
| `python3 tests/test_diary.py` | 通过 | 日记加载、标题 / 目的地查询、排序、兴趣推荐、CRUD 演示和全文入口通过 |
| `python3 tests/test_fulltext.py` | 通过 | 全文索引构建、单关键词 / 多关键词 / 别名检索和离线索引 round-trip 通过 |
| `python3 tests/test_compress.py` | 通过 | 哈夫曼频率表、编码表、压缩 / 解压和单字符 round-trip 通过 |
| `python3 tests/test_ui_demo.py` | 通过 | Web Demo 服务、Bootstrap、Leaflet / GeoJSON、室内图、路线联动、日记和 AIGC 入口回归通过 |
| `python3 tests/test_integration.py` | 通过 | `19` 项集成链路通过，`0` 失败；覆盖查询到路线、日记到路线、全文检索到路线和压缩解压一致性 |
| `python3 tests/test_course_requirements.py`（本文档落盘后） | 通过 | 必要文档检查通过，输出 `docs=13`；同时复核 `pku_nodes=1565`、`pku_edges=3550`、`local_osm_road_features=505`、`extension_objects=208` |
| `python3 -m pytest -q` | 未能启动 | 当前环境提示 `No module named pytest`，因此本记录采用已实际通过的拆分脚本作为回归证据 |

---

## 5. 关键统计快照

| 项目 | 当前值 |
|------|--------|
| `users` | `70` |
| `diary_authors` | `70` |
| `diaries` | `132` |
| `media_diaries` | `4` |
| `aigc_samples` | `3` |
| `aigc_status_counts` | `{"ready": 3}` |
| `aigc_asset_missing` | `[]` |
| `extension_objects` | `208` |
| `mapped_extension_objects` | `5` |
| `pku_nodes` | `1565` |
| `pku_edges` | `3550` |
| `pku_categories` | `16` |
| `facility_like_nodes` | `1397` |
| `outdoor_nodes` | `1090` |
| `outdoor_edges` | `2556` |
| `white_road_nodes` | `868` |
| `poi_access_nodes` | `111` |
| `local_osm_road_features` | `505` |
| `indoor_registry_buildings` | `20` |
| `indoor_json_files` | `20` |

说明：

1. 如第 11 周记录中的 `58` 节点、`200` 边与当前快照不同，应按历史最低达标基准理解；第 13 周冻结版材料统一采用当前可验证的 `1565` 节点、`3550` 边口径。
2. 当前本地 OSM 简化路要素实际统计为 `505`，该项不作为课程硬指标核心数字；课程硬指标仍以 PKU 运行时图节点、边和设施口径为准。
3. AIGC 样例当前为 `ready` 状态，且静态资源路径均存在；周报中旧的 `placeholder_ready` 表述应视为阶段口径残留，正式冻结材料按当前文件状态写为 `ready`。

---

## 6. 主链路测试对应关系

| 主链路 | 对应测试 / 证据 |
|--------|-----------------|
| Web UI 主入口与 Bootstrap | `tests/test_ui_demo.py` 中 Bootstrap、静态入口、导航控件和状态重置相关用例 |
| 地图与路线展示 | `tests/test_ui_demo.py` 的 Leaflet / GeoJSON、室内图、路线叠加用例；`tests/test_routing.py` 的路径算法用例 |
| 单目标 / 多目标路线 | `tests/test_routing.py`、`tests/test_integration.py`、`tests/test_ui_demo.py` |
| 场所检索和附近设施 | `tests/test_search.py`、`tests/test_ui_demo.py` |
| 景点 / 美食推荐 | `tests/test_recommend.py`、`tests/test_ui_demo.py` |
| 日记浏览、目的地查询和管理 | `tests/test_diary.py`、`tests/test_integration.py`、`tests/test_ui_demo.py` |
| 全文检索 | `tests/test_fulltext.py`、`tests/test_diary.py`、`tests/test_integration.py` |
| 压缩 / 解压 | `tests/test_compress.py`、`tests/test_integration.py` |
| AIGC 轻量预览 | `tests/test_course_requirements.py`、`tests/test_ui_demo.py`、`data/aigc_media_samples.json` |

---

## 7. 主要问题与风险

1. **扩展对象映射范围有限**：`extension_objects=208` 已满足课程规模口径，但 `mapped_extension_objects=5` 说明多数对象仍用于推荐 / 查询规模，不应在验收讲解中表述为“208 个对象全部支持深度导航”。
2. **AIGC 是轻量预览能力**：当前样例资源真实存在且状态为 `ready`，但能力边界仍是模板化 / 样例化预览；实时生成路径在无密钥或异常时会回退，不应描述为稳定生产级生成服务。
3. **日记管理为演示口径**：日记 CRUD、评分、排序和全文检索测试已通过，但当前文档和页面仍应保持轻量演示说明，避免把 `memory_only` 入口包装成完整持久化平台。
4. **测试入口口径需统一**：本次在 macOS 环境使用 `python3` 执行拆分脚本；历史周报中出现的 `py -3` 是 Windows 推荐入口。后续验收材料应按实际运行环境标注命令，避免混用造成误解。
5. **历史数字不能继续当作当前快照**：第 11 周的 10 用户、53 服务设施、200 边等数字是最低达标阶段记录；第 13 周冻结版应统一写当前全量快照。

---

## 8. 冻结结论与后续建议

从 Member C 负责范围看，第 13 周冻结版的课程硬指标、数据规模、日记 / 检索 / 压缩 / AIGC 轻量样例和 Web 主链路均已有对应数据或测试证据。本文档补齐后已复跑 `python3 tests/test_course_requirements.py`，课程核验脚本中的“第 13 周冻结版书面记录缺失”问题已经消除。

后续建议：

1. 第 14-15 周仅做体验优化、答辩材料润色和演示预设稳定，不再扩大功能承诺。
2. 答辩时统一采用“PKU 深度导航核心站点 + 200+ 扩展推荐 / 查询对象池”的数据规模说明。
3. AIGC 和日记管理继续使用轻量演示边界说明，强调当前已有可见样例和测试覆盖，但不承诺生产级媒体管理或外部模型服务。
4. 每次验收前优先执行 `python3 tests/test_course_requirements.py` 和主链路拆分脚本；本次 `python3 -m pytest -q` 因当前解释器缺少 `pytest` 未能启动，如后续恢复全量入口，需单独记录环境与结果。
