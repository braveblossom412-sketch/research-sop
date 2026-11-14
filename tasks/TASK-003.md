# TASK-003 文献去重与字段归一化

## 1. 目标
对 ingest 后的文献记录做去重与字段归一化，输出干净数据集和重复报告，保证同一条文献不会重复计入矩阵。

## 2. 输入
- `src/literature/` 现有 ingest 模块
- `golden-set/smoke/` 冒烟样本（TASK-002）
- 字段定义以 TASK-001 schema 为准

## 3. 输出
- `src/literature/dedup.py`：去重模块
- `src/literature/normalize.py`：归一化模块
- `outputs/deduped-YYYYMMDD.jsonl`：去重后数据
- `outputs/duplicates-YYYYMMDD.jsonl`：重复记录，含 `kept_id`、`dropped_id`、`match_reason`、`score`
- `tests/test_dedup.py`：pytest 用例 ≥8 条
- `audit/` 追加记录

## 4. 约束
- DOI 归一化规则：小写、去 `https://doi.org/` 前缀、去尾部斜杠
- 标题匹配用模糊算法（difflib 或 rapidfuzz），阈值默认 0.92，必须可配置
- 作者名归一化为「姓, 名首字母」，不得丢弃原值（保留 `authors_raw`）
- 去重只做"标记+分流"，禁止物理删除原始记录
- 不许为通过测试而修改测试断言

## 5. 验收标准
- L1 格式：输出 jsonl 每行可被 `json.loads` 解析；`duplicates` 文件字段齐全
- L2 事实可核：抽 5 组重复对，人工确认确为同一文献，误杀率 ≤1 条
- L3 可复现：同一输入跑两次，`deduped` 与 `duplicates` 内容完全一致
- L4 人工可用：用户能看懂 `match_reason` 并判断是否合理，评分 ≥4/5

## 6. 派工与档位
- 执行：TRAE
- 测试与审查：CodeBuddy
- 允许改目录：`src/literature/`、`tests/`、`outputs/`、`audit/`
- **B 档**：模糊匹配阈值微调（±0.05 内），记 decisions
- **C 档**：阈值调整超过 ±0.05，需用户确认

## 7. token 预算
30k

## 8. 失败处理
- 依赖装不上 → 退回标准库 difflib，记录原因
- 误杀率超 1 条 → 提高阈值重跑，不改测试
- 连续 3 次失败 → 转 C 档，写入 pending

## 9. 依赖
TASK-001（ingest 模块）、TASK-002（冒烟样本）
