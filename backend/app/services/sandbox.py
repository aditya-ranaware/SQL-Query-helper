import sqlite3
import time

import sqlglot
from sqlglot.errors import SqlglotError

from app.services.dataset import Dataset

PREVIEW_ROWS = 20       # rows shown for a SELECT
SAMPLE_ROWS = 5         # example rows shown for an UPDATE or DELETE
TIMEOUT_SECONDS = 3.0


def _sqlite_type(mysql_type: str) -> str:
    t = mysql_type.upper()
    if t.startswith(("INT", "BIGINT", "SMALLINT", "TINYINT")):
        return "INTEGER"
    if t.startswith(("DOUBLE", "FLOAT", "DECIMAL", "REAL")):
        return "REAL"
    return "TEXT"


def _build(dataset: Dataset) -> sqlite3.Connection:
    """A throwaway copy of the user's data, in memory. It disappears when the connection closes."""
    con = sqlite3.connect(":memory:")
    for table in dataset.tables.values():
        columns = ", ".join(f'"{c}" {_sqlite_type(t)}' for c, t in table.columns.items())
        con.execute(f'CREATE TABLE "{table.name}" ({columns})')
        marks = ", ".join("?" * len(table.columns))
        con.executemany(f'INSERT INTO "{table.name}" VALUES ({marks})', table.rows or [])
    con.commit()
    return con


def _to_sqlite(mysql: str) -> str:
    return sqlglot.transpile(mysql, read="mysql", write="sqlite")[0]


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def preview(dataset: Dataset, kind: str, mysql: str, check_query: str | None = None,
            table: str | None = None, timeout: float = TIMEOUT_SECONDS) -> dict | None:
    """Try the query on a copy of the data. Returns None when there is no data to try it on.

    The preview uses SQLite, so it can differ slightly from real MySQL. It never fails the whole request:
    if it cannot run, it says why and the query is still shown.
    """
    if not dataset.has_data:
        return None

    try:
        sqlite_sql = _to_sqlite(mysql)
        sqlite_check = _to_sqlite(check_query) if check_query else None
    except SqlglotError:
        return _unavailable("This query uses MySQL features the preview cannot run.")

    con = _build(dataset)
    deadline = time.monotonic() + timeout
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10000)
    try:
        if kind == "SELECT":
            cur = con.execute(sqlite_sql)
            columns = [d[0] for d in cur.description or []]
            rows = cur.fetchmany(PREVIEW_ROWS + 1)
            return {
                "available": True,
                "kind": kind,
                "columns": columns,
                "rows": [list(r) for r in rows[:PREVIEW_ROWS]],
                "has_more": len(rows) > PREVIEW_ROWS,
            }

        table_rows = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] if table else None
        sample = None
        if sqlite_check:   # example rows that match, before the change
            cur = con.execute(sqlite_check)
            sample = {
                "columns": [d[0] for d in cur.description or []],
                "rows": [list(r) for r in cur.fetchmany(SAMPLE_ROWS)],
            }
        cur = con.execute(sqlite_sql)
        affected = cur.rowcount
        con.rollback()
        return {
            "available": True,
            "kind": kind,
            "affected": affected,
            "table": table,
            "table_rows": table_rows,
            "sample": sample,
        }
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e):
            return _unavailable("The preview took too long and was stopped.")
        return _unavailable(f"The preview could not run this query ({e}).")
    except sqlite3.Error as e:
        return _unavailable(f"The preview could not run this query ({e}).")
    finally:
        con.close()