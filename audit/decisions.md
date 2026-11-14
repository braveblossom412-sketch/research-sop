# decisions.md — 自主运行决策留痕（B 档）

## [2026-11-12] [档位B] 决策：补全 TASK-002 任务卡
- 理由：registry.yaml 声明 TASK-002 ready，但磁盘无任务卡；AUTONOMY.md §5.2 授权缺卡自补。golden-set README 第 14-15 行"用本规范校验 data/lit.jsonl 结构一致"指向结构校验工具化需求。
- 影响：TASK-002 定为"golden-set 结构校验工具"，把 L1/L3 验收机器化；真实样本归 TASK-004（已 blocked_c），本任务不依赖数据源、不涉及编造样本。
- 备选：将 TASK-002 定义为"真实样本入库"——不可行，依赖 TASK-004 数据源（C 档阻塞），故弃。

## [2026-11-12] [档位B] 决策：补全 TASK-003 任务卡
- 理由：registry 声明 TASK-003 ready 但磁盘无卡。TASK-001 卡 §2 已声明支持 .csv 输入但从未验证，本任务验收该已声明能力，不扩范围、不加功能。
- 影响：TASK-003 定为"CSV 导入路径验收"，产出 demo.csv 样例 + CSV 导入跑通 + check_lit 校验一致。

## [2026-11-12] [档位B] 决策：占位哨兵「待核实」不视为真实 DOI
- 理由：TASK-003 去重实测发现 `doi="待核实"` 被当作真实 DOI，导致 csv-001 等不同记录因同一占位符被误合并（误杀率超限风险）。"待核实"是 ingest 层的缺失占位，非 DOI 值。
- 影响：`normalize.norm_doi` 将「待核实 / N/A / none / null / -」等哨兵归为缺失（返回空串），去重回退到标题+年份模糊匹配；新增测试固化。修复后 8 条输入 → 4 deduped + 4 duplicates，重复对全部为同 id 二次导入，无误杀。
- 备选：改去重阈值——无效（DOI 分支 score 恒为 1.0）；改 ingest 清洗占位——越界改别层，故弃。
