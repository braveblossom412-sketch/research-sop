# TASK-005 引用可核校验器（L2 专用）

## 1. 目标
对矩阵中每条文献的 DOI 做可核性校验，确保 L2 事实可核达标，凡不可解析的一律标「待核实」而非删除。

## 2. 输入
- `outputs/lit-matrix-YYYYMMDD.csv`（TASK-004）
- DOI 解析服务：doi.org 内容协商或 Crossref API

## 3. 输出
- `src/literature/verify.py`：校验模块
- `outputs/verification-YYYYMMDD.jsonl`：逐条结果，字段 `doi`、`status`（ok/failed/pending）、`http_code`、`resolved_title`、`title_match`、`checked_at`
- `outputs/verification-summary-YYYYMMDD.md`：汇总（总数、通过数、待核实数、通过率）
- `tests/test_verify.py`：pytest 用例 ≥6 条（含 mock 网络失败）
- `audit/` 追加记录

## 4. 约束
- 网络请求必须设超时（默认 10s）与重试（≤2 次），禁止无限重试
- 失败一律标 `pending` + 原因，禁止删除该行
- 禁止把"解析失败"判定为"文献不存在"
- 测试必须用 mock，不许真打外部接口跑 CI
- 校验频率限制：每秒 ≤3 次，避免被封

## 5. 验收标准
- L1 格式：`verification.jsonl` 每行字段齐全，`status` 取值仅限三值
- L2 事实可核：抽 5 条 `ok` 记录，人工点开 DOI 确认标题一致；`pending` 记录必须带原因
- L3 可复现：mock 环境下两次运行结果一致；真实环境下 `checked_at` 之外字段稳定
- L4 人工可用：`summary.md` 一眼能看出通过率，评分 ≥4/5

## 6. 派工与档位
- 执行：TRAE
- 测试：CodeBuddy
- 允许改目录：`src/literature/`、`tests/`、`outputs/`、`audit/`
- **C 档**：真实全量校验（>50 条）需用户确认后再跑，避免误触频率限制

## 7. token 预算
30k

## 8. 失败处理
- doi.org 不可达 → 切 Crossref API，记录切换原因
- 通过率 <90% → 不硬改阈值，输出问题清单转 C 档
- 连续 3 次网络失败 → 全部标 pending，停止当日校验

## 9. 依赖
TASK-004（矩阵 CSV）
