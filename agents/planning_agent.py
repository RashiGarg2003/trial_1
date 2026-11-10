"""Agent 2 – Planning: decomposes the request into an ordered analytical workflow."""
from schemas import ExecutionPlan

SYSTEM = """You are the Planning Agent. Break the structured business request into 1-5 analytical tasks that
together answer it. Each task must be answerable by ONE SQLite query. For root-cause questions plan a
progression: (1) establish the overall trend, (2) locate WHERE the change happened by drilling into
dimensions (region, category, product, segment), (3) check contributing drivers (volume, price/discount, order count).
Only reference tables that exist in the schema. Keep the plan minimal and non-redundant."""


def run(state: dict, llm, db) -> dict:
    intent = state["intent"]
    prompt = (f"DATABASE SCHEMA:\n{db.schema_text(sample_rows=0)}\n\n"
              f"STRUCTURED REQUEST:\n{intent.model_dump_json(indent=1)}\n\nORIGINAL QUESTION: {state['question']}")
    plan = llm.structured(SYSTEM, prompt, ExecutionPlan)
    known = set(db.table_names())
    for s in plan.steps:  # validate planner output against real schema
        s.tables_needed = [t for t in s.tables_needed if t in known]
    steps = "; ".join(f"{s.step_id}: {s.objective}" for s in plan.steps)
    return {"plan": plan, "current_step": 0, "retry_count": 0, "last_error": None,
            "trace": [f"[Planner] {len(plan.steps)} steps -> {steps}"]}
