# TASK-006 审计员角色 v0 与周报生成

## 1. 目标
建立审计员角色卡（role card）与审计卡模板，实现从 `audit/` 日志自动生成日报与周报，让用户只看报告不看过程。

## 2. 输入
- 各项目 `audit/*.md`（已有格式见 AGENTS.md 第 6 节）
- `harness/registry.yaml`（任务状态）
- `harness/AUTONOMY.md`（C 档清单）

## 3. 输出
- `roles/auditor.md`：审计员角色卡（职责、输入输出、禁止事项）
- `shared/audit-card-template.md`：审计卡模板
- `src/audit/report.py`：报告生成脚本
- `audit/daily-YYYYMMDD.md`：日报（自动生成）
- `audit/weekly-YYYY-Www.md`：周报（自动生成）
- `tests/test_report.py`：pytest 用例 ≥5 条

## 4. 约束
- 日报只报三块：今日完成、今日决策（B 档）、待你确认（C 档）
- 周报只报四块：完成任务数、token 消耗、C 档积压、方向偏移预警
- 禁止在报告中美化失败；失败必须原样呈现
- 禁止审计员参与业务决策，只做记录与汇总
- 报告必须含成本字段，无成本的报告视为不完整

## 5. 验收标准
- L1 格式：日报/周报四块结构齐全，字段不缺
- L2 事实可核：抽 3 条"今日完成"，能对应到 `tasks/` 里的真实状态
- L3 可复现：同一天日志跑两次，报告内容一致（时间戳除外）
- L4 人工可用：用户读完 3 分钟能判断"要不要出手"，评分 ≥4/5

## 6. 派工与档位
- 执行：TRAE
- 审查：CodeBuddy（检查是否漏报失败）
- 允许改目录：`src/audit/`、`roles/`、`shared/`、`tests/`、`audit/`
- **A 档**：报告排版、措辞自主决定

## 7. token 预算
20k

## 8. 失败处理
- audit 目录为空 → 输出"无记录"报告，不报错
- 日志格式不统一 → 做兼容解析，记 B 档
- 连续 2 次解析失败 → 降级为纯文本汇总，记 decisions

## 9. 依赖
TASK-001（audit 目录已存在）；可与 TASK-002~005 并行
