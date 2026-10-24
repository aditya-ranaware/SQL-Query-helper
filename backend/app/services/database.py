import re
import sqlite3
import time
from pathlib import Path

from app.config import settings

# Words that must never appear in a query (checked outside of quoted text)
FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create", "attach", "detach",
             "pragma", "vacuum", "reindex", "truncate"]


class QueryError(Exception):
    """A problem with the SQL. The message goes back to the AI so it can fix the query."""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.db_path).resolve()
    # mode=ro opens the database read-only, so even a bug in our own checks cannot change data
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def check_sql(sql: str) -> str:
    """Allow one SELECT statement only. Returns the cleaned query or raises QueryError."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise QueryError("The query is empty.")

    text = re.sub(r"'(?:[^']|'')*'", "''", cleaned)                  # ignore text inside quotes
    text = re.sub(r"--[^\n]*|/\*.*?\*/", " ", text, flags=re.S)      # ignore comments

    if ";" in text:
        raise QueryError("Only one SQL statement is allowed.")
    if not re.match(r"\s*(select|with)\b", text, re.I):
        raise QueryError("Only SELECT queries are allowed. The query must start with SELECT or WITH.")
    for word in FORBIDDEN:
        if re.search(rf"\b{word}\b", text, re.I):
            raise QueryError(f"The keyword '{word.upper()}' is not allowed. This database is read-only.")
    if re.search(r"\breplace\b(?!\s*\()", text, re.I):  # REPLACE(...) the text function is fine
        raise QueryError("The keyword 'REPLACE' is not allowed. This database is read-only.")
    return cleaned


def run_query(sql: str, timeout_seconds: float = 5.0, db_path: Path | None = None) -> dict:
    """Run a safe SELECT and return {"columns", "rows", "truncated"}. Raises QueryError on any problem."""
    sql = check_sql(sql)
    con = _connect(db_path)
    deadline = time.monotonic() + timeout_seconds
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10000)  # stop slow queries
    try:
        cur = con.execute(sql)
        columns = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(settings.max_result_rows + 1)
    except sqlite3.OperationalError as e:
        message = "The query took too long and was stopped." if "interrupted" in str(e) else str(e)
        raise QueryError(message) from None
    except sqlite3.Error as e:
        raise QueryError(str(e)) from None
    finally:
        con.close()

    limit = settings.max_result_rows
    return {"columns": columns, "rows": [list(r) for r in rows[:limit]], "truncated": len(rows) > limit}


def get_schema_text(db_path: Path | None = None) -> str:
    """Describe every table for the AI: columns, types, links between tables, and small sets of values."""
    con = _connect(db_path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        lines = []
        for table in tables:
            links = {r[3]: f"{r[2]}.{r[4]}" for r in con.execute(f'PRAGMA foreign_key_list("{table}")')}
            columns = []
            for _, name, col_type, _, _, is_pk in con.execute(f'PRAGMA table_info("{table}")'):
                part = f"{name} {col_type}"
                if is_pk:
                    part += " PRIMARY KEY"
                if name in links:
                    part += f" -> {links[name]}"
                if col_type.upper() == "TEXT":  # show the allowed values of small categories
                    values = [r[0] for r in con.execute(f'SELECT DISTINCT "{name}" FROM "{table}" LIMIT 9')
                              if r[0] is not None]
                    if 0 < len(values) <= 8:
                        part += " (values: " + ", ".join(f"'{v}'" for v in values) + ")"
                columns.append(part)
            lines.append(f"{table}({', '.join(columns)})")
        return "\n".join(lines)
    finally:
        con.close()




def get_schema_info(db_path: Path | None = None) -> list[dict]:
    """The same information as get_schema_text, as data the screen can display."""
    con = _connect(db_path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        info = []
        for table in tables:
            links = {r[3]: f"{r[2]}.{r[4]}" for r in con.execute(f'PRAGMA foreign_key_list("{table}")')}
            columns = []
            for _, name, col_type, _, _, is_pk in con.execute(f'PRAGMA table_info("{table}")'):
                key = "primary key" if is_pk else (f"links to {links[name]}" if name in links else "")
                columns.append({"name": name, "type": col_type, "key": key})
            rows = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            info.append({"name": table, "rows": rows, "columns": columns})
        return info
    finally:
        con.close()