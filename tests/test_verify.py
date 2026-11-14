"""TASK-005 引用可核校验器测试。全部用 mock，禁止真打外部接口。"""
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from literature.verify import (PLACEHOLDER, MAX_RETRIES, TIMEOUT,
                               norm_doi, resolve_doi, summarize,
                               title_similar, verify_row, verify_records, write_summary)


def _fake_response(body: str, code: int = 200):
    class R:
        def getcode(self): return code
        def read(self, *a, **k): return body.encode("utf-8")
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return R()


class TestNormDoi:
    def test_prefix_and_case(self):
        assert norm_doi("HTTPS://doi.org/10.1000/ABC/") == "10.1000/abc"

    def test_placeholder_returns_empty(self):
        assert norm_doi("待核实") == ""
        assert norm_doi("N/A") == ""


class TestResolveMock:
    def test_ok_resolution(self):
        body = "@article{x, title={Real Paper Title}}\n"
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(body)):
            r = resolve_doi("10.1000/abc")
        assert r["status"] == "ok"
        assert r["resolved_title"] == "Real Paper Title"

    def test_network_failure_is_pending_not_failed(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("t")), \
             mock.patch("time.sleep", return_value=None):
            r = resolve_doi("10.1000/abc")
        assert r["status"] == "pending"
        assert r["error"].startswith("network:")

    def test_retry_bounded(self):
        calls = []
        def boom(*a, **k):
            calls.append(1)
            raise ConnectionError("down")
        with mock.patch("urllib.request.urlopen", side_effect=boom), \
             mock.patch("time.sleep", return_value=None):
            r = resolve_doi("10.1000/abc")
        assert r["status"] == "pending"
        assert len(calls) == MAX_RETRIES + 1  # 重试 ≤2 次（共 3 次尝试），不无限

    def test_timeout_set_on_request(self):
        seen = {}
        def capture(req, **kw):
            seen.update(kw)
            raise ConnectionError("x")
        with mock.patch("urllib.request.urlopen", side_effect=capture), \
             mock.patch("time.sleep", return_value=None):
            resolve_doi("10.1000/abc")
        assert seen.get("timeout") == TIMEOUT


class TestTitleMatch:
    def test_match(self):
        assert title_similar("Covid-19 Study", "COVID-19 Study") == "match"

    def test_mismatch(self):
        assert title_similar("Unrelated Title A", "Completely Different B") == "mismatch"

    def test_unknown_when_missing(self):
        assert title_similar("", "Some Title") == "unknown"


class TestSummarize:
    def test_status_values_only_three(self):
        ok = [{"status": "ok"}, {"status": "failed"}, {"status": "pending"}]
        assert {r["status"] for r in ok} <= {"ok", "failed", "pending"}

    def test_pass_rate(self):
        s = summarize([{"status": "ok"}, {"status": "ok"}, {"status": "pending"}])
        assert s["total"] == 3 and s["ok"] == 2 and s["pending"] == 1
        assert s["pass_rate"] == round(2 / 3, 3)


class TestEndToEnd:
    def test_verify_row_no_doi_pending(self):
        r = verify_row("待核实", "Some title")
        assert r["status"] == "pending" and r["error"].startswith("no-doi")

    def test_verify_row_ok_with_mock(self):
        body = "@article{x, title={Real Title}}\n"
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(body)):
            r = verify_row("10.1000/abc", "Real Title")
        assert r["status"] == "ok" and r["title_match"] == "match"
        assert set(r) >= {"doi", "status", "http_code", "resolved_title", "title_match", "checked_at"}

    def test_cli_no_net_pending(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("DOI,标题\n待核实,T\n10.1000/abc,R\n", encoding="utf-8-sig")
        out = tmp_path / "out"
        subprocess.run([sys.executable, "-m", "literature.verify", "--in", str(src),
                        "--out-dir", str(out), "--no-net", "--date", "20261112"], check=True, cwd=str(SRC))
        lines = [json.loads(l) for l in (out / "verification-20261112.jsonl").read_text().splitlines() if l.strip()]
        assert len(lines) == 2 and all(l["status"] == "pending" for l in lines)
        assert (out / "verification-summary-20261112.md").exists()

    def test_summary_md_content(self, tmp_path):
        p = tmp_path / "s.md"
        write_summary(p, summarize([{"status": "ok"}] * 8 + [{"status": "pending"}] * 2))
        txt = p.read_text(encoding="utf-8")
        assert "总数: 10" in txt and "通过率: 80.0%" in txt


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
