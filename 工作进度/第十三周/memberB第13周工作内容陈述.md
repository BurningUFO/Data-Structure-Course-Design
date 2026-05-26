# memberB 第13周工作内容陈述

> 成员：Member B（业务交互、Web 主入口与产品体验）
> 周次：第13周（2026-05-25 至 2026-05-31）
> 阶段：正式产品冻结周

---

## 1. 本周目标

本周的核心目标不是扩功能，而是把第12周已经接入 Web 主入口的查询、推荐、路线、日记和 AIGC 入口冻结为正式产品版本，确保页面结构稳定、文案统一、帮助口径一致，并为第14周后的体验微调留出可控边界。

---

## 2. 本周完成事项

1. 继续维护 Web 主入口冻结口径，固定顶部导航、操作区、地图区、结果区和帮助入口的展示方式。
2. 保持综合查询、导航规划、场所与美食、日记中心和帮助与演示五条主入口链路可直接进入。
3. 收口 AIGC 轻量预览文案，将“第十二周继续增强”的旧表述改为第十三周冻结版口径。
4. 将帮助说明、演示链路和冻结版边界统一到当前 Web 主入口中，减少调试型提示对验收的干扰。
5. 配合冻结周要求，补齐第十三周成员 B 材料，确保周报可以直接汇总。

---

## 3. Web 主入口冻结情况

当前顶层主入口已冻结为以下五项：

1. 综合查询
2. 导航规划
3. 场所与美食
4. 日记中心
5. 帮助与演示

其中，AIGC 轻量预览保留为“帮助与演示”下的二级演示入口，不再作为顶层导航项。AIGC 当前仍是模板化预览，不调用真实生成模型；日记管理仍采用 `memory_only` 轻量演示口径。

---

## 4. 本周验证口径

本周已执行冻结周最小回归集合：

```powershell
node --check src/ui/static/app.js
python -B tests/test_routing.py
python -B tests/test_integration.py
python -B tests/test_course_requirements.py
python -B tests/test_ui_demo.py
```

验证结果：

- `node --check src/ui/static/app.js` 通过。
- `python -B tests/test_routing.py` 通过，83 项路由测试通过。
- `python -B tests/test_integration.py` 通过，19 项集成测试通过。
- `python -B tests/test_course_requirements.py` 通过，课程规模和文档核验通过。
- `python -B tests/test_ui_demo.py` 通过，Web 主入口和演示链路测试通过。
- `python -m pytest -q` 在当前本机 `Python313` 环境失败，原因为未安装 `pytest`；`py -3 -m pytest -q` 在当前终端提示未找到已安装 Python。因此本次冻结证据继续采用上述脚本化最小回归集合。

帮助页面与用户说明已对齐第13周冻结版口径，避免出现“第十二周继续增强”这类过期表述。

---

## 5. 完成判定

成员 B 第13周当前达到阶段性可提交状态：

- Web 主入口已保持正式产品入口形态。
- 关键演示链路仍可重复运行。
- AIGC、帮助说明和页面文案已按第13周冻结周收口。
- 第13周工作内容陈述已补齐。
