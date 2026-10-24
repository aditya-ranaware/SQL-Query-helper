import difflib
import logging
import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, SqlglotError
from sqlglot.optimizer.qualify import qualify

logging.getLogger("sqlglot").setLevel(logging.ERROR)  # stay quiet about syntax sqlglot only half understands

READ_TYPES = (exp.Select, exp.SetOperation)       # SELECT, and SELECT ... UNION ...
BLOCKED_FUNCTIONS = {"sleep", "benchmark", "load_file"}


class SqlProblem(Exception):
    """The query is not acceptable. The message goes back to the AI so it can fix the query."""


@dataclass
class CheckResult:
    kind: str                         # SELECT, INSERT, UPDATE or DELETE
    sql: str                          # the query, neatly formatted in MySQL
    tables: list[str]                 # the real tables it uses
    warnings: list[dict] = field(default_factory=list)   # [{"level": "danger" | "warning", "text": "..."}]
    check_query: str | None = None    # for UPDATE and DELETE: a SELECT that shows the rows that match


def check_sql(sql: str, schema: dict[str, dict[str, str]]) -> CheckResult:
    """Check a MySQL query against the user's tables. Raises SqlProblem with a helpful message."""
    tree = _parse(sql)
    kind = _kind(tree)
    tables = _check_tables(tree, schema)
    _check_functions(tree)
    if kind == "SELECT":
        _check_select_columns(tree, schema, tables)
    else:
        _check_write_columns(tree, schema, tables)
    warnings, check_query = _risk(tree, kind)
    return CheckResult(kind, _format(tree), tables, warnings, check_query)

def _compact(pretty: str) -> str:
    """sqlglot puts every column on its own line. Join short lists back onto one line so the query reads easily."""
    lines = pretty.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if re.fullmatch(r"(SELECT|ORDER BY|GROUP BY|WHERE|HAVING|SET)", line):
            block, j = [], i + 1
            while j < len(lines) and lines[j].startswith("  ") and not lines[j].startswith("    "):
                block.append(lines[j].strip())
                j += 1
            joined = f"{line} {' '.join(block)}"
            nested = any(b.endswith("(") or b == ")" for b in block) or joined.count("(") != joined.count(")")
            if block and not nested and len(joined) <= 76:
                out.append(joined)
                i = j
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _format(tree) -> str:
    return _compact(tree.sql(dialect="mysql", pretty=True))

# ------------------------------------------------------------------ 1) is it one allowed statement?
def _parse(sql: str):
    text = (sql or "").strip()
    if not text:
        raise SqlProblem("The query is empty.")
    try:
        trees = [t for t in sqlglot.parse(text, dialect="mysql") if t is not None]
    except SqlglotError as e:
        first_line = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).splitlines()[0]
        raise SqlProblem(f"MySQL syntax error: {first_line}") from None
    if not trees:
        raise SqlProblem("The query is empty.")
    if len(trees) > 1:
        raise SqlProblem("Only one SQL statement is allowed. Write a single query.")
    return trees[0]


def _kind(tree) -> str:
    if isinstance(tree, READ_TYPES):
        return "SELECT"
    if isinstance(tree, (exp.Insert, exp.Update, exp.Delete)):
        return tree.key.upper()
    name = tree.name.upper() if isinstance(tree, exp.Command) else tree.key.upper()
    name = {"TRUNCATETABLE": "TRUNCATE"}.get(name, name)
    raise SqlProblem(f"Only SELECT, INSERT, UPDATE and DELETE queries are allowed. This query uses {name}.")


def _check_functions(tree) -> None:
    for fn in tree.find_all(exp.Func):
        name = fn.name if isinstance(fn, exp.Anonymous) else fn.sql_name()
        if name.lower() in BLOCKED_FUNCTIONS:
            raise SqlProblem(f"The function {name.upper()}() is not allowed.")


# ------------------------------------------------------------------ 2) do the tables exist?
def _suggest(name: str, options) -> str:
    close = difflib.get_close_matches(name.lower(), [o.lower() for o in options], n=1, cutoff=0.6)
    if not close:
        return ""
    original = next(o for o in options if o.lower() == close[0])
    return f" Did you mean '{original}'?"


def _check_tables(tree, schema) -> list[str]:
    known = {name.lower(): name for name in schema}
    ctes = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    used: list[str] = []
    for table in tree.find_all(exp.Table):
        name = table.name
        if not name or name.lower() in ctes or name.lower() == "dual":
            continue
        if name.lower() not in known:
            raise SqlProblem(
                f"Table '{name}' does not exist. Available tables: {', '.join(schema)}.{_suggest(name, schema)}"
            )
        if known[name.lower()] not in used:
            used.append(known[name.lower()])
    return used


# ------------------------------------------------------------------ 3) do the columns exist?
def _lowercase(tree):
    copy = tree.copy()
    for ident in copy.find_all(exp.Identifier):
        ident.set("this", ident.name.lower())
    return copy


def _columns_text(schema, tables) -> str:
    return "; ".join(f"{t}({', '.join(schema[t])})" for t in tables)


def _missing_column(col: str, schema, tables) -> SqlProblem:
    pool = [c for t in tables for c in schema[t]]
    return SqlProblem(
        f"Column '{col}' does not exist in the tables used. Available columns: {_columns_text(schema, tables)}."
        f"{_suggest(col, pool)}"
    )


def _check_select_columns(tree, schema, tables) -> None:
    lowered = _lowercase(tree)
    schema_lc = {t.lower(): {c.lower(): ty for c, ty in cols.items()} for t, cols in schema.items()}
    try:
        qualify(lowered, schema=schema_lc, dialect="mysql")
    except OptimizeError as e:
        raise _explain_optimize_error(str(e), lowered, schema, tables) from None
    except Exception:
        return  # sqlglot could not analyse this shape of query; the table checks above already passed


def _explain_optimize_error(message: str, tree, schema, tables) -> SqlProblem:
    aliases = {t.alias_or_name.lower(): t.name.lower() for t in tree.find_all(exp.Table) if t.name}
    real = {t.lower(): t for t in schema}

    m = re.search(r"Column '([^']+)' could not be resolved for table: '([^']+)'", message)
    if m:
        col, qualifier = m.groups()
        if qualifier in aliases:
            table = real[aliases[qualifier]]
            return SqlProblem(
                f"Column '{col}' does not exist in table '{table}'. Columns of {table}: {', '.join(schema[table])}."
                f"{_suggest(col, schema[table])}"
            )
        return SqlProblem(
            f"'{qualifier}' is not a table or alias in this query. Use one of: {', '.join(aliases) or 'none'}."
        )

    m = re.search(r"Unknown column: (\w+)", message)
    if m:
        col = m.group(1)
        for node in tree.find_all(exp.Column):          # written like  c.nme  ?
            if node.name == col and node.table in aliases:
                table = real[aliases[node.table]]
                return SqlProblem(
                    f"Column '{col}' does not exist in table '{table}'. Columns of {table}: {', '.join(schema[table])}."
                    f"{_suggest(col, schema[table])}"
                )
        return _missing_column(col, schema, tables)

    m = re.search(r"Column '([^']+)' could not be resolved", message)
    if m:
        col = m.group(1)
        owners = [t for t in tables if col.lower() in {c.lower() for c in schema[t]}]
        if len(owners) >= 2:   # sqlglot says "could not be resolved" for an ambiguous column too
            return SqlProblem(
                f"Column '{col}' is ambiguous: it exists in {' and '.join(owners)}. "
                f"Write it with the table name, like {owners[0]}.{col}."
            )
        return _missing_column(col, schema, tables)

    return SqlProblem(f"Column problem: {message.split('.')[0]}")


def _check_write_columns(tree, schema, tables) -> None:
    """INSERT, UPDATE and DELETE are not analysed by sqlglot, so the columns are checked here."""
    lower_cols = {t.lower(): {c.lower() for c in cols} for t, cols in schema.items()}
    aliases = {t.alias_or_name.lower(): t.name.lower() for t in tree.find_all(exp.Table) if t.name.lower() in lower_cols}
    virtual = {a.alias.lower() for a in tree.find_all(exp.Alias)}
    virtual |= {c.alias.lower() for c in tree.find_all(exp.CTE)}
    virtual |= {s.alias.lower() for s in tree.find_all(exp.Subquery) if s.alias}
    used_cols = set().union(*(lower_cols[t.lower()] for t in tables)) if tables else set()
    real = {t.lower(): t for t in schema}

    if isinstance(tree, exp.Insert):
        _check_insert(tree, schema, real)

    for col in tree.find_all(exp.Column):
        name = col.name.lower()
        if not name or isinstance(col.this, exp.Star):
            continue
        qualifier = col.table.lower()
        if qualifier in aliases:
            if name not in lower_cols[aliases[qualifier]]:
                table = real[aliases[qualifier]]
                raise SqlProblem(
                    f"Column '{col.name}' does not exist in table '{table}'. "
                    f"Columns of {table}: {', '.join(schema[table])}.{_suggest(col.name, schema[table])}"
                )
        elif qualifier:
            if qualifier not in virtual:
                raise SqlProblem(
                    f"'{col.table}' is not a table or alias in this query. Use one of: {', '.join(aliases) or 'none'}."
                )
        elif name not in used_cols and name not in virtual:
            raise _missing_column(col.name, schema, tables)


def _check_insert(tree, schema, real) -> None:
    target = tree.this
    listed = None
    table_node = target
    if isinstance(target, exp.Schema):
        table_node = target.this
        listed = [i.name for i in target.expressions]
    table = real.get(table_node.name.lower())
    if table is None:
        return
    table_cols = list(schema[table])

    if listed is not None:
        valid = {c.lower() for c in table_cols}
        for col in listed:
            if col.lower() not in valid:
                raise SqlProblem(
                    f"Column '{col}' does not exist in table '{table}'. "
                    f"Columns of {table}: {', '.join(table_cols)}.{_suggest(col, table_cols)}"
                )
    expected = len(listed) if listed is not None else len(table_cols)

    values = tree.expression
    if isinstance(values, exp.Values):
        for row in values.expressions:
            if len(row.expressions) != expected:
                where = f" ({', '.join(listed)})" if listed else f" ({', '.join(table_cols)})"
                raise SqlProblem(
                    f"INSERT gives {len(row.expressions)} values but {expected} columns are expected{where}."
                )


# ------------------------------------------------------------------ 4) how risky is it?
def _always_true(cond) -> bool:
    if isinstance(cond, exp.Boolean):
        return bool(cond.this)
    if isinstance(cond, exp.Paren):
        return _always_true(cond.this)
    return isinstance(cond, exp.EQ) and cond.left == cond.right


def _risk(tree, kind: str) -> tuple[list[dict], str | None]:
    warnings: list[dict] = []
    check_query = None

    if kind in ("UPDATE", "DELETE"):
        where = tree.args.get("where")
        if where is None or _always_true(where.this):
            warnings.append({
                "level": "danger",
                "text": f"There is no real WHERE condition, so this {kind} changes EVERY row in the table.",
            })
        else:
            warnings.append({
                "level": "warning",
                "text": "This changes data. Run the check query first to see exactly which rows match.",
            })
            check_query = _make_check_query(tree, where)
        if kind == "DELETE":
            warnings.append({"level": "warning", "text": "Deleted rows cannot be restored unless you have a backup."})

    if kind == "INSERT" and not isinstance(tree.this, exp.Schema):
        warnings.append({
            "level": "warning",
            "text": "No column list is given, so the values must match the table's column order exactly.",
        })

    return warnings, check_query


def _make_check_query(tree, where) -> str | None:
    """A SELECT with the same WHERE, so the user can see which rows would change."""
    target = tree.this
    if not isinstance(target, exp.Table) or target.args.get("joins"):
        return None
    query = exp.select("*").from_(target.copy()).where(where.this.copy())
    return _compact(query.sql(dialect="mysql", pretty=True))