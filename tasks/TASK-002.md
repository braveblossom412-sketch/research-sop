# TASK-002 黄金测试集基线与文献员角色卡

## 1. 目标
建立可执行的黄金测试集（golden-set）采集与标注规范，产出文献员角色卡（role card）v0，并交付一个仅用于技术冒烟（不用于验收）的公开样本包。

## 2. 输入
- 现有 `golden-set/README.md`（TASK-001 产出）
- 公开可引用的开放获取文献元数据（Crossref / PubMed 开放接口）
- 用户后续提供的真实论文（C 档，见第 6 节）

## 3. 输出
- `golden-set/SPEC.md`：标注规范（字段定义、判定口径、禁编造规则）
- `golden-set/template.csv`：空模板，含全部字段表头
- `golden-set/smoke/`：3-5 条公开样本，每条带 `source_url` 与 `retrieved_at`，文件头注明"仅技术冒烟，不作验收基准"
- `golden-set/validate.py`：模板校验脚本（字段完整性、必填项、DOI 格式）
- `roles/literature-clerk.md`：文献员角色卡，含职责、输入输出、边界、禁止事项
- `audit/2026-11-13.md`：追加本次记录

## 4. 约束
- 禁止编造任何文献条目；冒烟样本必须可点回公开来源
- 禁止把冒烟样本混入正式 golden-set 目录
- 字段口径必须与 TASK-001 的 schema 一致，不得新增未定义字段
- 不调用需付费或需登录的数据库接口

## 5. 验收标准
- L1 格式：`template.csv` 表头齐全，`validate.py` 对空模板返回通过；冒烟样本字段完整率 100%
- L2 事实可核：冒烟样本逐条点开 `source_url` 可访问，DOI 可解析；抽检 3 条全部命中
- L3 可复现：`validate.py` 对同一输入跑两次结果一致；冒烟样本重新采集后结构不变
- L4 人工可用：角色卡读完能明确"文献员做什么、不做什么"，用户评分 ≥4/5

## 6. 派工与档位
- 执行：TRAE（写规范、脚本、角色卡）
- 审查：CodeBuddy（检查禁编造、字段一致性）
- 允许改目录：`golden-set/`、`roles/`、`audit/`
- **C 档**：真实论文样本录入需用户提供（3 篇 PDF 或 DOI + 学科方向），TRAE 不得代填

## 7. token 预算
25k，超限暂停

## 8. 失败处理
- 公开接口不可用 → 换 Crossref 备选端点，记录到 decisions
- 字段与 TASK-001 schema 冲突 → 以 schema 为准，记 B 档
- 连续 2 次校验失败 → 简化模板，先跑通再加字段

## 9. 依赖
TASK-001（骨架与 schema）
