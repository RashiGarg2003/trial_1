"""Generates docs/architecture.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(13, 10))
ax.set_xlim(-0.9, 13); ax.set_ylim(0, 10); ax.axis("off")

def box(x, y, w, h, text, fc, ec="#333", fs=10, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")

def arrow(x1, y1, x2, y2, text="", style="-|>", color="#333", ls="-", rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.5, ls=ls, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + 0.1, (y1 + y2) / 2 + 0.05, text, fontsize=8, color=color)

ax.text(6.5, 9.7, "Multi-Agent Data Analytics System – Architecture (LangGraph)", ha="center", fontsize=15, fontweight="bold")

box(0.3, 8.6, 3.2, 0.7, "Business User\n(natural-language question)", "#e8eaf6", bold=True)
box(0.3, 7.2, 3.2, 0.9, "LangGraph Orchestrator\nshared GraphState + routing", "#fff3e0", bold=True)
box(0.3, 5.9, 3.2, 0.9, "Agent 1: Intent Understanding\nKPIs · dimensions · filters · time", "#c8e6c9")
box(0.3, 4.6, 3.2, 0.9, "Agent 2: Planning\ntask decomposition · workflow", "#c8e6c9")
box(0.3, 3.3, 3.2, 0.9, "Agent 3a: SQL Generation\ntext-to-SQL (schema-aware)", "#c8e6c9")
box(0.3, 2.0, 3.2, 0.9, "Agent 3b: SQL Validation/Execution\nsafety · retry · self-correction", "#c8e6c9")
box(0.3, 0.7, 3.2, 0.9, "Agent 4: Analysis\ntrends · anomalies · root cause", "#c8e6c9")

box(5.0, 0.7, 3.2, 0.9, "Agent 5: Reporting\nsummary · charts · recommendations", "#c8e6c9")
box(5.0, 2.0, 3.2, 0.9, "SQLite Database\n(read-only connection)", "#ffe0b2", bold=True)
box(5.0, 4.0, 3.2, 1.2, "Pydantic Validation Layer\nIntentOutput · ExecutionPlan · SQLQuery\nStepResult · AnalysisOutput · ReportOutput", "#e1bee7", fs=9, bold=True)
box(5.0, 6.1, 3.2, 1.0, "Google Gemini LLM\nstructured JSON outputs\n(used by agents 1,2,3a,4,5)", "#bbdefb", bold=True)

box(9.6, 0.7, 3.1, 1.6, "Final Output\n• Business summary\n• Key findings\n• Visualizations (PNG)\n• Root cause analysis\n• Recommendations", "#fff9c4", fs=9, bold=True)
box(9.6, 3.3, 3.1, 1.1, "Guardrails\nSELECT-only · no DDL/DML\nschema check (EXPLAIN)\nrow cap · max retries", "#ffcdd2", fs=9)
box(9.6, 5.0, 3.1, 1.1, "Clarification path\nif question unanswerable\n→ ask user, END", "#f5f5f5", fs=9)

# vertical flow
for y1, y2 in [(8.6, 8.1), (7.2, 6.8), (5.9, 5.5), (4.6, 4.2), (3.3, 2.9), (2.0, 1.6)]:
    arrow(1.9, y1, 1.9, y2)
arrow(3.5, 1.15, 5.0, 1.15)
arrow(8.2, 1.15, 9.6, 1.15)
# retry loop
arrow(0.3, 2.45, -0.1, 2.45, style="-", color="#c62828")
arrow(-0.1, 2.45, -0.1, 3.75, style="-", color="#c62828")
arrow(-0.1, 3.75, 0.3, 3.75, color="#c62828")
ax.text(-0.85, 3.05, "retry with\nerror feedback", fontsize=8, color="#c62828")
# next step loop
arrow(3.5, 2.45, 4.0, 2.45, style="-", color="#1565c0")
arrow(4.0, 2.45, 4.0, 3.75, style="-", color="#1565c0")
arrow(4.0, 3.75, 3.5, 3.75, "next plan step", color="#1565c0")
# DB
arrow(3.5, 2.3, 5.0, 2.3, "SELECT", color="#e65100")
arrow(5.0, 2.1, 3.5, 2.1, "rows", color="#e65100")
# Gemini to agents (dashed)
for y in [6.35, 5.05, 3.75]:
    arrow(5.0, 6.6 if y > 5 else 6.3, 3.5, y, style="<|-|>", color="#1565c0", ls="--")
arrow(5.0, 6.2, 3.5, 1.3, style="<|-|>", color="#1565c0", ls="--", rad=-0.15)
arrow(6.6, 6.1, 6.6, 5.2, style="<|-|>", color="#6a1b9a", ls="--")
ax.text(6.7, 5.55, "validate", fontsize=8, color="#6a1b9a")
arrow(8.2, 6.7, 8.2, 1.5, style="<|-|>", color="#1565c0", ls="--", rad=-0.25)

ax.text(6.5, 0.15, "Solid = data flow · Dashed blue = LLM calls · Purple = Pydantic validation · Red = guardrails / retry loop",
        ha="center", fontsize=9, style="italic")
plt.savefig("docs/architecture.png", dpi=150, bbox_inches="tight", facecolor="white")
