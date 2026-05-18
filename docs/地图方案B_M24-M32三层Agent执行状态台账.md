# 地图方案 B M24-M32 三层 Agent 执行状态台账

## 使用规则

1. 本文件是三层协作中的唯一持久化执行台账。
2. 一级总管 agent 与二级经理 agent 都必须在每次阶段完成后更新本文件。
3. 三级原子执行 agent 不直接维护总表，但二级经理必须在其完成后立刻回填状态。
4. 状态只能使用：`pending`、`in_progress`、`blocked`、`completed`。
5. 若任务中断，恢复时必须先读取本文件，再从“第一个未完成项”继续。
6. 不允许跳过本文件直接凭上下文记忆继续执行。

## 全局摘要

- `top_manager_status`: `in_progress`
- `current_manager`: `L2-01`
- `last_completed_manager`: `none`
- `next_manager`: `L2-02`
- `last_commit`: `25a3ae3`
- `last_verification`: `py -m pytest -q`，138 passed
- `last_update_note`: `M24D 已完成，已完成脚手架兼容性自检，下一步 M25A`

## 二级经理状态总表

| Manager ID | 经理文档 | 状态 | 子任务完成数 | 最后 commit | 备注 |
| --- | --- | --- | --- | --- | --- |
| L2-01 | `docs/地图方案B_M24-M25基线模板经理Agent_Goal提示词.md` | `in_progress` | `4/8` | `25a3ae3` | M24D 已完成，下一步 M25A |
| L2-02 | `docs/地图方案B_M26-M27试点与首批室外经理Agent_Goal提示词.md` | `pending` | `0/10` | `none` | 试点校 + 首批 5 校室外 |
| L2-03 | `docs/地图方案B_M28全量室外扩展经理Agent_Goal提示词.md` | `pending` | `0/16` | `none` | 剩余 15 校室外 |
| L2-04 | `docs/地图方案B_M29首批室内经理Agent_Goal提示词.md` | `pending` | `0/6` | `none` | 首批 5 校室内 |
| L2-05 | `docs/地图方案B_M30全量室内扩展经理Agent_Goal提示词.md` | `pending` | `0/16` | `none` | 剩余 15 校室内 |
| L2-06 | `docs/地图方案B_M31A交通方式校准经理Agent_Goal提示词.md` | `pending` | `0/20` | `none` | 20 校交通方式 |
| L2-07 | `docs/地图方案B_M31B附近查询校准经理Agent_Goal提示词.md` | `pending` | `0/20` | `none` | 20 校查附近 |
| L2-08 | `docs/地图方案B_M31C兴趣推荐校准经理Agent_Goal提示词.md` | `pending` | `0/20` | `none` | 20 校兴趣推荐与文案 |
| L2-09 | `docs/地图方案B_M31D-M32总验收经理Agent_Goal提示词.md` | `pending` | `0/4` | `none` | M31D + M32A/B/C |

## 一级总管执行记录

- `status`: `in_progress`
- `completed_managers`:
- `current_action`: `L2-01 已完成 M24D`
- `next_action`: `继续执行 M25A`
- `notes`: `一级总管已完成启动检查，L2-01 当前完成 4/8。`

## L2-01 基线模板经理子任务

- [x] `M24A`
- [x] `M24B`
- [x] `M24C`
- [x] `M24D`
- [ ] `M25A`
- [ ] `M25B`
- [ ] `M25C`
- [ ] `M25D`

## L2-02 试点与首批室外经理子任务

- [ ] `M26A THU`
- [ ] `M26B THU`
- [ ] `M26C THU`
- [ ] `M26D THU`
- [ ] `M27X THU`
- [ ] `M27X WHU`
- [ ] `M27X XMU`
- [ ] `M27X ZJU`
- [ ] `M27X NJU`
- [ ] `M27Y`

## L2-03 全量室外扩展经理子任务

- [ ] `M28X FDU`
- [ ] `M28X SJTU`
- [ ] `M28X TONGJI`
- [ ] `M28X SEU`
- [ ] `M28X SYSU`
- [ ] `M28X SCU`
- [ ] `M28X HNU`
- [ ] `M28X SDU`
- [ ] `M28X HUST`
- [ ] `M28X SCUT`
- [ ] `M28X OUC`
- [ ] `M28X SUDA`
- [ ] `M28X HIT`
- [ ] `M28X YNU`
- [ ] `M28X HZAU`
- [ ] `M28Y`

## L2-04 首批室内经理子任务

- [ ] `M29X THU`
- [ ] `M29X WHU`
- [ ] `M29X XMU`
- [ ] `M29X ZJU`
- [ ] `M29X NJU`
- [ ] `M29Y`

## L2-05 全量室内扩展经理子任务

- [ ] `M30X FDU`
- [ ] `M30X SJTU`
- [ ] `M30X TONGJI`
- [ ] `M30X SEU`
- [ ] `M30X SYSU`
- [ ] `M30X SCU`
- [ ] `M30X HNU`
- [ ] `M30X SDU`
- [ ] `M30X HUST`
- [ ] `M30X SCUT`
- [ ] `M30X OUC`
- [ ] `M30X SUDA`
- [ ] `M30X HIT`
- [ ] `M30X YNU`
- [ ] `M30X HZAU`
- [ ] `M30Y`

## L2-06 交通方式校准经理子任务

- [ ] `M31A THU`
- [ ] `M31A WHU`
- [ ] `M31A XMU`
- [ ] `M31A ZJU`
- [ ] `M31A NJU`
- [ ] `M31A FDU`
- [ ] `M31A SJTU`
- [ ] `M31A TONGJI`
- [ ] `M31A SEU`
- [ ] `M31A SYSU`
- [ ] `M31A SCU`
- [ ] `M31A HNU`
- [ ] `M31A SDU`
- [ ] `M31A HUST`
- [ ] `M31A SCUT`
- [ ] `M31A OUC`
- [ ] `M31A SUDA`
- [ ] `M31A HIT`
- [ ] `M31A YNU`
- [ ] `M31A HZAU`

## L2-07 附近查询校准经理子任务

- [ ] `M31B THU`
- [ ] `M31B WHU`
- [ ] `M31B XMU`
- [ ] `M31B ZJU`
- [ ] `M31B NJU`
- [ ] `M31B FDU`
- [ ] `M31B SJTU`
- [ ] `M31B TONGJI`
- [ ] `M31B SEU`
- [ ] `M31B SYSU`
- [ ] `M31B SCU`
- [ ] `M31B HNU`
- [ ] `M31B SDU`
- [ ] `M31B HUST`
- [ ] `M31B SCUT`
- [ ] `M31B OUC`
- [ ] `M31B SUDA`
- [ ] `M31B HIT`
- [ ] `M31B YNU`
- [ ] `M31B HZAU`

## L2-08 兴趣推荐校准经理子任务

- [ ] `M31C THU`
- [ ] `M31C WHU`
- [ ] `M31C XMU`
- [ ] `M31C ZJU`
- [ ] `M31C NJU`
- [ ] `M31C FDU`
- [ ] `M31C SJTU`
- [ ] `M31C TONGJI`
- [ ] `M31C SEU`
- [ ] `M31C SYSU`
- [ ] `M31C SCU`
- [ ] `M31C HNU`
- [ ] `M31C SDU`
- [ ] `M31C HUST`
- [ ] `M31C SCUT`
- [ ] `M31C OUC`
- [ ] `M31C SUDA`
- [ ] `M31C HIT`
- [ ] `M31C YNU`
- [ ] `M31C HZAU`

## L2-09 总验收经理子任务

- [ ] `M31D`
- [ ] `M32A`
- [ ] `M32B`
- [ ] `M32C`

## 提交与验证日志

按时间倒序追加：

- [2026-05-18 18:00] manager=L2-01 child=M24D status=completed commit=25a3ae3 verify=`py -m pytest -q` 138 passed note=为 bootstrap 站点项增加可用性标记，前端禁用脚手架站点以保护 PKU 当前体验
- [2026-05-18 17:52] manager=L2-01 child=M24C status=completed commit=9aacd67 verify=`py -m pytest -q` 138 passed note=在 `data/global_sites.json` 新增 20 校占位注册，PKU 保持首位且测试通过
- [2026-05-18 17:45] manager=L2-01 child=M24B status=completed commit=304c765 verify=`py -m pytest -q` 138 passed note=创建 20 校 `data/sites/<SITE_ID>/geo/.gitkeep` 脚手架，未修改 `global_sites.json`
- [2026-05-18 17:37] manager=L2-01 child=M24A status=completed commit=10557c6 verify=`py -m pytest -q` 138 passed note=冻结 20 校 SITE_ID、中文名、城市、优先级，输出 `docs/地图方案B_M24A_20校SITE_ID注册表.md`

```text
- [YYYY-MM-DD HH:MM] manager=<L2-XX> child=<阶段ID> status=<completed|blocked> commit=<sha或none> verify=<命令摘要> note=<简述>
```
