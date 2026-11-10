"""Agent 4 – Analysis: deterministic statistics (pandas) + LLM interpretation (trends, anomalies, root cause)."""
import json
import re

import pandas as pd

from schemas import AnalysisOutput

SYSTEM = """You are the Analysis Agent, a senior business data analyst. You receive query results plus
pre-computed statistics. Identify trends, anomalies, business drivers and ROOT CAUSES. Rules: ground every
statement in numbers actually present in the data; never invent figures; distinguish correlation from proven
causation and set confidence accordingly; for root cause, drill from the overall change down to the segment
(region/category/product) and the mechanism (volume vs price/discount vs order count) that explains most of it."""

PERIOD_COL = re.compile(r"(month|date|period|year|quarter|week|day)", re.I)


def profile(res) -> dict:
    """Deterministic statistics so the LLM reasons over verified numbers."""
    df = pd.DataFrame(res.rows)
    out = {"step_id": res.step_id, "objective": res.objective, "rows": len(df), "columns": res.columns}
    num = df.select_dtypes("number").columns.tolist()
    label = next((c for c in df.columns if c not in num), df.columns[0])
    stats = {}
    for c in num:
        s = df[c].astype(float)
        info = {"min": round(s.min(), 2), "max": round(s.max(), 2), "mean": round(s.mean(), 2), "sum": round(s.sum(), 2)}
        if len(s) >= 4 and s.std() > 0:
            z = (s - s.mean()) / s.std()
            info["outliers"] = [{str(label): str(df.loc[i, label]), c: round(float(s[i]), 2), "z": round(float(z[i]), 2)}
                                for i in z.index if abs(z[i]) > 2][:5]
        if PERIOD_COL.search(str(label)) and len(s) >= 3:
            ch = s.pct_change().replace([float("inf")], float("nan")) * 100
            info["first_to_last_pct"] = round((s.iloc[-1] / s.iloc[0] - 1) * 100, 1) if s.iloc[0] else None
            info["largest_drop"] = {"period": str(df.loc[ch.idxmin(), label]), "pct": round(float(ch.min()), 1)} if ch.notna().any() else None
            info["largest_rise"] = {"period": str(df.loc[ch.idxmax(), label]), "pct": round(float(ch.max()), 1)} if ch.notna().any() else None
        stats[c] = info
    out["numeric_stats"] = stats
    return out


def run(state: dict, llm, db) -> dict:
    ok = [r for r in state["step_results"] if r.success]
    blocks = []
    for r in ok:
        blocks.append({"profile": profile(r), "data": r.rows[:60]})
    prompt = (f"BUSINESS QUESTION: {state['question']}\n"
              f"INTENT: {state['intent'].model_dump_json()}\n\n"
              f"RESULTS (statistics + up to 60 rows each):\n{json.dumps(blocks, default=str)}")
    analysis = llm.structured(SYSTEM, prompt, AnalysisOutput)
    return {"analysis": analysis, "trace": [f"[Analysis] {len(analysis.key_findings)} findings, "
                                            f"{len(analysis.root_causes)} root causes, {len(analysis.anomalies)} anomalies"]}
