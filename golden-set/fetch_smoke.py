"""抓取 Crossref 公开开放获取文献元数据，生成冒烟样本（仅技术冒烟，不作验收基准）。

用法: python fetch_smoke.py [--out smoke/samples.csv] [--query "biomedical"] [--rows 5]
可复现：重跑后仅 retrieved_at 变化，其余字段稳定。
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.crossref.org/works"


def fetch(query: str, rows: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": query, "rows": rows,
        "select": "DOI,title,author,issued,container-title,URL",
    })
    req = urllib.request.Request(
        f"{API}?{params}",
        headers={"User-Agent": "research-sop-smoke/0.1 (harness@agent-factory.local)"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    return payload["message"]["items"]


def to_rows(items: list[dict], now: str) -> list[dict]:
    out = []
    for n, it in enumerate(items, start=1):
        doi = (it.get("DOI") or "").lower().strip()
        title = (it.get("title") or ["待核实"])[0] or "待核实"
        authors = "; ".join(
            f"{a.get('family', '待核实')}, {(a.get('given', '') or '')[:1]}".rstrip(", ")
            for a in it.get("author", []) or []
        ) or "待核实"
        year = (it.get("issued", {}).get("date-parts", [[None]])[0][0]) or "待核实"
        journal = (it.get("container-title") or ["待核实"])[0] or "待核实"
        out.append({
            "id": f"SMOKE-{n:03d}", "title": title, "authors": authors, "year": year,
            "journal": journal, "doi": doi, "abstract": "待核实（冒烟样本不抓摘要）",
            "source": f"Crossref:{doi}", "status": "new", "imported_at": now,
            "source_url": f"https://doi.org/{doi}" if doi else "待核实",
            "retrieved_at": now,
        })
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Crossref 冒烟样本采集")
    p.add_argument("--out", type=Path, default=Path("smoke/samples.csv"))
    p.add_argument("--query", default="biomedical artificial intelligence")
    p.add_argument("--rows", type=int, default=5)
    args = p.parse_args()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = to_rows(fetch(args.query, args.rows), now)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    header = ["id", "title", "authors", "year", "journal", "doi",
              "abstract", "source", "status", "imported_at",
              "source_url", "retrieved_at"]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        f.write("# 仅技术冒烟，不作验收基准。数据来源：Crossref 公开 API。\n")
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"已生成 {len(rows)} 条冒烟样本 -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
