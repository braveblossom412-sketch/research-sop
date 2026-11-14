"""TASK-006 审计员报告生成测试（标准库 + pytest，零网络依赖）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from audit.report import gen_daily, gen_weekly, _token_total  # noqa: E402


def _make_audit(tmp: Path) -> tuple[Path, Path, Path]:
    """构造: audit_dir / (空 tasks_dir + registry)。返回 (audit, tasks, registry)。"""
    audit = tmp / "audit"
    tasks = tmp / "tasks"
    audit.mkdir()
    tasks.mkdir()
    registry = tmp / "registry.yaml"
    registry.write_text("tasks:\n  - id: TASK-001\n    status: pending_acceptance\n", encoding="utf-8")
    return audit, tasks, registry


def _log_entry(path: Path, task: str, extra: str = "", token: str = "未统计（待补）"):
    text = (
        f"## [10:00] {task}\n"
        f"- 执行工具：TRAE\n"
        f"- 测试结果：通过 1 / 失败 0\n"
        f"- token 消耗：{token}\n"
        f"- 验收结论：L1✓ L2✓ L3✓ L4 待验 → 待验收\n{extra}"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def test_empty_audit_dir_no_error(tmp_path):
    audit, tasks, _ = _make_audit(tmp_path)
    report = gen_daily(audit, "2026-11-13", tasks)
    assert "无任务完成" in report
    assert "## 今日完成" in report and "## 成本" in report


def test_daily_three_sections_with_entries(tmp_path):
    audit, tasks, _ = _make_audit(tmp_path)
    _log_entry(audit / "2026-11-13.md", "TASK-006")
    _log_entry(audit / "2026-11-13.md", "TASK-005")
    report = gen_daily(audit, "2026-11-13", tasks)
    assert "## 今日完成" in report and "## 今日决策（B 档）" in report and "## 待你确认（C 档）" in report
    assert "TASK-006" in report and "TASK-005" in report


def test_weekly_four_sections_and_cost(tmp_path):
    audit, _, registry = _make_audit(tmp_path)
    _log_entry(audit / "2026-11-13.md", "TASK-006", token="20k")
    report = gen_weekly(audit, registry, "2026-11-13")
    for sec in ["## 完成任务数", "## token 消耗", "## C 档积压", "## 方向偏移预警", "## 成本"]:
        assert sec in report
    assert "20k" in report


def test_missing_token_flagged_not_complete(tmp_path):
    audit, tasks, _ = _make_audit(tmp_path)
    _log_entry(audit / "2026-11-13.md", "TASK-006", token="未统计（待补）")
    report = gen_daily(audit, "2026-11-13", tasks)
    assert "未统计（待补）" in report


def test_b_decision_collected_same_day(tmp_path):
    audit, tasks, _ = _make_audit(tmp_path)
    decisions = audit / "decisions.md"
    decisions.write_text(
        "## [2026-11-13] [档位B] 决策：xxx\n- 理由：yyy\n- 影响：zzz\n", encoding="utf-8"
    )
    report = gen_daily(audit, "2026-11-13", tasks)
    assert "决策：xxx" in report


def test_l3_same_input_same_output(tmp_path):
    audit, tasks, _ = _make_audit(tmp_path)
    _log_entry(audit / "2026-11-13.md", "TASK-006", token="20k")
    assert gen_daily(audit, "2026-11-13", tasks) == gen_daily(audit, "2026-11-13", tasks)


def test_token_total_aggregates(tmp_path):
    entries = [
        {"fields": {"token 消耗": "20k"}},
        {"fields": {"token 消耗": "30k"}},
        {"fields": {"token 消耗": "未统计（待补）"}},
    ]
    assert _token_total(entries) == "50k（来自 2 条日志）"
