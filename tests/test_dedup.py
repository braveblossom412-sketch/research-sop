"""TASK-003 去重与归一化测试。阈值与断言按任务卡固定，不得为过测而改。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from literature.dedup import dedup
from literature.normalize import norm_authors, norm_doi, norm_title, normalize_record


def rec(rid, doi=None, title=None, year=None, authors=None):
    return {"id": rid, "title": title, "authors": authors, "year": year,
            "journal": None, "doi": doi, "abstract": None, "source": None,
            "status": "待核实", "imported_at": "2026-11-12"}


class TestNormDoi:
    def test_doi_lowercase(self):
        assert norm_doi("10.1000/ABC123") == "10.1000/abc123"

    def test_doi_strip_prefix(self):
        assert norm_doi("https://doi.org/10.1000/xyz") == "10.1000/xyz"
        assert norm_doi("http://dx.doi.org/10.1000/xyz") == "10.1000/xyz"

    def test_doi_strip_trailing_slash(self):
        assert norm_doi("10.1000/xyz/") == "10.1000/xyz"

    def test_doi_empty(self):
        assert norm_doi(None) == ""
        assert norm_doi("") == ""

    def test_doi_placeholder_not_treated_as_real(self):
        # 占位哨兵不得当作真实 DOI（避免不同记录因同一占位符被误合并）
        assert norm_doi("待核实") == ""
        assert norm_doi("N/A") == ""


class TestNormTitle:
    def test_title_fold_and_collapse(self):
        assert norm_title("  The  COVID-19  Pandemic! ") == "the covid 19 pandemic"

    def test_title_cjk_kept(self):
        assert norm_title("蛋白质 折叠 研究") == "蛋白质 折叠 研究"


class TestNormAuthors:
    def test_authors_given_family_format(self):
        assert norm_authors("Alice Smith; Bob Jones") == "Smith, A; Jones, B"

    def test_authors_raw_preserved(self):
        src = {"authors": "Alice Smith; Bob Jones"}
        out = normalize_record(src)
        assert out["authors_raw"] == "Alice Smith; Bob Jones"
        assert out["authors"] == "Smith, A; Jones, B"
        assert src["authors"] == "Alice Smith; Bob Jones"  # 原值不被改写


class TestDedup:
    def test_doi_case_insensitive_merge(self):
        a = rec("a", doi="https://doi.org/10.1000/ABC", title="Same paper")
        b = rec("b", doi="10.1000/abc", title="Same paper")
        deduped, dups = dedup([a, b])
        assert len(deduped) == 1
        assert len(dups) == 1
        assert dups[0]["kept_id"] == "a" and dups[0]["dropped_id"] == "b"
        assert dups[0]["match_reason"] == "doi 相同"
        assert dups[0]["score"] == 1.0

    def test_title_fuzzy_match_above_threshold(self):
        a = rec("a", doi=None, title="Effects of Vitamin D on Bone Density", year=2020)
        b = rec("b", doi=None, title="Effects of Vitamin D on Bone Densities", year=2020)
        deduped, dups = dedup([a, b])
        assert len(deduped) == 1
        assert dups[0]["match_reason"].startswith("标题相似度")

    def test_title_below_threshold_not_merged(self):
        a = rec("a", doi=None, title="A completely unrelated paper title", year=2020)
        b = rec("b", doi=None, title="Another totally different topic", year=2021)
        deduped, dups = dedup([a, b], threshold=0.92)
        assert len(deduped) == 2 and len(dups) == 0

    def test_same_title_different_year_not_merged(self):
        a = rec("a", doi=None, title="Identical title here", year=2019)
        b = rec("b", doi=None, title="Identical title here", year=2022)
        deduped, dups = dedup([a, b])
        assert len(deduped) == 2 and len(dups) == 0

    def test_threshold_configurable(self):
        a = rec("a", doi=None, title="RNA interference in cancer therapy", year=2021)
        b = rec("b", doi=None, title="RNA interferenc in cancer therap", year=2021)
        loose, _ = dedup([a, b], threshold=0.85)
        strict, dups = dedup([a, b], threshold=0.98)
        assert len(loose) == 1          # 低阈值合并
        assert len(strict) == 2 and len(dups) == 0  # 高阈值不合并

    def test_duplicates_fields_complete(self):
        a = rec("a", doi="10.1000/xyz", title="T")
        b = rec("b", doi="10.1000/xyz", title="T")
        _, dups = dedup([a, b])
        assert set(dups[0].keys()) == {"kept_id", "dropped_id", "match_reason", "score"}

    def test_no_physical_delete(self):
        a = rec("a", doi="10.1000/one", title="A")
        b = rec("b", doi="10.1000/two", title="B")
        deduped, _ = dedup([a, b])
        assert len(deduped) == 2          # 分流后仍保留全部唯一记录

    def test_l3_reproducible(self):
        rows = [rec("a", doi="10.1000/aaa", title="X", year=2020),
                rec("b", doi=None, title="X", year=2020),
                rec("c", doi="10.1000/ccc", title="Y", year=2021)]
        d1, u1 = dedup(rows)
        d2, u2 = dedup(rows)
        assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)
        assert json.dumps(u1, sort_keys=True) == json.dumps(u2, sort_keys=True)

    def test_jsonl_outputs_parseable(self, tmp_path):
        rows = [rec("a", doi="10.1000/aaa", title="X", year=2020),
                rec("b", doi="10.1000/aaa", title="X", year=2020)]
        src = tmp_path / "in.jsonl"
        src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        out = tmp_path / "out"
        subprocess.run([sys.executable, "-m", "literature.dedup", "--in", str(src),
                        "--out-dir", str(out), "--date", "20261112"], check=True, cwd=str(SRC))
        deduped = [json.loads(l) for l in (out / "deduped-20261112.jsonl").read_text().splitlines() if l.strip()]
        dups = [json.loads(l) for l in (out / "duplicates-20261112.jsonl").read_text().splitlines() if l.strip()]
        assert len(deduped) == 1 and len(dups) == 1
        assert dups[0]["match_reason"] == "doi 相同"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
