# TASK-001 建文献员角色骨架

## 1. 目标（一句话，可验收）
建立"文献员"角色最小闭环骨架：文献接收 → 解析 → 结构化入库，跑通一次 CLI 全流程，产出结构可被 TASK-002 golden-set 校验复用。

## 2. 输入（数据来源、格式、样例路径）
- 人工提交的文献条目，格式 JSON 或 CSV，字段见 §3。
- 样例：`src/samples/` 下自带的 3 条演示数据（字段值可含"待核实"占位，不得编造真实文献）。
- 首期学科：生物医学。

## 3. 输出（文件路径 + 字段清单）
- `src/schema/literature.py` —— 字段定义与校验
- `src/literature/ingest.py` —— 输入接收与解析
- `src/literature/cli.py` —— 命令行入口
- 入库产物：`data/raw/`（原样留档）+ `data/lit.jsonl`（结构化落盘）
- 字段清单：`id, title, authors, year, journal, doi, abstract, source, status, imported_at`

## 4. 约束（红线：禁止事项）
- 只改 `src/` 与 `data/`，不碰测试断言、不改 golden-set。
- 不联网检索、不爬取；只处理人工提交内容。
- 不硬编码密钥；可执行文件与说明写入环境变量引用。

## 5. 验收标准（四级）
- L1：字段齐全、命名规范、CLI 参数合法 → 机器校验 100%
- L2：演示数据含"待核实"标注，不伪造来源 → 人工抽检 ≥95%
- L3：同输入二次执行结构一致 → 100%
- L4：PI 可运行 CLI 完成一次入库，小改即用 → ≥4 分

## 6. 派工（TRAE / CodeBuddy，写明允许改的目录）
- TRAE（builder）：允许改 `src/`、`data/`、`src/samples/`。
- CodeBuddy（reviewer）：仅审不写，目录分离。

## 7. token 预算（单次上限）
- 50k（单任务），超限暂停等确认。

## 8. 失败处理（回滚 / 报警 / 降级）
- 连续 3 次失败 → 回滚 git commit，不硬刚。
- CLI 崩溃 → 保留 `data/raw/` 原档，重跑不覆盖。

## 9. 依赖（前置任务号）
- TASK-002：golden-set 样本规范先行占位（本任务放行条件：`golden-set/` 存在且含规范 README）。
