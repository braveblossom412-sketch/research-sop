"""引用可核校验器：对 DOI 做内容协商解析，失败一律标 pending，禁止删除行。

用法:
  python -m literature.verify --in outputs/lit-matrix-YYYYMMDD.csv --out-dir outputs
  python -m literature.verify --in golden-set/smoke/samples.csv --out-dir outputs --doi-col doi --title-col title
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TIMEOUT = 10          # 默认超时 10s
MAX_RETRIES = 2       # 重试 ≤2 次，禁止无限重试
RATE_LIMIT_PER_SEC = 3
PLACEHOLDER = {"待核实", "n/a", "na", "none", "null", "-", ""}


def norm_doi(v: str | None) -> str:
    if not v:
        return ""
    s = str(v).strip().lower()
    for pre in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    s = s.rstrip("/")
    return "" if s in PLACEHOLDER else s


def resolve_doi(doi: str, timeout: int = TIMEOUT, max_retries: int = MAX_RETRIES) -> dict:
    """内容协商解析。返回 {status, http_code, resolved_title, error}。"""
    url = f"https://doi.org/{doi}"
    last_err = ""
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, headers={"Accept": "application/x-bibtex;q=1.0,text/x-bibliography;q=0.5,*/*;q=0.1"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                code = resp.getcode()
                title = _parse_bibtex_title(body) or _parse_html_title(body)
                return {"status": "ok" if title else "failed",
                        "http_code": code, "resolved_title": title, "error": ""}
        except Exception as e:  # 网络失败：标 pending，不判定为不存在
            last_err = str(e)[:200]
            time.sleep(0.5 * (attempt + 1))
    return {"status": "pending", "http_code": None, "resolved_title": None,
            "error": f"network:{last_err}"}


def _parse_bibtex_title(body: str) -> str | None:
    import re
    m = re.search(r"title\s*=\s*\{(.+?)\}", body, re.S)
    return m.group(1).strip() if m else None


def _parse_html_title(body: str) -> str | None:
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    return m.group(1).strip() if m else None


def title_similar(title: str, resolved: str | None) -> str:
    """标题粗匹配：归一化后相等/包含。返回 'match'/'mismatch'/'unknown'。"""
    if not title or not resolved:
        return "unknown"
    a = " ".join(c for c in title.lower() if c.isalnum())
    b = " ".join(c for c in resolved.lower() if c.isalnum())
    if a and (a == b or a in b or b in a):
        return "match"
    return "mismatch"


def verify_row(doi_raw: str | None, title: str | None) -> dict:
    """单行校验。占位/缺失 DOI → pending（无网校验，仅记录）。"""
    doi = norm_doi(doi_raw)
    now = datetime.now(timezone.utc).isoformat()
    if not doi or doi in PLACEHOLDER:
        return {"doi": doi_raw or "", "status": "pending", "http_code": None,
                "resolved_title": None, "title_match": "unknown",
                "error": "no-doi:输入为占位或缺失，需人工核实", "checked_at": now}
    r = resolve_doi(doi)
    return {"doi": doi_raw or "", "status": r["status"], "http_code": r["http_code"],
            "resolved_title": r["resolved_title"], "title_match": title_similar(title, r["resolved_title"]),
            "error": r["error"], "checked_at": now}


def verify_records(records: list[dict], doi_col: str = "DOI", title_col: str = "标题",
                   rate_per_sec: int = RATE_LIMIT_PER_SEC) -> list[dict]:
    out = []
    for i, rec in enumerate(records):
        out.append(verify_row(rec.get(doi_col), rec.get(title_col)))
        if rate_per_sec > 0 and (i + 1) % rate_per_sec == 0:
            time.sleep(1)  # 每秒 ≤3 次
    return out


def summarize(results: list[dict]) -> dict:
    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "failed")
    pending = sum(1 for r in results if r["status"] == "pending")
    total = len(results)
    rate = ok / total if total else 0.0
    return {"total": total, "ok": ok, "failed": failed, "pending": pending,
            "pass_rate": round(rate, 3)}


def write_summary(path: Path, stats: dict) -> None:
    path.write_text(
        f"# 引用可核性校验汇总\n\n"
        f"- 总数: {stats['total']}\n"
        f"- 通过 (ok): {stats['ok']}\n"
        f"- 解析失败 (failed): {stats['failed']}\n"
        f"- 待核实 (pending): {stats['pending']}\n"
        f"- 通过率: {stats['pass_rate'] * 100:.1f}%\n",
        encoding="utf-8")


def load_csv(path: Path) -> list[dict]:
    import io
    text = path.read_text(encoding="utf-8-sig")
    buf = io.StringIO("\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#")))
    return [dict(r) for r in csv.DictReader(buf)]


def main() -> int:
    p = argparse.ArgumentParser(description="引用可核校验器")
    p.add_argument("--in", dest="inp", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    p.add_argument("--doi-col", default="DOI")
    p.add_argument("--title-col", default="标题")
    p.add_argument("--no-net", action="store_true", help="跳过网络请求，全部标 pending（离线冒烟）")
    p.add_argument("--date", default=None, help="产物日期戳 YYYYMMDD，默认当天；测试可注入固定值")
    args = p.parse_args()

    if not args.inp.exists():
        print(f"文件不存在: {args.inp}", file=__import__("sys").stderr)
        return 2
    records = load_csv(args.inp)
    if args.no_net:
        results = [verify_row(r.get(args.doi_col), r.get(args.title_col)) for r in records]
    else:
        results = verify_records(records, args.doi_col, args.title_col)

    stamp = args.date or datetime.now().strftime("%Y%m%d")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    j_path = args.out_dir / f"verification-{stamp}.jsonl"
    with j_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = summarize(results)
    m_path = args.out_dir / f"verification-summary-{stamp}.md"
    write_summary(m_path, stats)

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
