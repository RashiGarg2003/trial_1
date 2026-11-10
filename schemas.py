"""Pydantic models = the structured contracts exchanged between agents."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ---- Agent 1: Intent Understanding -------------------------------------
class IntentOutput(BaseModel):
    is_answerable: bool = Field(description="False if the question is unrelated to the business data or too vague")
    clarification_needed: Optional[str] = Field(default=None, description="Question to ask the user if not answerable")
    question_type: Literal["trend", "comparison", "ranking", "performance", "root_cause", "anomaly", "summary"]
    kpis: list[str] = Field(description="Metrics requested, e.g. revenue, order count, AOV")
    dimensions: list[str] = Field(default_factory=list, description="Group-by dimensions: region, category, month ...")
    filters: list[str] = Field(default_factory=list, description="Filters, e.g. 'region = Europe'")
    time_period: Optional[str] = Field(default=None, description="Time window or comparison periods")
    requires_root_cause: bool = False
    structured_query_requirements: str = Field(description="Precise, structured description of the data needed")


# ---- Agent 2: Planning --------------------------------------------------
class PlanStep(BaseModel):
    step_id: int
    objective: str = Field(description="What this analytical task answers")
    tables_needed: list[str]
    expected_columns: list[str] = Field(description="Columns the result set should contain")


class ExecutionPlan(BaseModel):
    rationale: str
    steps: list[PlanStep] = Field(min_length=1, max_length=5)

    @field_validator("steps")
    @classmethod
    def ids_are_sequential(cls, v):
        for i, s in enumerate(v):
            s.step_id = i
        return v


# ---- Agent 3: SQL generation / execution -------------------------------
class SQLQuery(BaseModel):
    sql: str = Field(description="A single read-only SQLite SELECT statement")
    explanation: str

    @field_validator("sql")
    @classmethod
    def not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("sql must not be empty")
        return v


class StepResult(BaseModel):
    step_id: int
    objective: str
    sql: str
    attempts: int
    success: bool
    error: Optional[str] = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


# ---- Agent 4: Analysis --------------------------------------------------
class RootCause(BaseModel):
    cause: str
    evidence: str = Field(description="Numbers from the data that support this cause")
    confidence: Literal["high", "medium", "low"]


class AnalysisOutput(BaseModel):
    trends: list[str]
    anomalies: list[str]
    business_drivers: list[str]
    root_causes: list[RootCause]
    key_findings: list[str]


# ---- Agent 5: Reporting -------------------------------------------------
class ChartSpec(BaseModel):
    step_id: int = Field(description="Which step's result set to plot")
    chart_type: Literal["line", "bar", "barh", "pie"]
    x: str
    y: list[str]
    title: str
    xlabel: str = ""
    ylabel: str = ""


class Recommendation(BaseModel):
    action: str
    rationale: str
    priority: Literal["high", "medium", "low"]


class ReportOutput(BaseModel):
    business_summary: str
    key_findings: list[str]
    root_cause_analysis: str
    recommendations: list[Recommendation]
    charts: list[ChartSpec] = Field(default_factory=list, max_length=4)
