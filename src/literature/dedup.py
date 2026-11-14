"""文献去重：标记+分流，禁止物理删除。DOI 为唯一键；无 DOI 按标题+年份模糊匹配。

用法: python -m literature.dedup --in data/lit.jsonl --out-dir outputs [--threshold 0.92]
"""
from __future__ import annotations

import argparse
import difflib
import json
from datetime import datetime
from pathlib import Path

from literature.normalize import norm_doi, norm_title


def dedup(records: list[dict], threshold: float = 0.92) -> tuple[list[dict], list[dict]]:
    """返回 (deduped, duplicates)。duplicates 含 kept_id/dropped_id/match_reason/score。"""
    doi_seen: dict[str, dict] = {}
    title_seen: list[tuple[str, str, dict]] = []
    deduped: list[dict] = []
    duplicates: list[dict] = []

    for rec in records:
        rid = rec.get("id") or "?"
        d = norm_doi(rec.get("doi"))
        if d:
            if d in doi_seen:
                duplicates.append({
                    "kept_id": doi_seen[d]["id"], "dropped_id": rid,
                    "match_reason": "doi 相同", "score": 1.0,
                })
            else:
                doi_seen[d] = rec
                deduped.append(rec)
            continue

        nt = norm_title(rec.get("title"))
        yr = str(rec.get("year") or "")
        best: tuple[float, dict] | None = None
        for snt, syr, srec in title_seen:
            if not nt or not snt or (yr and syr and yr != syr):
                continue
            ratio = difflib.SequenceMatcher(None, nt, snt).ratio()
            if ratio >= threshold and (best is None or ratio > best[0]):
                best = (ratio, srec)
        if best:
            ratio, srec = best
            duplicates.append({
                "kept_id": srec["id"], "dropped_id": rid,
                "match_reason": f"标题相似度 {ratio:.2f}", "score": round(ratio, 4),
            })
        else:
            title_seen.append((nt, yr, rec))
            deduped.append(rec)

    return deduped, duplicates


def main() -> int:
    p = argparse.ArgumentParser(description="文献去重（标记+分流）")
    p.add_argument("--in", dest="inp", type=Path, required=True, help="输入 jsonl")
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    p.add_argument("--threshold", type=float, default=0.92)
    p.add_argument("--date", default=None, help="产物日期戳 YYYYMMDD，默认当天；测试可注入固定值")
    args = p.parse_args()

    if not args.inp.exists():
        print(f"文件不存在: {args.inp}", file=__import__("sys").stderr)
        return 2
    records = [json.loads(ln) for ln in args.inp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    deduped, duplicates = dedup(records, args.threshold)

    stamp = args.date or datetime.now().strftime("%Y%m%d")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    d_path = args.out_dir / f"deduped-{stamp}.jsonl"
    u_path = args.out_dir / f"duplicates-{stamp}.jsonl"
    with d_path.open("w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with u_path.open("w", encoding="utf-8") as f:
        for r in duplicates:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({
        "input": len(records), "deduped": len(deduped),
        "duplicates": len(duplicates), "threshold": args.threshold,
        "deduped_file": str(d_path), "duplicates_file": str(u_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
