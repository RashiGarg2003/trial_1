"""Offline tests: full LangGraph pipeline with a fake LLM (no API key needed)."""
import tempfile
from pathlib import Path

import pytest

import create_sample_db
from database import Database, SQLValidationError
from graph import build_graph, run_question
from schemas import *

GOOD_SQL = ("SELECT strftime('%Y-%m', o.order_date) AS month, ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)),2) AS revenue "
            "FROM orders o JOIN order_items oi ON oi.order_id=o.order_id GROUP BY month ORDER BY month")


class FakeLLM:
    def __init__(self, answerable=True):
        self.sql_calls, self.answerable = 0, answerable

    def structured(self, system, prompt, cls):
        if cls is IntentOutput:
            return IntentOutput(is_answerable=self.answerable, clarification_needed=None if self.answerable else "Which metric?",
                                question_type="trend", kpis=["revenue"], dimensions=["month"], requires_root_cause=False,
                                structured_query_requirements="monthly revenue")
        if cls is ExecutionPlan:
            return ExecutionPlan(rationale="r", steps=[PlanStep(step_id=0, objective="Monthly revenue",
                                 tables_needed=["orders", "order_items", "bogus"], expected_columns=["month", "revenue"])])
        if cls is SQLQuery:
            self.sql_calls += 1
            return SQLQuery(sql="SELECT nonexistent FROM orders" if self.sql_calls == 1 else GOOD_SQL, explanation="e")
        if cls is AnalysisOutput:
            return AnalysisOutput(trends=["up"], anomalies=[], business_drivers=["d"], key_findings=["f"],
                                  root_causes=[RootCause(cause="c", evidence="e", confidence="low")])
        if cls is ReportOutput:
            return ReportOutput(business_summary="s", key_findings=["k"], root_cause_analysis="rca",
                                recommendations=[Recommendation(action="a", rationale="r", priority="high")],
                                charts=[ChartSpec(step_id=0, chart_type="line", x="month", y=["revenue"], title="Revenue")])
        raise AssertionError(cls)


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    p = tmp_path_factory.mktemp("db") / "t.db"
    create_sample_db.build(p)
    return Database(p)


def test_sql_guardrails(db):
    for bad in ["DROP TABLE orders", "SELECT 1; DELETE FROM orders", "SELECT * FROM nope", "UPDATE orders SET order_id=1"]:
        with pytest.raises(SQLValidationError):
            db.validate_sql(bad)
    cols, rows, _ = db.execute("SELECT COUNT(*) AS n FROM orders")
    assert rows[0]["n"] > 1000


def test_full_pipeline_with_retry(db, tmp_path):
    state = run_question("monthly revenue?", build_graph(FakeLLM(), db), tmp_path)
    assert state["step_results"][0].success and state["step_results"][0].attempts == 2  # retry loop worked
    assert (Path(state["output_dir"]) / "report.md").exists()
    assert state["chart_files"] == ["chart_1.png"]
    assert "Business Summary" in state["report_markdown"]


def test_unanswerable_routes_to_clarification(db, tmp_path):
    state = run_question("hello", build_graph(FakeLLM(answerable=False), db), tmp_path)
    assert "Clarification" in state["report_markdown"] and "step_results" in state and not state["step_results"]
