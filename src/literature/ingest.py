"""文献员：输入接收与解析（只读人工提交内容，不联网不爬取）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from schema.literature import validate, normalize


def parse_file(path: Path) -> list[dict]:
    """按扩展名解析 JSON / CSV，统一返回 dict 列表。"""
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else data.get("records", [])
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as f:
            records = list(csv.DictReader(f))
    else:
        raise ValueError(f"不支持的文件类型: {path.suffix}，仅支持 .json / .csv")

    if not records:
        raise ValueError("输入为空，无记录可入库")
    return records


def ingest(path: Path, raw_dir: Path, out_file: Path) -> dict:
    """接收 → 校验 → 原样留档 → 结构化落盘。返回统计。"""
    records = parse_file(path)

    valid, errors = [], []
    for i, r in enumerate(records):
        errs = validate(r)
        if errs:
            errors.append({"index": i, "record": r, "errors": errs})
        else:
            valid.append(normalize(r))

    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_target = raw_dir / f"{path.stem}-{len(list(raw_dir.iterdir()))}{path.suffix}"
    raw_target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    if valid:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("a", encoding="utf-8") as f:
            for rec in valid:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "raw_archive": str(raw_target),
        "total": len(records),
        "imported": len(valid),
        "rejected": len(errors),
        "errors": errors[:10],
    }
