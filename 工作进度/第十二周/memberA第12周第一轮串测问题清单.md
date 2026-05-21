# memberA 第12周第一轮串测问题清单

> 记录时间：2026-05-21
> 记录人：Member A（图结构与路径规划负责人 / 第 12 周协作统筹）
> 范围：第 12 周第一轮主链路串测与验证问题跟踪

---

## 1. 串测范围

本轮串测重点覆盖以下四条主线：

1. 路径规划主线：`python -B tests\test_routing.py`
2. 联调主线：`python -B tests\test_integration.py`
3. 课程硬指标核验主线：`python -B tests\test_course_requirements.py`
4. Web 主入口主线：`python -B tests\test_ui_demo.py`

---

## 2. 当前结论

截至 2026-05-21，本轮串测未发现新的 P0 / P1 级功能阻塞；路径接口、Web 主入口、课程硬指标核验和统一演示链路均可运行。

当前仍需跟踪的问题主要集中在“验证入口环境”与“主入口静态断言同步”两类，详见下表。

---

## 3. 问题清单

| 编号 | 级别 | 问题描述 | 影响范围 | 当前状态 | 负责人 |
|------|------|----------|----------|----------|--------|
| M12-01 | P2 | `tests/test_ui_demo.py` 中旧版静态断言仍引用已收起的地图调试控件与图例文案，导致 UI 回归最初失败。 | 阻塞 UI 回归验证，但不影响运行时功能。 | 已关闭：已同步测试断言到当前主入口 UI。 | Member A / B |
| M12-02 | P2 | 优先验证命令 `python -m pytest` 当前不可用，报错 `No module named pytest`。 | 无法使用单命令跑全量 pytest，需要继续依赖分测试脚本。 | 未关闭：属本机环境问题，不是当前代码回归。 | 本地环境 / Member C 协助 |

---

## 4. 已关闭问题说明

### M12-01 UI 静态断言与当前主入口不一致

现象：

- 地图区已收起旧版渲染器切换控件、调试面板和补充图例；
- 旧测试仍断言 `map-renderer-controls`、`高级地图调试选项`、`补充图例` 等静态内容存在；
- 导致 `python -B tests\test_ui_demo.py` 初次执行失败。

处理：

1. 将静态断言同步到当前 UI 收口后的实际结构；
2. 保留对 Leaflet 本地资源、地图快捷操作、室内导航入口、多目标路径入口和 AIGC 入口的有效断言；
3. 重新执行 `python -B tests\test_ui_demo.py`，确认全部通过。

结论：

这是验证脚本与当前主入口结构不同步的问题，不是路径接口或运行时功能退化。

---

## 5. 未关闭问题说明

### M12-02 `pytest` 环境缺失

失败命令：

```powershell
python -m pytest
```

失败原因：

- 当前 Python 解释器环境缺少 `pytest` 模块；
- 报错为：`No module named pytest`。

与当前改动的关系：

- 无直接关系；
- 属于本地验证环境缺项，不是本次第 12 周路径、UI 或文档改动引入的问题。

当前最安全替代动作：

1. 继续使用以下已验证通过的脚本作为收口入口：
   - `python -B tests\test_routing.py`
   - `python -B tests\test_integration.py`
   - `python -B tests\test_course_requirements.py`
   - `python -B tests\test_ui_demo.py`
2. 如需恢复统一 `pytest` 入口，由本地环境补装 `pytest` 后再执行。

---

## 6. 下一步跟踪

1. 若 Member B 后续继续调整主入口 UI，需要同步更新 `tests/test_ui_demo.py` 的静态结构断言，避免再次出现“页面已收口、测试仍停留旧结构”的问题。
2. 若后续需要周末全量验收截图或统一 CI 入口，需优先解决 `pytest` 模块缺失问题。
3. 若第 12 周后半程新增路径字段需求，仍按“仅追加字段、不改语义”的冻结规则处理，避免引入新的联调回退。
