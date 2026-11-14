# -*- coding: utf-8 -*-
"""research-sop 本地演示后端（标准库零依赖）。

复用 src 既有引擎纯函数，不新增业务规则；离线运行，verify 不联网。
用法（在 research-sop 目录，PYTHONPATH=src）:
    python -m literature.server [--port 8091]
浏览器打开 http://127.0.0.1:8091/

数据源：
  lit   既有库存 src/data/lit.jsonl（占位样例）
  demo  演示批次 outputs/demo-batch/lit.jsonl（虚构样例）
  smoke 冒烟样本 golden-set/smoke/samples.csv（Crossref 公开元数据，仅技术冒烟）
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from schema.literature import validate, normalize
from literature.dedup import dedup
from literature.matrix import build_rows, COLUMNS
from literature.verify import verify_row, summarize, norm_doi, PLACEHOLDER

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "src" / "data" / "lit.jsonl"
SMOKE = ROOT / "golden-set" / "smoke" / "samples.csv"
DEMO = ROOT / "outputs" / "demo-batch" / "lit.jsonl"
WEB = ROOT / "web"
DEMO_OUT = ROOT / "outputs" / "web-ingest"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    buf = io.StringIO("\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#")))
    return [dict(r) for r in csv.DictReader(buf)]


def load_source(source: str) -> list[dict]:
    if source == "smoke":
        return _read_csv(SMOKE)
    if source == "demo":
        return _read_jsonl(DEMO)
    return _read_jsonl(LIT)


def offline_verify(records: list[dict]) -> list[dict]:
    """离线校验：不联网。占位/缺 DOI 记 no-doi；有 DOI 也记 pending（待联网授权）。"""
    out = []
    for r in records:
        doi = r.get("doi")
        if not norm_doi(doi):
            row = verify_row(doi, r.get("title"))
        else:
            row = {"doi": doi or "", "status": "pending", "http_code": None,
                   "resolved_title": None, "title_match": "unknown",
                   "error": "offline-demo: 离线演示未联网，待授权后再校验",
                   "checked_at": None}
        out.append(row)
    return out


HANDLERS: dict[str, callable] = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 静默访问日志
        return

    def _send_json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, ctype: str):
        if not path.exists():
            self._send_json({"error": "文件不存在"}, 404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self, key: str, default: str = "lit") -> str:
        q = parse_qs(urlparse(self.path).query)
        return q.get(key, [default])[0]

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send_file(WEB / "index.html", "text/html; charset=utf-8")
            return
        try:
            if path == "/api/sources":
                sources = []
                for key, label in [("lit", "既有库存（占位样例）"), ("demo", "演示批次（虚构样例）"),
                                   ("smoke", "Crossref 冒烟样本")]:
                    sources.append({"key": key, "label": label, "count": len(load_source(key))})
                self._send_json({"sources": sources})
            elif path == "/api/records":
                records = load_source(self._query("source"))
                self._send_json({"source": self._query("source"), "count": len(records), "records": records})
            elif path == "/api/dedup":
                records = load_source(self._query("source"))
                deduped, duplicates = dedup(records)
                self._send_json({"input": len(records), "deduped": len(deduped),
                                 "duplicates": len(duplicates), "deduped": deduped,
                                 "duplicates": duplicates})
            elif path == "/api/matrix":
                records = load_source(self._query("source"))
                rows = build_rows(records)
                self._send_json({"columns": COLUMNS, "rows": rows, "count": len(rows)})
            elif path == "/api/verify":
                records = load_source(self._query("source"))
                results = offline_verify(records)
                self._send_json({"results": results, "summary": summarize(results)})
            else:
                self._send_json({"error": "未知路径"}, 404)
        except Exception as e:  # 演示后端：错误如实返回，不吞
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/ingest":
            self._send_json({"error": "未知路径"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            raw = payload.get("records", [])
            if not isinstance(raw, list):
                raise ValueError("records 必须是数组")

            valid, errors = [], []
            for i, r in enumerate(raw):
                errs = validate(r)
                if errs:
                    errors.append({"index": i, "record": r, "errors": errs})
                else:
                    valid.append(normalize(r))

            DEMO_OUT.mkdir(parents=True, exist_ok=True)
            out_file = DEMO_OUT / "web-ingest.jsonl"
            with out_file.open("a", encoding="utf-8") as f:
                for rec in valid:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            self._send_json({"total": len(raw), "imported": len(valid), "rejected": len(errors),
                             "errors": errors[:10], "records": valid,
                             "out_file": str(out_file)})
        except Exception as e:
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 500)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="research-sop 本地演示后端")
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"research-sop 演示后端: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
