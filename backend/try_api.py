import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get(path):
    with urllib.request.urlopen(BASE + path) as response:
        return json.loads(response.read())


names_only = "--names-only" in sys.argv
dataset_id = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--dataset=")), None)
words = [a for a in sys.argv[1:] if not a.startswith("--")]
request = " ".join(words) or "Show the 3 most expensive products"

if dataset_id:        # use data you uploaded earlier, for example through http://127.0.0.1:8000/docs
    dataset = get(f"/dataset/{dataset_id}")
elif names_only:
    dataset = post("/dataset/schema", {"text": "customers: id, name, city\norders: id, customer_id, order_date, status\nproducts: id, name, price"})
else:
    dataset = post("/dataset/sample", {})
print("DATA   :", [(t["name"], t["rows"]) for t in dataset["tables"]], "| id:", dataset["id"])
print("ASKING :", request, "\n")

req = urllib.request.Request(
    BASE + "/ask/stream",
    data=json.dumps({"dataset_id": dataset["id"], "request": request}).encode(),
    headers={"Content-Type": "application/json"}, method="POST",
)
start = time.time()
with urllib.request.urlopen(req) as response:
    for raw in response:
        line = raw.decode().strip()
        if not line.startswith("data: "):
            continue
        event = json.loads(line[6:])
        seconds = f"+{time.time() - start:.1f}s"
        if event["type"] == "step":
            step = event["step"]
            detail = step.get("sql") or step.get("error") or step.get("unanswerable") or step.get("needs_info") or ""
            print(seconds, step["node"], detail.replace("\n", " ")[:90])
        elif event["type"] == "final":
            r = event["result"]
            print(f"\nFINAL  : {r['status']} | {r['kind']} | attempts {r['attempts']} | {r['latency_ms']} ms")
            if r["sql"]:
                print("QUERY  :\n" + r["sql"])
            for w in r["warnings"]:
                print(f"WARNING: [{w['level']}] {w['text']}")
            p = r["preview"]
            if p and p["available"]:
                print("PREVIEW:", p["rows"][:3] if p["kind"] == "SELECT" else f"{p['kind']} affects {p['affected']} of {p['table_rows']} rows")
            print("TEXT   :", r["explanation"] or r["message"])
        else:
            print(seconds, "ERROR:", event["message"])