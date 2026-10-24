from app.services.sqlcheck import SqlProblem, check_sql

SCHEMA = {
    "customers": {"id": "INT", "name": "VARCHAR(50)", "city": "VARCHAR(50)"},
    "orders": {"id": "INT", "customer_id": "INT", "order_date": "DATE", "status": "VARCHAR(20)"},
    "products": {"id": "INT", "name": "VARCHAR(50)", "price": "INT"},
}


def run(label, sql):
    try:
        r = check_sql(sql, SCHEMA)
        warnings = [w["level"] for w in r.warnings]
        print(f"OK       {label:30} warnings: {warnings or 'none'}")
    except SqlProblem as e:
        print(f"REJECTED {label:30} -> {str(e)[:100]}")


print("--- should be accepted ---")
run("select with join", "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name ORDER BY n DESC")
run("MySQL date function", "SELECT DATE_FORMAT(order_date, '%Y-%m') AS m, COUNT(*) FROM orders GROUP BY m")
run("update with where", "UPDATE products SET price = 50000 WHERE name = 'Laptop'")
run("delete with where", "DELETE FROM orders WHERE status = 'cancelled'")
run("insert with columns", "INSERT INTO customers (id, name, city) VALUES (31, 'Zoya', 'Pune')")

print("\n--- wrong table or column names ---")
run("misspelled table", "SELECT * FROM ordars")
run("misspelled column (select)", "SELECT c.nme FROM customers c")
run("misspelled column (update)", "UPDATE products SET prise = 50000 WHERE name = 'Laptop'")
run("misspelled column (delete)", "DELETE FROM orders WHERE statuss = 'cancelled'")
run("wrong column (insert)", "INSERT INTO customers (id, name, town) VALUES (31, 'Zoya', 'Pune')")
run("wrong number of values", "INSERT INTO customers (id, name) VALUES (31, 'Zoya', 'Pune')")
run("ambiguous column", "SELECT id FROM customers c JOIN orders o ON o.customer_id = c.id")

print("\n--- not allowed ---")
run("DROP", "DROP TABLE orders")
run("TRUNCATE", "TRUNCATE TABLE orders")
run("two statements", "SELECT 1; DROP TABLE orders")
run("SLEEP", "SELECT SLEEP(10)")
run("syntax error", "SELEC name FROM customers")

print("\n--- risky but allowed (the user gets warnings) ---")
run("DELETE without WHERE", "DELETE FROM orders")
run("DELETE WHERE 1 = 1", "DELETE FROM orders WHERE 1 = 1")
run("UPDATE without WHERE", "UPDATE products SET price = 1")

print("\n--- a closer look ---")
r = check_sql("delete from orders where status='cancelled' and order_date<'2024-01-01'", SCHEMA)
print("Formatted query:\n" + r.sql)
print("\nWarnings:", [w["text"] for w in r.warnings])
print("\nCheck query (see the rows first):\n" + r.check_query)