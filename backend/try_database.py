from app.services.database import QueryError, get_schema_text, run_query

print("SCHEMA\n" + get_schema_text() + "\n")


def attempt(label, sql):
    try:
        r = run_query(sql)
        print(f"OK      {label}: {r['columns']} {r['rows'][:3]} truncated={r['truncated']}")
    except QueryError as e:
        print(f"BLOCKED {label}: {e}")


attempt("join query", "SELECT p.name, SUM(oi.quantity * p.price) AS revenue FROM order_items oi "
        "JOIN products p ON p.id = oi.product_id GROUP BY p.name ORDER BY revenue DESC LIMIT 3")
attempt("text with a keyword inside quotes", "SELECT COUNT(*) FROM orders WHERE status = 'delete me'")
attempt("REPLACE function", "SELECT REPLACE(name, 'a', 'o') FROM customers LIMIT 2")
attempt("DELETE", "DELETE FROM customers")
attempt("DROP", "DROP TABLE orders")
attempt("two statements", "SELECT 1; DROP TABLE orders")
attempt("PRAGMA", "PRAGMA table_info(orders)")
attempt("wrong column", "SELECT salary FROM customers")
attempt("wrong table", "SELECT * FROM clients")
attempt("syntax error", "SELEC name FROM customers")
attempt("too many rows", "SELECT * FROM order_items")
attempt("endless query", "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r) SELECT COUNT(*) FROM r")