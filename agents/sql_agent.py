"""Agent 3 – SQL Generation: text-to-SQL, schema validation, execution, retry/self-correction.

Implemented as two graph nodes (generate / execute) so the retry loop is visible in the LangGraph.
"""
from schemas import SQLQuery, StepResult
from config import MAX_SQL_RETRIES
from database import SQLValidationError

SYSTEM = """You are the SQL Generation Agent. Write ONE read-only SQLite SELECT query for the given task.
Rules: use only tables/columns in the schema; SQLite syntax (strftime for dates, no DATE_TRUNC);
revenue = quantity * unit_price * (1 - discount) from order_items; join orders -> customers for region;
alias every computed column with a clear name; round money to 2 decimals; use ORDER BY; avoid SELECT *;
no semicolons or comments; use LIMIT <= 100 for rankings. Months: strftime('%Y-%m', order_date).
If a previous attempt failed, fix the exact error shown."""


def generate(state: dict, llm, db) -> dict:
    step = state["plan"].steps[state["current_step"]]
    prev = ""
    for r in state.get("step_results", []):
        if r.success:
            prev += f"\nStep {r.step_id} ({r.objective}) columns={r.columns} first rows={r.rows[:5]}"
    err = state.get("last_error")
    prompt = (f"DATABASE SCHEMA:\n{db.schema_text(sample_rows=2)}\n\n"
              f"OVERALL QUESTION: {state['question']}\nCURRENT TASK (step {step.step_id}): {step.objective}\n"
              f"Expected columns: {step.expected_columns}\nTables: {step.tables_needed}\n"
              f"RESULTS SO FAR:{prev or ' none'}\n")
    if err:
        prompt += f"\nPREVIOUS SQL FAILED:\n{state['current_sql']}\nERROR: {err}\nReturn a corrected query."
    q = llm.structured(SYSTEM, prompt, SQLQuery)
    return {"current_sql": q.sql, "trace": [f"[SQL-Gen] step {step.step_id} attempt {state.get('retry_count', 0)+1}: {q.sql}"]}


def execute(state: dict, llm, db) -> dict:
    idx, step = state["current_step"], state["plan"].steps[state["current_step"]]
    attempts = state.get("retry_count", 0) + 1
    try:
        cols, rows, n = db.execute(state["current_sql"])
        if not rows:
            raise SQLValidationError("Query returned zero rows; check filters / date formats / joins.")
        res = StepResult(step_id=step.step_id, objective=step.objective, sql=state["current_sql"], attempts=attempts,
                         success=True, columns=cols, rows=rows, row_count=n)
        return {"step_results": [res], "current_step": idx + 1, "retry_count": 0, "last_error": None,
                "step_done": True, "trace": [f"[SQL-Exec] step {idx} OK ({n} rows)"]}
    except SQLValidationError as e:
        if attempts >= MAX_SQL_RETRIES:
            res = StepResult(step_id=step.step_id, objective=step.objective, sql=state["current_sql"],
                             attempts=attempts, success=False, error=str(e))
            return {"step_results": [res], "current_step": idx + 1, "retry_count": 0, "last_error": None,
                    "step_done": True, "trace": [f"[SQL-Exec] step {idx} FAILED after {attempts} attempts: {e}"]}
        return {"retry_count": attempts, "last_error": str(e), "step_done": False,
                "trace": [f"[SQL-Exec] step {idx} error -> retrying: {e}"]}
