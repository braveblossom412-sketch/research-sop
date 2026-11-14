"""文献条目 schema：字段定义与校验（确定性逻辑，非业务判断）。"""
from __future__ import annotations

REQUIRED_FIELDS = ["id", "title", "year", "status"]
OPTIONAL_FIELDS = [
    "authors", "journal", "doi", "abstract", "source", "imported_at",
]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

ALLOWED_STATUS = {"new", "normalized", "verified", "pending"}


def validate(record: dict) -> list[str]:
    """返回错误列表；空列表 = 通过。缺失字段补 None，不做业务判断。"""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record 必须是 dict"]

    for f in REQUIRED_FIELDS:
        if f not in record or record[f] in (None, ""):
            errors.append(f"缺少必填字段: {f}")

    if record.get("status") not in ALLOWED_STATUS:
        errors.append(f"status 非法: {record.get('status')!r}")

    if record.get("year") and not str(record["year"]).isdigit():
        errors.append(f"year 非数字: {record.get('year')!r}")

    unknown = set(record) - set(ALL_FIELDS)
    if unknown:
        errors.append(f"未知字段: {sorted(unknown)}")

    return errors


def normalize(record: dict) -> dict:
    """补齐缺失字段为 None 并落 imported_at。"""
    out = {f: record.get(f) for f in ALL_FIELDS}
    if out["imported_at"] is None:
        from datetime import datetime, timezone

        out["imported_at"] = datetime.now(timezone.utc).isoformat()
    return out
