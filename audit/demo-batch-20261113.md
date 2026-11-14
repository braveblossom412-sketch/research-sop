# 演示批次跑通记录 2026-11-13

## 背景
按要求先用虚构样例跑通 research-sop 全流程，查看产物形态；数据非真实、非验收基准。样例：`golden-set/demo-batch/papers.json`（11 条，含缺 DOI、标题近似重复、缺标题非法用例）。

## 执行
- 跑批脚本：`src/tools/run_demo.py`（ingest → dedup → matrix → verify 离线 → 总览 HTML）
- 产物目录：`outputs/demo-batch/`（独立批次，未覆盖既有库存与历史产物）
- 运行环境：根 `.venv`（Python 3.11.9），本轮补装已声明依赖 `openpyxl 3.1.5`、`pytest 9.2.0`

## 结果（离线 mock，未联网校验）
- 入库：提交 11，入库 10，校验拒绝 1（P-011 缺标题）
- 去重：保留 9，标记重复 1（P-010 与 P-001 标题相似度 0.95）
- 矩阵：9 行 × 固定 12 列，年份降序；方法/样本量/可复现性等 schema 未定义字段统一「待核实」
- 校验：9 条全部 pending（离线，占位/缺 DOI 不联网）

## 已知问题（留痕，未在本轮展开修）
- 现有 3 个 CLI 端到端测试（test_dedup / test_matrix / test_verify）因测试硬编码昨日日期、CLI 按当天日期写文件而 FileNotFoundError，属历史日期快照耦合，非本轮引入；需后续把日期改为注入参数。
- 全量联网校验仍待授权；正式 golden-set ≥20 条可溯源样本未提供。

## 待确认（C 档）
- 是否认可本演示批次的产物形态作为 M1 本地端到端 DEMO 的雏形。
- 后端框架 FastAPI / Flask（规划 §7）。
