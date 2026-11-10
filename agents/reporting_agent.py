"""Agent 5 – Reporting: business summary, key findings, visualizations, root cause, recommendations."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from schemas import ChartSpec, ReportOutput

SYSTEM = """You are the Reporting Agent writing for senior executives. Use ONLY the analysis and data provided.
Write a concise business summary (3-5 sentences, lead with the answer), key findings with concrete numbers,
a root cause analysis narrative, and 3-5 specific, actionable recommendations with priority.
Also choose 1-3 charts that best support the story. For each chart give step_id and EXACT column names
(x and y) from that step's columns."""


def _render(spec: ChartSpec, results, out_dir: Path, n: int) -> str | None:
    res = next((r for r in results if r.success and r.step_id == spec.step_id), None)
    if not res or spec.x not in res.columns or any(c not in res.columns for c in spec.y):
        return None
    df = pd.DataFrame(res.rows)
    if len(df) > 30 and spec.chart_type != "line":
        df = df.head(30)
    fig, ax = plt.subplots(figsize=(9, 5))
    if spec.chart_type == "line":
        for c in spec.y:
            ax.plot(df[spec.x].astype(str), df[c], marker="o", label=c)
        plt.xticks(rotation=60, ha="right")
    elif spec.chart_type == "bar":
        df.set_index(spec.x)[spec.y].plot(kind="bar", ax=ax)
        plt.xticks(rotation=45, ha="right")
    elif spec.chart_type == "barh":
        df.set_index(spec.x)[spec.y].plot(kind="barh", ax=ax)
    else:
        ax.pie(df[spec.y[0]], labels=df[spec.x].astype(str), autopct="%1.1f%%")
    ax.set_title(spec.title)
    if spec.chart_type != "pie":
        ax.set_xlabel(spec.xlabel or spec.x)
        ax.set_ylabel(spec.ylabel or ", ".join(spec.y))
        ax.grid(alpha=0.3)
        if len(spec.y) > 1:
            ax.legend()
    fig.tight_layout()
    path = out_dir / f"chart_{n}.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path.name


def _fallback_chart(results) -> ChartSpec | None:
    for r in results:
        if r.success and len(r.columns) >= 2 and r.rows:
            df = pd.DataFrame(r.rows)
            num = df.select_dtypes("number").columns.tolist()
            lab = [c for c in df.columns if c not in num]
            if num and lab:
                return ChartSpec(step_id=r.step_id, chart_type="bar", x=lab[0], y=[num[0]], title=r.objective)
    return None


def to_markdown(question, intent, plan, results, analysis, report, chart_files) -> str:
    md = [f"# Business Analytics Report\n\n**Question:** {question}\n", "## Business Summary\n", report.business_summary + "\n",
          "## Key Findings\n"] + [f"- {f}" for f in report.key_findings]
    if chart_files:
        md.append("\n## Visualizations\n")
        md += [f"![{t}]({f})\n" for f, t in chart_files]
    md += ["\n## Root Cause Analysis\n", report.root_cause_analysis + "\n"]
    if analysis and analysis.root_causes:
        md += [f"- **{rc.cause}** (confidence: {rc.confidence}) — {rc.evidence}" for rc in analysis.root_causes]
    md += ["\n## Actionable Recommendations\n"]
    md += [f"{i}. **[{r.priority.upper()}]** {r.action} — _{r.rationale}_" for i, r in enumerate(report.recommendations, 1)]
    md += ["\n## Appendix: Execution Plan & SQL\n"]
    for r in results:
        status = "OK" if r.success else f"FAILED ({r.error})"
        md.append(f"**Step {r.step_id}: {r.objective}** — {status}, attempts: {r.attempts}\n```sql\n{r.sql}\n```")
    return "\n".join(md)


def run(state: dict, llm, db) -> dict:
    out_dir: Path = Path(state["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    results, analysis = state.get("step_results", []), state.get("analysis")

    if analysis is None:  # nothing could be queried -> honest failure report
        errs = "; ".join(f"step {r.step_id}: {r.error}" for r in results if not r.success)
        md = f"# Business Analytics Report\n\n**Question:** {state['question']}\n\nThe system could not retrieve data. {errs}\n"
        (out_dir / "report.md").write_text(md, encoding="utf-8")
        return {"report_markdown": md, "trace": ["[Report] no data available – failure report written"]}

    prompt = (f"QUESTION: {state['question']}\n\nANALYSIS:\n{analysis.model_dump_json(indent=1)}\n\n"
              "AVAILABLE RESULT SETS:\n" + json.dumps(
                  [{"step_id": r.step_id, "objective": r.objective, "columns": r.columns, "sample_rows": r.rows[:5]}
                   for r in results if r.success], default=str))
    report = llm.structured(SYSTEM, prompt, ReportOutput)

    specs = list(report.charts) or ([c] if (c := _fallback_chart(results)) else [])
    chart_files = []
    for i, spec in enumerate(specs, 1):
        f = _render(spec, results, out_dir, i)
        if f:
            chart_files.append((f, spec.title))
    if not chart_files and (fb := _fallback_chart(results)):
        f = _render(fb, results, out_dir, 1)
        if f:
            chart_files.append((f, fb.title))

    md = to_markdown(state["question"], state["intent"], state["plan"], results, analysis, report, chart_files)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps(
        {"question": state["question"], "intent": state["intent"].model_dump(), "plan": state["plan"].model_dump(),
         "analysis": analysis.model_dump(), "report": report.model_dump(),
         "steps": [r.model_dump() for r in results], "trace": state.get("trace", [])}, indent=2, default=str), encoding="utf-8")
    return {"report": report, "report_markdown": md, "chart_files": [f for f, _ in chart_files],
            "trace": [f"[Report] report.md written with {len(chart_files)} chart(s) -> {out_dir}"]}
