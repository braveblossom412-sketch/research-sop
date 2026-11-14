"""演示批次端到端跑批：ingest → dedup → matrix → verify(离线) → 结果总览 HTML。

用法（在 research-sop 目录，PYTHONPATH=src）:
  python -m tools.run_demo

产物落在 outputs/demo-batch/，不覆盖既有库存与历史产物。
本批次为虚构演示样例，非验收基准；verify 离线运行，全部标 pending。
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from literature.ingest import ingest
from literature.dedup import dedup
from literature.matrix import build_rows, write_csv, write_xlsx, COLUMNS
from literature.verify import verify_row, summarize, write_summary

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT = ROOT / "golden-set" / "demo-batch" / "papers.json"
OUT = ROOT / "outputs" / "demo-batch"
RAW = OUT / "raw"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    # 1. 入库（校验 + 留档 + 结构化落盘）
    ingest_report = ingest(INPUT, RAW, OUT / "lit.jsonl")
    records = _read_jsonl(OUT / "lit.jsonl")

    # 2. 去重（标记 + 分流，不物理删除）
    deduped, duplicates = dedup(records)
    (OUT / "deduped.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in deduped) + "\n", encoding="utf-8")
    (OUT / "duplicates.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in duplicates) + "\n", encoding="utf-8")

    # 3. 对比矩阵 CSV + XLSX
    rows = build_rows(deduped)
    write_csv(OUT / "lit-matrix.csv", rows)
    write_xlsx(OUT / "lit-matrix.xlsx", rows)

    # 4. 引用校验（离线：占位/缺 DOI 一律 pending，不联网）
    results = [verify_row(r.get("doi"), r.get("title")) for r in deduped]
    (OUT / "verification.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n", encoding="utf-8")
    stats = summarize(results)
    write_summary(OUT / "verification-summary.md", stats)

    # 5. 结果总览 HTML（内联数据，file:// 可直接打开）
    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ingest": ingest_report,
        "dedup": {"input": len(records), "deduped": len(deduped), "duplicates": len(duplicates)},
        "matrix": {"rows": len(rows), "columns": COLUMNS},
        "verify": stats,
        "duplicates": duplicates,
        "rows": rows,
    }
    (OUT / "overview-data.json").write_text(
        json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_html(OUT / "结果总览.html", overview)

    print(json.dumps({
        "out_dir": str(OUT),
        "ingest": {"total": ingest_report["total"], "imported": ingest_report["imported"],
                   "rejected": ingest_report["rejected"]},
        "dedup": overview["dedup"],
        "verify": stats,
        "html": str(OUT / "结果总览.html"),
    }, ensure_ascii=False, indent=2))
    return 0


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _write_html(path: Path, ov: dict) -> None:
    ing = ov["ingest"]
    vf = ov["verify"]
    dup_rows = "".join(
        f"<tr><td>{_esc(d['kept_id'])}</td><td>{_esc(d['dropped_id'])}</td>"
        f"<td>{_esc(d['match_reason'])}</td><td>{_esc(d['score'])}</td></tr>"
        for d in ov["duplicates"]) or "<tr><td colspan='4'>无重复条目</td></tr>"

    head = "".join(f"<th>{_esc(c)}</th>" for c in COLUMNS)
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>"
        for row in ov["rows"])

    rejected = ing.get("errors", [])
    rej_html = "".join(
        f"<li>第 {e['index']} 条：{_esc('；'.join(e['errors']))}</li>" for e in rejected
    ) or "<li>无</li>"

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>research-sop 演示批次结果总览</title>
<style>
:root{{--bg:#f5f6f8;--card:#fff;--line:#e3e6ea;--ink:#1c2330;--sub:#5b6572;--accent:#2f5d8a;--ok:#1f8a5b;--warn:#b8860b;--bad:#b3402f;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.55}}
.wrap{{max-width:1080px;margin:0 auto;padding:24px 18px 60px}}
h1{{font-size:22px;margin:0 0 6px}}
.note{{background:#fff7e6;border:1px solid #f0d9a8;color:#7a5a10;padding:10px 14px;border-radius:8px;font-size:14px;margin:12px 0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.card .num{{font-size:26px;font-weight:700}}
.card .lab{{color:var(--sub);font-size:13px;margin-top:2px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:16px 0}}
h2{{font-size:16px;margin:0 0 12px}}
table{{border-collapse:collapse;width:100%;font-size:13px;table-layout:fixed}}
th,td{{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;word-break:break-word}}
th{{color:var(--sub);font-weight:600}}
.muted{{color:var(--sub);font-size:13px}}
.tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px}}
.pending{{background:#fdeecd;color:var(--warn)}}
ul{{margin:6px 0;padding-left:20px}}
</style>
</head>
<body>
<div class="wrap">
  <h1>research-sop 演示批次 · 结果总览</h1>
  <div class="note">本批次为<b>虚构演示样例</b>，仅用于跑通管线、查看产物形态；来源/DOI 均为占位，引用校验离线运行，全部标「待核实」，<b>不是验收基准</b>。生成时间：{_esc(ov['generated_at'])}</div>

  <div class="cards">
    <div class="card"><div class="num">{ing['total']}</div><div class="lab">提交条目</div></div>
    <div class="card"><div class="num" style="color:var(--ok)">{ing['imported']}</div><div class="lab">入库成功</div></div>
    <div class="card"><div class="num" style="color:var(--bad)">{ing['rejected']}</div><div class="lab">校验拒绝</div></div>
    <div class="card"><div class="num">{ov['dedup']['deduped']}</div><div class="lab">去重后保留</div></div>
    <div class="card"><div class="num" style="color:var(--warn)">{ov['dedup']['duplicates']}</div><div class="lab">标记重复</div></div>
    <div class="card"><div class="num">{vf['total']}</div><div class="lab">校验条目 / 通过率 {vf['pass_rate']*100:.1f}%</div></div>
  </div>

  <section>
    <h2>校验拒绝明细</h2>
    <ul>{rej_html}</ul>
  </section>

  <section>
    <h2>去重分流</h2>
    <table><thead><tr><th>保留条目</th><th>重复条目</th><th>匹配理由</th><th>相似度</th></tr></thead>
    <tbody>{dup_rows}</tbody></table>
  </section>

  <section>
    <h2>对比矩阵（{ov['matrix']['rows']} 行 × {ov['matrix']['columns']} 列）</h2>
    <p class="muted">方法 / 样本量 / 可复现性等 schema 未定义字段统一标「待核实」，未编造。</p>
    <div style="overflow-x:auto"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>
  </section>

  <section>
    <h2>引用可核性校验（离线）</h2>
    <p class="muted">通过 {vf['ok']} · 失败 {vf['failed']} · 待核实 {vf['pending']} · 通过率 {vf['pass_rate']*100:.1f}%。联网校验需单独授权后开启。</p>
  </section>
</div>
</body>
</html>"""
    path.write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
