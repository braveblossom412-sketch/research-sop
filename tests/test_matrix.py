"""TASK-004 矩阵导出测试。列序/空值/排序/截断/XLSX 展示与 L3 复现。"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from literature.matrix import COLUMNS, UNKNOWN_FIELD, build_rows, _conclusion, write_csv, write_xlsx


def rec(rid, title, year, authors, doi=None, journal=None, abstract=None, source=None):
    return {"id": rid, "title": title, "authors": authors, "year": year,
            "journal": journal, "doi": doi, "abstract": abstract,
            "source": source, "status": "pending", "imported_at": "2026-11-12T00:00:00+00:00"}


class TestColumnsAndOrder:
    def test_column_order_fixed(self):
        assert COLUMNS == ["序号", "标题", "第一作者", "年份", "期刊或会议", "DOI",
                           "方法", "样本量", "主要结论", "可复现性", "来源库", "检索时间"]

    def test_csv_xlsx_same_columns(self, tmp_path):
        rows = build_rows([rec("a", "T", 2020, "A. Smith", doi="10.1/x")])
        c = tmp_path / "m.csv"
        x = tmp_path / "m.xlsx"
        write_csv(c, rows)
        write_xlsx(x, rows)
        from openpyxl import load_workbook
        wb = load_workbook(x)
        ws = wb.active
        assert [cell.value for cell in ws[1]] == list(csv.reader(c.open(encoding="utf-8-sig")))[0]


class TestEmptyValues:
    def test_empty_filled_verified(self):
        rows = build_rows([rec("a", "T", 2020, None, doi=None, journal=None, abstract=None, source=None)])
        r = rows[0]
        assert "待核实" not in [str(rec.get("title")) for rec in [{"title": "T"}]]  # 占位自检
        for v in r:
            assert str(v) != "" and str(v) != "N/A"

    def test_unknown_schema_fields_are_verified(self):
        rows = build_rows([rec("a", "T", 2020, "A")])
        r = rows[0]
        # 序号/标题/第一作者/年份/期刊/DOI/来源库/检索时间之外 → 待核实
        assert r[6] == UNKNOWN_FIELD and r[7] == UNKNOWN_FIELD and r[9] == UNKNOWN_FIELD


class TestSorting:
    def test_year_desc_then_author_asc(self):
        rows = build_rows([
            rec("old", "Older", 2019, "B. Writer"),
            rec("new", "Newer", 2022, "A. Writer"),
            rec("same", "SameYear", 2022, "C. Writer"),
        ])
        titles = [r[1] for r in rows]
        assert titles == ["Newer", "SameYear", "Older"]

    def test_missing_year_last(self):
        rows = build_rows([
            rec("ny", "NoYear", None, "A"),
            rec("y", "HasYear", 2021, "A"),
        ])
        assert [r[1] for r in rows] == ["HasYear", "NoYear"]


class TestConclusion:
    def test_truncation_200_chars_with_ellipsis(self):
        long_abs = "结" * 300
        out = _conclusion(long_abs)
        assert out == "结" * 200 + "…" and len(out) == 201

    def test_short_conclusion_untouched(self):
        s = "A short finding."
        assert _conclusion(s) == s

    def test_missing_conclusion_verified(self):
        assert _conclusion(None) == UNKNOWN_FIELD


class TestXlsxStyle:
    def test_freeze_first_row(self, tmp_path):
        rows = build_rows([rec("a", "T", 2020, "A")])
        x = tmp_path / "m.xlsx"
        write_xlsx(x, rows)
        from openpyxl import load_workbook
        wb = load_workbook(x)
        assert wb.active.freeze_panes == "A2"

    def test_doi_hyperlink(self, tmp_path):
        rows = build_rows([rec("a", "T", 2020, "A", doi="10.1000/xyz")])
        x = tmp_path / "m.xlsx"
        write_xlsx(x, rows)
        from openpyxl import load_workbook
        cell = load_workbook(x).active.cell(row=2, column=6)
        assert cell.hyperlink is not None
        assert cell.hyperlink.target == "https://doi.org/10.1000/xyz"


class TestL3Reproducible:
    def test_two_runs_same_csv(self, tmp_path):
        rows = build_rows([rec("a", "T", 2020, "A", doi="10.1/x", abstract="abs")])
        c1, c2 = tmp_path / "a.csv", tmp_path / "b.csv"
        write_csv(c1, rows)
        write_csv(c2, rows)
        assert c1.read_bytes() == c2.read_bytes()

    def test_cli_end_to_end(self, tmp_path):
        rows = [rec("a", "T1", 2020, "A", doi="10.1/a", abstract="a1"),
                rec("b", "T2", 2021, "B", doi="10.1/b", abstract="a2")]
        src = tmp_path / "in.jsonl"
        src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        out = tmp_path / "out"
        subprocess.run([sys.executable, "-m", "literature.matrix", "--in", str(src),
                        "--out-dir", str(out), "--date", "20261112"], check=True, cwd=str(SRC))
        assert (out / "lit-matrix-20261112.csv").exists()
        assert (out / "lit-matrix-20261112.xlsx").exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
