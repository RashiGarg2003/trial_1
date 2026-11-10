"""Agent 1 – Intent Understanding: question -> structured query requirements."""
from schemas import IntentOutput

SYSTEM = """You are the Intent Understanding Agent of a business analytics platform.
Convert the user's business question into structured analytical requirements: KPIs/metrics, dimensions,
filters, time periods, and whether root-cause analysis is needed. Use only concepts that can be answered
from the provided database schema. If the question cannot be answered from this data or is too vague,
set is_answerable=false and write a clarification question."""


def run(state: dict, llm, db) -> dict:
    prompt = f"DATABASE SCHEMA:\n{db.schema_text(sample_rows=1)}\n\nUSER QUESTION: {state['question']}"
    intent = llm.structured(SYSTEM, prompt, IntentOutput)
    return {"intent": intent, "trace": [f"[Intent] type={intent.question_type}, kpis={intent.kpis}, "
                                        f"dims={intent.dimensions}, answerable={intent.is_answerable}"]}
