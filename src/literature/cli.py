"""文献员 CLI 入口：python -m literature.cli <input.json|csv> [--raw-dir] [--out]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from literature.ingest import ingest

DEFAULT_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "lit.jsonl"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lit-cli", description="文献员骨架：接收→解析→结构化入库")
    p.add_argument("input", type=Path, help="文献输入文件 .json / .csv")
    p.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW, help="原样留档目录")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="结构化输出 jsonl")
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"[lit-cli] 文件不存在: {args.input}", file=sys.stderr)
        return 1

    try:
        report = ingest(args.input, args.raw_dir, args.out)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[lit-cli] 解析失败: {e}", file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["rejected"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
