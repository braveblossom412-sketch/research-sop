"""字段归一化：DOI / 标题 / 作者名（确定性逻辑，保留原始值）。"""
from __future__ import annotations

import re

DOI_PREFIX_RE = re.compile(r"^https?://(dx\.)?doi\.org/", re.I)
NON_ALNUM_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")
PLACEHOLDER_DOI = {"待核实", "n/a", "na", "none", "null", "tbd", "-", "--", ""}


def norm_doi(doi: str | None) -> str:
    """DOI 归一化：小写、去 https://doi.org/ 前缀、去尾部斜杠。占位哨兵视为缺失。"""
    if not doi:
        return ""
    s = DOI_PREFIX_RE.sub("", str(doi).strip().lower())
    s = s.rstrip("/")
    return "" if s in PLACEHOLDER_DOI else s


def norm_title(title: str | None) -> str:
    """标题归一化（用于模糊匹配）：小写、非字母数字折叠为单空格。"""
    if not title:
        return ""
    return " ".join(NON_ALNUM_RE.sub(" ", str(title).lower()).split())


def norm_authors(authors: str | None) -> str:
    """作者名归一化为「姓, 名首字母」；无法拆分时原样返回。"""
    if not authors:
        return "待核实"
    parts = []
    for raw in re.split(r"[;；,，]", str(authors)):
        raw = raw.strip()
        if not raw:
            continue
        toks = raw.split()
        if len(toks) == 0:
            continue
        if "," in raw or (len(toks) >= 2 and not raw.endswith(".")):
            family = toks[-1]
            given = toks[0][0] if len(toks) >= 2 else ""
        else:
            family = toks[0]
            given = toks[-1][0] if len(toks) >= 2 else ""
        parts.append(f"{family}, {given}".rstrip(", "))
    return "; ".join(p for p in parts if p) or "待核实"


def normalize_record(record: dict) -> dict:
    """返回归一化副本，保留 authors_raw（原始作者值）。不修改原记录。"""
    out = dict(record)
    out["authors_raw"] = out.get("authors")
    out["doi"] = norm_doi(out.get("doi")) or None
    out["title_norm"] = norm_title(out.get("title"))
    out["authors"] = norm_authors(out.get("authors"))
    return out
