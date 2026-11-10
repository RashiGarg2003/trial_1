# Demonstration Video Script (~5 min)
1. (0:00) Problem: business users cannot write SQL; show the assignment goal.
2. (0:30) Show `docs/architecture.png`; name the 5 agents and the LangGraph retry loop.
3. (1:15) Terminal: `python create_sample_db.py`, then `python main.py -v "Why did Europe's Electronics sales drop in the last quarter of 2024?"`
4. (1:45) Walk through the agent trace: intent -> plan -> SQL (point out a retry if one happens) -> analysis -> report.
5. (3:00) Open `outputs/<run>/report.md`: summary, findings, charts, root cause, recommendations.
6. (4:00) Show guardrails: ask "Delete all orders" -> blocked / not answerable.
7. (4:30) Show `pytest` passing and the sample outputs folder. Wrap up.
