# memberC 第13周工作内容陈述

> 角色：Member C（数据、检索、压缩、测试与文档负责人）
> 周期：2026-05-25 至 2026-05-31
> 阶段定位：正式产品冻结周，负责课程核验口径维持、文档冻结对齐、AIGC 素材落地和冻结版证据链闭环

---

## 1. 本周任务目标

第十三周是项目"正式产品冻结周"。Member C 的核心目标不是继续扩功能或补数据，而是把第十二周已建立的数据底座、课程核验证据链和文档体系冻结为正式交付版本，确保：

1. 课程硬指标回归口径不回退，快照数字与文档材料一致。
2. 冻结版文档（用户使用说明、评价和改进意见、AI 能力分析、课程覆盖清单）口径统一到第13周正式产品边界。
3. AIGC 轻量预览补齐真实可见媒体素材，从"placeholder"升级为"ready"状态。
4. 回归入口和验证命令说明收口，为第14周后的验收和彩排提供稳定基准。

---

## 2. 本周完成事项

### 2.1 课程核验口径维持

1. 继续维护 `tests/test_course_requirements.py`，本周未做破坏性修改，仅确认核验脚本在冻结版代码上仍稳定通过。
2. 保持第十二周已锁定的规模快照不变：
   - `users=70`
   - `diary_authors=70`
   - `extension_objects=208`
   - `mapped_extension_objects=5`
   - `pku_nodes=1565`
   - `pku_edges=3550`
   - `white_road_nodes=868`
   - `poi_access_nodes=111`
   - `facility_like_nodes=1397`
3. 本周未引入新的统计口径，也未调整强断言阈值，核验输出与第十二周书面记录一致。

### 2.2 AIGC 素材落地

1. 使用 AI 视频模型生成 3 段校园导览动画素材：
   - `北大秋日.mp4`：秋日燕园银杏、未名湖、图书馆广场校园漫游（1280×720, 24fps, 10s）
   - `北大食堂.mp4`：农园食堂窗口到餐盘特写的校园美食推荐（1280×720, 24fps, 10s）
   - `北大图书馆.mp4`：图书馆入口、阅览室到自习场景的学习攻略（1280×720, 24fps, 10s）
2. 将视频转换为 GIF 分镜预览（400×225, 3fps, 全局128色调色板）和首帧 JPG 截图，放置到 `src/ui/static/assets/aigc/` 和 `src/ui/static/assets/` 目录。
3. 更新 `data/aigc_media_samples.json`，将 `image_placeholder` 和 `preview_placeholder` 路径指向实际静态资源（`/assets/xxx.jpg` 和 `/assets/aigc/xxx.gif`），状态从 `placeholder_ready` 升级为 `ready`。
4. 配合 Member B 更新前端渲染逻辑，使 AIGC 预览区域展示真实 GIF 动画和 JPG 占位图，而非纯文字路径。
5. 更新 `demo_service.py` 中 AIGC 预览的 `prototype_notice` 措辞，从"不调用真实 AIGC 模型"改为"AIGC 模板化预览：基于用户描述生成校园导览分镜动画，GIF 由 AI 视频模型生成"。

### 2.3 文档冻结对齐

1. 复核 `docs/用户使用说明.md`，确认当前版本与第13周正式产品边界一致，无过期阶段表述。
2. 复核 `docs/评价和改进意见.md`，确认改进意见与当前冻结版功能集匹配。
3. 复核 `docs/AI辅助开发能力分析.md`，确认 AI 使用说明与当前开发流程一致。
4. 复核 `docs/课程要求覆盖清单.md`，确认 AIGC 条目已更新为"提供真实可见的轻量输出"状态。
5. 确认 `docs/数据字典.md` 和根目录 `数据字典.md` 的课程核验快照与本周核验输出一致。

### 2.4 回归验证与证据收口

1. 本周执行冻结版最小回归集合，确认主链路无回退。
2. 记录冻结版验证命令和结果，为第14周边界验收提供统一口径。
3. 确认浏览器验收前端口检查流程（`netstat -ano | findstr :8765`）已纳入帮助说明和周报材料。

---

## 3. 涉及文件

| 操作 | 文件 | 说明 |
|------|------|------|
| 更新 | `data/aigc_media_samples.json` | 路径指向实际静态资源，状态改为 ready |
| 新增 | `src/ui/static/assets/aigc/aigc_sample_001_storyboard.gif` | 秋日燕园分镜 GIF |
| 新增 | `src/ui/static/assets/aigc/aigc_sample_002_storyboard.gif` | 食堂美食分镜 GIF |
| 新增 | `src/ui/static/assets/aigc/aigc_sample_003_storyboard.gif` | 图书馆攻略分镜 GIF |
| 新增 | `src/ui/static/assets/pku_autumn_yanyuan.jpg` | 燕园秋景首帧截图 |
| 新增 | `src/ui/static/assets/pku_canteen_food.jpg` | 食堂美食首帧截图 |
| 新增 | `src/ui/static/assets/pku_library_study.jpg` | 图书馆学习首帧截图 |
| 协同更新 | `src/ui/static/app.js` | 媒体占位和 AIGC 预览区域渲染真实图片/GIF |
| 协同更新 | `src/ui/demo_service.py` | AIGC 预览 prototype_notice 措辞更新 |
| 复核 | `docs/课程要求覆盖清单.md` | 确认 AIGC 条目状态已对齐 |
| 复核 | `docs/用户使用说明.md` | 确认无过期表述 |
| 复核 | `docs/评价和改进意见.md` | 确认与冻结版功能一致 |
| 复核 | `docs/AI辅助开发能力分析.md` | 确认与开发流程一致 |
| 复核 | `docs/数据字典.md` | 确认快照数字一致 |
| 维护 | `tests/test_course_requirements.py` | 确认核验口径不回退 |

---

## 4. 测试命令与结果

本周执行的冻结版最小回归集合：

```powershell
node --check src/ui/static/app.js
python -B tests/test_course_requirements.py
python -B tests/test_integration.py
python -B tests/test_ui_demo.py
```

验证结论：

| 命令 | 结果 | 说明 |
|------|------|------|
| `node --check src/ui/static/app.js` | 通过 | 前端脚本语法检查稳定 |
| `python -B tests/test_course_requirements.py` | 通过 | 课程硬指标与文档核验稳定 |
| `python -B tests/test_integration.py` | 通过 | 查询/推荐/日记/检索/压缩/路径联调主链路稳定 |
| `python -B tests/test_ui_demo.py` | 通过 | Web 主入口和演示链路回归稳定 |

统一入口 `python -m pytest` 当前环境仍提示 `No module named pytest`，属于本机 Python 环境缺少 pytest 模块，非本周代码改动引起。冻结版继续采用上述分脚本最小回归集合。

浏览器验收前统一端口检查：

```powershell
netstat -ano | findstr :8765
```

---

## 5. 当前判断

1. 以 Member C 负责范围来看，第13周已实现课程核验口径的完全冻结：快照数字、测试输出、课程覆盖清单和周报材料保持一致。
2. AIGC 模块从"placeholder_ready"升级为"ready"状态，具备真实可见的 GIF 动画和 JPG 占位图输出，满足课程要求中"有真实输出，不是纯文档说明"的验收门槛。
3. 文档体系已对齐第13周正式产品边界：用户使用说明、评价和改进意见、AI 能力分析和课程覆盖清单均无过期表述。
4. 扩展对象口径维持稳定：`mapped_extension_objects=5`，对外表述为"PKU 深度导航 + 扩展推荐/查询对象池"，不承诺全量深度导航。

---

## 6. 冻结周边界声明

本周不承诺且不执行以下事项：

1. 不继续扩大扩展对象的深度导航映射数量。
2. 不引入新的数据统计口径或调整已有强断言。
3. 不对测试脚本做破坏性修改（只允许追加检查项）。
4. 不在文档中扩大 AIGC 的能力描述——当前明确为"模板化预览，GIF 由 AI 视频模型生成"。

---

## 7. 第14-15周计划

1. 配合 Member A / B 完成答辩彩排和演示链路确认。
2. 根据答疑反馈微调文档措辞（不改变口径，仅润色）。
3. 整理最终验收材料打包结构，包括代码包、测试记录、文档和截图。
4. 配合完成课程设计报告和答辩 PPT 的数据口径校对。
