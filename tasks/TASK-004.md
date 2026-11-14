# TASK-004 文献对比矩阵导出

## 1. 目标
把去重后的文献数据导出为可直接阅读的对比矩阵（CSV + XLSX），字段固定、空值有明确标注，供研究者人工判读。

## 2. 输入
- `outputs/deduped-YYYYMMDD.jsonl`（TASK-003）
- 字段清单见 TASK-001 schema

## 3. 输出
- `src/literature/matrix.py`：矩阵导出模块
- `outputs/lit-matrix-YYYYMMDD.csv`
- `outputs/lit-matrix-YYYYMMDD.xlsx`
- `tests/test_matrix.py`：pytest 用例 ≥6 条
- `audit/` 追加记录

## 4. 约束
- 列顺序固定：`序号 / 标题 / 第一作者 / 年份 / 期刊或会议 / DOI / 方法 / 样本量 / 主要结论 / 可复现性 / 来源库 / 检索时间`
- 空值统一填 `待核实`，禁止留空、禁止填 `N/A`
- XLSX 必须冻结首行、列宽自适应、DOI 列设为超链接
- 禁止对结论字段做任何 AI 改写，只做截断（超 200 字截断并标 `…`）
- 排序默认按年份降序，同年按第一作者字母序

## 5. 验收标准
- L1 格式：CSV 与 XLSX 列名、列序完全一致；XLSX 首行冻结生效
- L2 事实可核：抽 5 行，DOI 点击可跳转，标题与 DOI 对应无误
- L3 可复现：同输入两次导出，CSV 逐字节一致（时间戳列除外）
- L4 人工可用：用户可直接打开 XLSX 阅读并用于组会，评分 ≥4/5

## 6. 派工与档位
- 执行：TRAE
- 测试：CodeBuddy
- 允许改目录：`src/literature/`、`tests/`、`outputs/`、`audit/`
- **A 档**：列宽、字体、冻结等展示细节自主决定

## 7. token 预算
25k

## 8. 失败处理
- openpyxl 不可用 → 先出 CSV，XLSX 转 C 档待装
- 逐字节比对失败 → 剔除时间戳列后重比，记 decisions
- 连续 2 次失败 → 降级为仅 CSV，记 B 档

## 9. 依赖
TASK-003（去重后数据）
