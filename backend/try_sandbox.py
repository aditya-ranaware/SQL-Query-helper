import time

from app.services.dataset import from_schema_text, sample_dataset
from app.services.sandbox import preview
from app.services.sqlcheck import check_sql

data = sample_dataset()
schema = data.schema_for_checker()


def run(label, sql, timeout=3.0):
    check = check_sql(sql, schema)
    table = check.tables[0] if len(check.tables) == 1 else None
    start = time.time()
    p = preview(data, check.kind, check.sql, check.check_query, table, timeout)
    took = f"{time.time() - start:.2f}s"
    print(f"\n{label} ({took})")
    if not p["available"]:
        print("   unavailable:", p["reason"])
    elif p["kind"] == "SELECT":
        print("   columns:", p["columns"], "| first rows:", p["rows"][:3], "| more rows:", p["has_more"])
    else:
        if p["kind"] == "INSERT":
            print(f"   INSERT would add {p['affected']} row to '{p['table']}' (it has {p['table_rows']} rows now)")
        else:
            print(f"   {p['kind']} would affect {p['affected']} of {p['table_rows']} rows in '{p['table']}'")
        if p["sample"]:
            print("   example rows:", p["sample"]["rows"][:2])


run("SELECT top products", "SELECT p.name, SUM(oi.quantity * p.price) AS revenue FROM order_items oi JOIN products p ON p.id = oi.product_id JOIN orders o ON o.id = oi.order_id WHERE o.status != 'cancelled' GROUP BY p.name ORDER BY revenue DESC LIMIT 3")
run("SELECT with MySQL date function", "SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, COUNT(*) AS orders FROM orders GROUP BY month ORDER BY month LIMIT 3")
run("DELETE cancelled orders", "DELETE FROM orders WHERE status = \"cancelled\"")
run("UPDATE electronics prices", "UPDATE products SET price = price * 1.1 WHERE category = 'Electronics'")
run("INSERT a customer", "INSERT INTO customers (id, name, city, joined_date) VALUES (31, 'Zoya', 'Pune', '2025-01-01')")
run("DELETE with no WHERE", "DELETE FROM orders")
run("a query that never ends (1 second limit)", "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT COUNT(*) FROM r", timeout=1.0)
run("a function the preview does not have", "SELECT FOO_BAR(name) FROM customers")

print("\nYOUR REAL DATA IS UNTOUCHED:")
print("   orders still has", len(data.tables["orders"].rows), "rows | products still has", len(data.tables["products"].rows))
p = preview(data, "SELECT", "SELECT COUNT(*) FROM orders")
print("   a fresh preview of COUNT(*) FROM orders says:", p["rows"])

schema_only = from_schema_text("customers: id, name, city")
print("\nNO DATA (pasted table names only):", preview(schema_only, "SELECT", "SELECT * FROM customers"))