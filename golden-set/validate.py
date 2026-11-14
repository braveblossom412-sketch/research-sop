"""golden-set 校验：字段完整性 / 必填项 / DOI 格式 / 表头一致性。

用法:
  python validate.py --file template.csv            # 空模板应通过
  python validate.py --file smoke/samples.csv --smoke  # 冒烟样本（额外检 source_url/retrieved_at）
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

EXPECTED_HEADER = [
    "id", "title", "authors", "year", "journal", "doi",
    "abstract", "source", "status", "imported_at",
]
REQUIRED = {"id", "title", "year", "status"}
SMOKE_EXTRA = ["source_url", "retrieved_at"]
ALLOWED_STATUS = {"new", "normalized", "verified", "pending"}
DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$")


def check(path: Path, smoke: bool) -> dict:
    problems: list[str] = []
    import io

    with path.open(encoding="utf-8-sig", newline="") as f:
        filtered = io.StringIO("\n".join(ln for ln in f if not ln.lstrip().startswith("#")))
        reader = csv.DictReader(filtered)
        header = reader.fieldnames or []
        rows = list(reader)

    expect = list(EXPECTED_HEADER) + (list(SMOKE_EXTRA) if smoke else [])
    if header != expect:
        problems.append(f"表头不一致: 期望 {expect}，实际 {header}")

    for i, row in enumerate(rows, start=2):
        for k in REQUIRED:
            if not (row.get(k) or "").strip():
                problems.append(f"第{i}行缺必填 {k}")
        st = (row.get("status") or "").strip()
        if st and st not in ALLOWED_STATUS:
            problems.append(f"第{i}行 status 非法: {st}")
        yr = (row.get("year") or "").strip()
        if yr and not yr.isdigit():
            problems.append(f"第{i}行 year 非数字: {yr}")
        doi = (row.get("doi") or "").strip()
        if doi and not DOI_RE.match(doi):
            problems.append(f"第{i}行 doi 格式非法: {doi}")
        if smoke:
            for k in SMOKE_EXTRA:
                if not (row.get(k) or "").strip():
                    problems.append(f"第{i}行冒烟必填缺 {k}")

    return {"file": str(path), "rows": len(rows), "smoke": smoke, "ok": not problems, "problems": problems[:20]}


def main() -> int:
    p = argparse.ArgumentParser(description="golden-set 校验")
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="冒烟模式：额外校验 source_url/retrieved_at")
    args = p.parse_args()

    if not args.file.exists():
        print(f"文件不存在: {args.file}", file=sys.stderr)
        return 2
    report = check(args.file, args.smoke)
    for pr in report["problems"]:
        print(f"  ✗ {pr}", file=sys.stderr)
    print(f"{'通过' if report['ok'] else '失败'}（{report['rows']} 行，冒烟={report['smoke']}）")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
