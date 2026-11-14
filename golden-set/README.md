# golden-set — 验收基准样本

## 现状
- 本目录为 **规范占位**。样本条目尚未入库，等待真实数据源确认（TASK-002 负责）。
- 铁律：**禁止编造样本**。任何条目必须可溯源（可点回原始来源）。

## 样本规范（TASK-002 按此入库）
- 数量：≥ 20 条。
- 来源：每条含 `source` 字段（期刊 DOI / 数据库编号），供 L2 事实可核抽检。
- 结构：与 `src/schema/literature.py` 字段一致：`id, title, authors, year, journal, doi, abstract, source, status, imported_at`。
- 格式：`golden-set/samples.jsonl`，一行一条。
- 覆盖：至少 3 类边界（正常条目 / 缺 DOI / 年份异常）。

## 使用
- 骨架验收：TASK-001 跑通后，用本规范校验 `data/lit.jsonl` 结构一致。
- 后续任务回归：同输入二次执行比对（L3）。

## 待办
- [ ] 确认数据源（待用户拍板）
- [ ] 入库 ≥20 条真实可溯源样本
