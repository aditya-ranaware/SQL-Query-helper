from app.graph.nodes import explain, run_sql, write_sql
from app.services.database import get_schema_text

state = {"question": "Which product earned the most revenue?", "schema": get_schema_text(), "attempts": 0}

for step in (write_sql, run_sql, explain):
    state.update(step(state))
    print(f"--- {step.__name__} ---")

print("SQL   :", state["sql"])
print("ROWS  :", state["result"]["rows"][:3])
print("ANSWER:", state["answer"])