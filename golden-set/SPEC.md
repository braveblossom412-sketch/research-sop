# golden-set 标注规范（SPEC v0）

## 1. 字段口径（与 TASK-001 schema 完全一致，不得新增）
`id, title, authors, year, journal, doi, abstract, source, status, imported_at`

必填：`id / title / year / status`
- `id`：全局唯一，格式 `GS-四位序号`（正式样本）或 `SMOKE-三位序号`（冒烟样本）
- `year`：四位数字
- `status`：仅 `new / normalized / verified / pending`
- `doi`：可选但必须规范（小写、无 `https://doi.org/` 前缀、无尾部斜杠，形如 `10.xxxx/xxxx`）
- `source`：可溯源出处（期刊名 / 数据库编号）

冒烟样本**附加**字段（仅冒烟层，正式样本不含）：`source_url`（可点回链接）、`retrieved_at`（采集时间 ISO）

## 2. 判定口径
- 同一文献以 **DOI 规范化值** 为唯一键；无 DOI 时以 `title 归一化 + year` 为键
- 禁止把"解析失败"判为"文献不存在"

## 3. 禁编造规则（红线）
- 任何条目必须可点回公开来源：`source_url` 可访问或 DOI 可解析
- 禁止凭空生成标题/作者/年份；字段缺失填 `待核实`，禁止编造
- 冒烟样本与正式样本**物理隔离**：`smoke/` 永远不进入验收基准
- 正式样本 ≥20 条、可溯源，须用户提供或用户授权采集后才入库（C 档）

## 4. 目录结构
```
golden-set/
  SPEC.md          # 本文件
  template.csv     # 空模板（含全部表头）
  smoke/           # 冒烟样本（仅技术冒烟，不作验收基准）
  samples.jsonl    # 正式验收样本（TASK-002 用户提供后由 TASK-004 等使用，当前未生成）
```

## 5. 校验工具
`golden-set/validate.py`：字段完整性、必填项、DOI 格式、表头一致性；冒烟模式另检 `source_url`/`retrieved_at`。
