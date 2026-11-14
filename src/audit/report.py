"""审计员：从 audit/ 日志自动生成日报/周报。标准库实现，零依赖。

用法:
  python -m audit.report daily --audit-dir <dir> --date 2026-11-12
  python -m audit.report weekly --audit-dir <dir> --registry <path> --date 2026-11-12
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

TASK_ENTRY_RE = re.compile(r"^##\s+\[(\d{2}:\d{2})\]\s+(TASK-\w+)", re.M)
FIELD_LINE_RE = re.compile(r"^-\s+([^:：]+)[:：]\s*(.*)$", re.M)
B_DECISION_RE = re.compile(r"^##\s+\[(\d{4}-\d{2}-\d{2})\]\s+\[档位B\]\s*决策[:：]?\s*(.*)$", re.M)
PENDING_RE = re.compile(r"^##\s+\[(\d{4}-\d{2}-\d{2})\]\s+待确认[:：]?\s*(.*)$", re.M)
SKIP_FILES = ("daily-", "weekly-", "pending-", "decisions.md")


def _entries(audit_dir: Path) -> list[dict]:
    """收集 audit/*.md 中所有 `## [HH:MM] TASK-xx` 条目及字段。"""
    out: list[dict] = []
    if not audit_dir.exists():
        return out
    for fp in sorted(audit_dir.glob("*.md")):
        if fp.name.startswith(SKIP_FILES):
            continue
        text = fp.read_text(encoding="utf-8")
        for m in TASK_ENTRY_RE.finditer(text):
            end = TASK_ENTRY_RE.search(text, m.end())
            block = text[m.end(): end.start() if end else len(text)]
            fields = {k: v for k, v in FIELD_LINE_RE.findall(block)}
            out.append({"file": fp.name, "time": m.group(1), "task": m.group(2), "fields": fields})
    return out


def _b_decisions(decisions_path: Path, day: str) -> list[str]:
    if not decisions_path.exists():
        return []
    text = decisions_path.read_text(encoding="utf-8")
    return [
        f"决策：{m.group(2).strip()}" if m.group(2).strip() else m.group(0).strip()
        for m in B_DECISION_RE.finditer(text)
        if m.group(1) == day
    ]


def _pending_items(audit_dir: Path, day: str) -> list[str]:
    fp = audit_dir / f"pending-{day.replace('-', '')}.md"
    if not fp.exists():
        return []
    return [m.group(2).strip() for m in PENDING_RE.finditer(fp.read_text(encoding="utf-8"))]


def _token_total(entries: list[dict]) -> str:
    vals = [e["fields"].get("token 消耗", "") for e in entries]
    vals = [v for v in vals if v and "未统计" not in v]
    if not vals:
        return "未统计（待补）"
    total = 0
    for v in vals:
        m = re.search(r"(\d+)k", v)
        if m:
            total += int(m.group(1))
    return f"{total}k（来自 {len(vals)} 条日志）"


def gen_daily(audit_dir: Path, day: str, tasks_dir: Path) -> str:
    d = day.replace("-", "")
    entries = [e for e in _entries(audit_dir) if e["file"] == f"{day}.md"]
    decisions = _b_decisions(audit_dir / "decisions.md", day)
    pending = _pending_items(audit_dir, day)
    lines = [
        f"# 日报 {day}（自动生成）",
        "",
        "## 今日完成",
    ]
    if entries:
        for e in entries:
            verdict = e["fields"].get("验收结论", "")
            lines.append(f"- {e['task']}（{e['time']}）— {verdict or '待验收'}")
    else:
        lines.append("- 无任务完成")
    lines += ["", "## 今日决策（B 档）"] + (decisions or ["- 无"]) + ["", "## 待你确认（C 档）"]
    lines += pending or ["- 无"]
    lines += ["", "## 成本", f"- token 消耗：{_token_total(entries)}", f"- 待验收任务卡：{len(list(tasks_dir.glob('TASK-*.md')))} 张（blocked 计数见 registry）"]
    return "\n".join(lines) + "\n"


def gen_weekly(audit_dir: Path, registry_path: Path, day: str) -> str:
    entries = _entries(audit_dir)
    done = len({e["task"] for e in entries})
    registry = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    awaiting = len(re.findall(r"status:\s*pending_acceptance", registry))
    pending_total = sum(1 for fp in audit_dir.glob("pending-*.md"))
    weekly_section = [
        f"# 周报 {day}（自动生成）",
        "",
        "## 完成任务数",
        f"- 本周日志任务条目：{done}；registry 待验收：{awaiting}",
        "",
        "## token 消耗",
        f"- {_token_total(entries)}",
        "",
        "## C 档积压",
        f"- 待确认文件：{pending_total} 个（明细见 audit/pending-*.md）",
        "",
        "## 方向偏移预警",
        "- 无自动判定（人工核 brief 与任务卡）",
        "",
        "## 成本",
        f"- token 消耗：{_token_total(entries)}",
    ]
    return "\n".join(weekly_section) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="审计员报告生成")
    p.add_argument("kind", choices=["daily", "weekly"])
    p.add_argument("--audit-dir", type=Path, default=Path("projects/research-sop/audit"))
    p.add_argument("--tasks-dir", type=Path, default=Path("projects/research-sop/tasks"))
    p.add_argument("--registry", type=Path, default=Path("harness/registry.yaml"))
    p.add_argument("--date", default="")
    args = p.parse_args()

    day = args.date or __import__("datetime").date.today().isoformat()
    if args.kind == "daily":
        print(gen_daily(args.audit_dir, day, args.tasks_dir))
    else:
        print(gen_weekly(args.audit_dir, args.registry, day))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
