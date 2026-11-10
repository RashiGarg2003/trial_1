"""LangGraph orchestration of the 5 specialised agents (with SQL retry loop + conditional routing)."""
import operator
import re
from datetime import datetime
from functools import partial
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

import config
from agents import analysis_agent, intent_agent, planning_agent, reporting_agent, sql_agent
from database import Database
from schemas import AnalysisOutput, ExecutionPlan, IntentOutput, ReportOutput, StepResult


class GraphState(TypedDict, total=False):
    question: str
    output_dir: str
    intent: IntentOutput
    plan: ExecutionPlan
    current_step: int
    current_sql: str
    retry_count: int
    last_error: Optional[str]
    step_done: bool
    step_results: Annotated[list[StepResult], operator.add]   # appended by SQL agent
    analysis: AnalysisOutput
    report: ReportOutput
    report_markdown: str
    chart_files: list[str]
    trace: Annotated[list[str], operator.add]                 # human-readable agent log


def _clarify(state: dict, llm, db) -> dict:
    msg = state["intent"].clarification_needed or "Please rephrase your question about the business data."
    md = f"# Clarification needed\n\n{msg}\n"
    return {"report_markdown": md, "trace": [f"[Clarify] question not answerable: {msg}"]}


def route_after_intent(state: dict) -> str:
    return "planner" if state["intent"].is_answerable else "clarify"


def route_after_execute(state: dict) -> str:
    if not state.get("step_done"):
        return "sql_generate"                                  # retry with error feedback
    if state["current_step"] < len(state["plan"].steps):
        return "sql_generate"                                  # next planned step
    return "analysis" if any(r.success for r in state["step_results"]) else "report"


def build_graph(llm=None, db: Database | None = None):
    if llm is None:
        from llm import GeminiLLM
        llm = GeminiLLM()
    db = db or Database()
    bind = lambda fn: partial(fn, llm=llm, db=db)

    g = StateGraph(GraphState)
    g.add_node("intent", bind(intent_agent.run))
    g.add_node("clarify", bind(_clarify))
    g.add_node("planner", bind(planning_agent.run))
    g.add_node("sql_generate", bind(sql_agent.generate))
    g.add_node("sql_execute", bind(sql_agent.execute))
    g.add_node("analysis", bind(analysis_agent.run))
    g.add_node("report", bind(reporting_agent.run))

    g.add_edge(START, "intent")
    g.add_conditional_edges("intent", route_after_intent, {"planner": "planner", "clarify": "clarify"})
    g.add_edge("clarify", END)
    g.add_edge("planner", "sql_generate")
    g.add_edge("sql_generate", "sql_execute")
    g.add_conditional_edges("sql_execute", route_after_execute,
                            {"sql_generate": "sql_generate", "analysis": "analysis", "report": "report"})
    g.add_edge("analysis", "report")
    g.add_edge("report", END)
    return g.compile()


def run_question(question: str, graph=None, out_root=None) -> dict:
    graph = graph or build_graph()
    slug = re.sub(r"[^a-z0-9]+", "_", question.lower())[:40].strip("_")
    out_dir = (out_root or config.OUTPUT_DIR) / f"{datetime.now():%Y%m%d_%H%M%S}_{slug}"
    return graph.invoke({"question": question, "output_dir": str(out_dir), "step_results": [], "trace": [],
                         "retry_count": 0, "current_step": 0}, {"recursion_limit": 60})
