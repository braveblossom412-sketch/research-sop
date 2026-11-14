"""文献对比矩阵导出：CSV + XLSX。列序固定、空值统一「待核实」、结论只截断不改写。

用法: python -m literature.matrix --in outputs/deduped-YYYYMMDD.jsonl --out-dir outputs
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

# 列顺序固定（TASK-004 §4）
COLUMNS = [
    "序号", "标题", "第一作者", "年份", "期刊或会议", "DOI",
    "方法", "样本量", "主要结论", "可复现性", "来源库", "检索时间",
]

CONCLUSION_MAX_LEN = 200

# schema 未定义的展示字段，一律「待核实」，禁止编造
UNKNOWN_FIELD = "待核实"


def _first_author(authors: str | None) -> str:
    """取作者串首个（按 ; 或 , 分隔）。"""
    if not authors:
        return UNKNOWN_FIELD
    first = next((p.strip() for p in str(authors).split(";") if p.strip()), "")
    return first or UNKNOWN_FIELD


def _conclusion(abstract: str | None) -> str:
    """主要结论：只截断，禁止 AI 改写。超长标 …。"""
    if not abstract:
        return UNKNOWN_FIELD
    s = str(abstract).strip()
    if len(s) > CONCLUSION_MAX_LEN:
        return s[:CONCLUSION_MAX_LEN] + "…"
    return s


def build_rows(records: list[dict]) -> list[list]:
    """按 年份降序 → 同年第一作者字母序 排序后生成矩阵行。"""
    def sort_key(rec: dict):
        year = str(rec.get("year") or "").strip()
        yr = int(year) if year.isdigit() else -1  # 空年份排最后
        return (-yr, _first_author(rec.get("authors")).lower())

    ordered = sorted(records, key=sort_key)
    rows = []
    for i, rec in enumerate(ordered, start=1):
        rows.append([
            i,
            str(rec.get("title") or UNKNOWN_FIELD),
            _first_author(rec.get("authors")),
            str(rec.get("year") or UNKNOWN_FIELD),
            str(rec.get("journal") or UNKNOWN_FIELD),
            str(rec.get("doi") or UNKNOWN_FIELD),
            UNKNOWN_FIELD,   # 方法
            UNKNOWN_FIELD,   # 样本量
            _conclusion(rec.get("abstract")),
            UNKNOWN_FIELD,   # 可复现性
            str(rec.get("source") or UNKNOWN_FIELD),
            str(rec.get("imported_at") or UNKNOWN_FIELD),  # 检索时间
        ])
    return rows


def write_csv(path: Path, rows: list[list]) -> None:
    import csv
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)


def write_xlsx(path: Path, rows: list[list]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "文献对比矩阵"
    ws.append(COLUMNS)
    for r in rows:
        ws.append(r)

    # 首行冻结 + 加粗
    ws.freeze_panes = "A2"
    for c in ws[1]:
        c.font = Font(bold=True)

    # DOI 列（第 6 列）超链接
    for row in ws.iter_rows(min_row=2, min_col=6, max_col=6):
        for cell in row:
            v = str(cell.value or "")
            if v != UNKNOWN_FIELD and v.startswith("10."):
                cell.hyperlink = f"https://doi.org/{v}"
                cell.style = "Hyperlink"

    # 列宽自适应（按内容长度，限宽 60）
    for col_cells in ws.columns:
        length = max(len(str(c.value or "")) for c in col_cells)
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(60, max(8, length + 2))

    wb.save(path)


def main() -> int:
    p = argparse.ArgumentParser(description="文献对比矩阵导出")
    p.add_argument("--in", dest="inp", type=Path, required=True, help="去重后 jsonl")
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    p.add_argument("--date", default=None, help="产物日期戳 YYYYMMDD，默认当天；测试可注入固定值")
    args = p.parse_args()

    if not args.inp.exists():
        print(f"文件不存在: {args.inp}", file=__import__("sys").stderr)
        return 2
    records = [json.loads(ln) for ln in args.inp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = build_rows(records)

    stamp = args.date or datetime.now().strftime("%Y%m%d")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / f"lit-matrix-{stamp}.csv"
    xlsx_path = args.out_dir / f"lit-matrix-{stamp}.xlsx"
    write_csv(csv_path, rows)
    write_xlsx(xlsx_path, rows)

    print(json.dumps({
        "records": len(records), "rows": len(rows),
        "columns": COLUMNS,
        "csv": str(csv_path), "xlsx": str(xlsx_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
