# Final Project Report – Multi-Agent Data Analytics System
**Name / ID:** ____________  **Course:** ____________  **Date:** ____________

## 1. Introduction and business problem
Business users need answers on sales, customers and revenue but traditional platforms require SQL and analyst time. This project builds an agentic AI platform that turns a natural-language question into explainable insights.

## 2. Technology stack
LangGraph (orchestration) · Google Gemini (LLM) · SQLite (database) · Pydantic (validation) · pandas / matplotlib (analysis, charts).

## 3. System architecture
Insert `docs/architecture.png` and describe the flow (see `docs/architecture.md`).

## 4. Agent design
Describe each of the 5 agents: responsibilities, prompt strategy, Pydantic output model (table in `docs/architecture.md`).

## 5. Multi-agent collaboration
State passing through `GraphState`, conditional routing (clarification path), SQL retry loop, step loop, validation at each hand-off.

## 6. Dataset
Synthetic Northwind-style database (`create_sample_db.py`): categories, products, customers, orders, order_items; 2023-2024; includes a planted Q4-2024 Europe/Electronics decline to test root-cause analysis. Replace with Northwind / AdventureWorks / UCI Online Retail by setting `DB_PATH`.

## 7. Sample questions and outputs
Paste results from `sample_outputs/` (generated with `python main.py --samples`).

## 8. Testing and validation
Offline pytest suite (fake LLM): SQL guardrails, retry loop, clarification routing, report + chart generation.

## 9. Limitations and future work
LLM may mis-specify SQL on complex schemas (mitigated by retries); no caching; add memory, human-in-the-loop approval, more chart types, a web UI (Streamlit).

## 10. Conclusion
