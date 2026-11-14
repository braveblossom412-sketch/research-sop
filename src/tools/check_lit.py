"""golden-set 结构校验工具：逐行校验 jsonl/json，输出结构化报告（L1/L3 机器化）。

用法: python -m tools.check_lit --file <lit.jsonl|samples.jsonl|raw.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schema.literature import validate


def load_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        records = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else data.get("records", [])
    else:
        raise ValueError("仅支持 .jsonl / .json")
    return records


def boundary_coverage(records: list[dict], invalid: list[dict]) -> dict:
    """检测边界类覆盖：正常 / 缺 DOI / 年份异常（给 golden-set 质量提示，非硬门禁）。"""
    has_normal = any(r.get("status") for r in records)
    missing_doi = any(r.get("doi") in (None, "") for r in records)
    year_anomaly = any("year" in "".join(e["errors"]) for e in invalid)
    return {
        "normal": bool(has_normal),
        "missing_doi": bool(missing_doi),
        "year_anomaly": bool(year_anomaly),
    }


def check(path: Path) -> dict:
    records = load_records(path)
    valid, invalid = [], []
    for i, r in enumerate(records):
        errs = validate(r)
        if errs:
            invalid.append({"index": i, "id": r.get("id"), "errors": errs})
        else:
            valid.append(r)
    return {
        "file": str(path),
        "checked": len(records),
        "valid": len(valid),
        "invalid": len(invalid),
        "error_samples": invalid[:3],
        "boundary_coverage": boundary_coverage(records, invalid),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check-lit", description="golden-set 结构校验")
    p.add_argument("--file", type=Path, required=True, help="待校验文件 .jsonl / .json")
    args = p.parse_args(argv)

    if not args.file.exists():
        print(json.dumps({"error": f"文件不存在: {args.file}"}, ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        report = check(args.file)
    except (ValueError, json.JSONDecodeError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["invalid"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
