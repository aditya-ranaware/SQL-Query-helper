import sys

from app.graph.workflow import ask
from app.services.dataset import from_schema_text, sample_dataset

NAMES_ONLY = """customers: id, name, city
orders: id, customer_id, order_date, status
products: id, name, price"""

dataset = from_schema_text(NAMES_ONLY) if "--names-only" in sys.argv else sample_dataset()
words = [a for a in sys.argv[1:] if not a.startswith("--")]
request = " ".join(words) or "Show the 3 most expensive products"

state = ask(request, dataset)

print("PATH       :", " > ".join(s["node"] for s in state["steps"]))
print("STATUS     :", state["status"], "| attempts:", state["attempts"])

for s in state["steps"]:
    if s["node"] == "check" and not s["ok"]:
        print("A REJECTED TRY, the AI fixed it after seeing:", s["error"])

if state["status"] == "success":
    check = state["check"]
    print("\nQUERY      :\n" + check.sql)
    for w in check.warnings:
        print(f"WARNING    : [{w['level']}] {w['text']}")
    if check.check_query:
        print("\nCHECK FIRST (shows the rows that match):\n" + check.check_query)
    p = state["preview"]
    if p is None:
        print("\nPREVIEW    : none (no data was uploaded)")
    elif not p["available"]:
        print("\nPREVIEW    : unavailable,", p["reason"])
    elif p["kind"] == "SELECT":
        print("\nPREVIEW    :", p["columns"], p["rows"][:3])
    else:
        print(f"\nPREVIEW    : {p['kind']} would affect {p['affected']} rows of {p['table_rows']} in '{p['table']}'")
    print("\nEXPLANATION:", state["explanation"])
else:
    print("\nMESSAGE    :", state["answer"])