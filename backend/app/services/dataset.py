import csv
import io
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from app.config import settings

MAX_TABLES = 8
MAX_COLUMNS = 60
MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_ROWS = 50_000          # per table, keeps memory small on a free server
SESSION_MINUTES = 60
MAX_SESSIONS = 100


class DatasetError(Exception):
    """A problem with the data the user gave us. The message is safe to show on the screen."""


@dataclass
class Table:
    name: str
    columns: dict[str, str]              # column name -> MySQL type ("" if the user did not say)
    rows: list[list] | None = None       # real data, only when a CSV or the sample was used


@dataclass
class Dataset:
    tables: dict[str, Table]
    source: str                          # "csv", "schema" or "sample"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created: float = field(default_factory=time.time)

    @property
    def has_data(self) -> bool:
        return any(t.rows is not None for t in self.tables.values())

    def schema_for_checker(self) -> dict[str, dict[str, str]]:
        return {t.name: {c: (ty or "VARCHAR(255)") for c, ty in t.columns.items()} for t in self.tables.values()}

    def schema_text(self) -> str:
        """Describe the tables for the AI. Small sets of values (like statuses) are shown too."""
        lines = []
        for t in self.tables.values():
            parts = []
            for i, (col, col_type) in enumerate(t.columns.items()):
                part = f"{col} {col_type}".strip()
                if t.rows and col_type.upper().startswith(("VARCHAR", "TEXT")):
                    values = {r[i] for r in t.rows if r[i] is not None}
                    if 0 < len(values) <= 8:
                        part += " (values: " + ", ".join(f"'{v}'" for v in sorted(values)) + ")"
                parts.append(part)
            lines.append(f"{t.name}({', '.join(parts)})")
        return "\n".join(lines)

    def summary(self) -> dict:
        """What the screen shows in the tables panel."""
        return {
            "id": self.id,
            "source": self.source,
            "has_data": self.has_data,
            "tables": [
                {
                    "name": t.name,
                    "rows": len(t.rows) if t.rows is not None else None,
                    "columns": [{"name": c, "type": ty} for c, ty in t.columns.items()],
                }
                for t in self.tables.values()
            ],
        }


# ------------------------------------------------------------------ names and types
def clean_name(raw: str, fallback: str, prefix: str) -> str:
    name = re.sub(r"\W+", "_", raw.strip()).strip("_").lower() or fallback
    if name[0].isdigit():
        name = prefix + name
    return name[:64]


def unique(name: str, taken) -> str:
    candidate, n = name, 2
    while candidate in taken:
        candidate, n = f"{name}_{n}", n + 1
    return candidate


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?")


def _is_int(v: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", v)) and not (len(v.lstrip("-")) > 1 and v.lstrip("-").startswith("0"))


def _is_float(v: str) -> bool:
    try:
        return float(v) == float(v) and v.lower().lstrip("+-") not in ("inf", "infinity", "nan")
    except ValueError:
        return False


def infer_type(values: list[str]) -> str:
    vals = [v for v in values if v != ""]
    if not vals:
        return "VARCHAR(255)"
    keeps_leading_zero = any(re.fullmatch(r"-?0\d+", v) for v in vals)  # phone numbers, zip codes, ids like 007
    if not keeps_leading_zero and all(_is_int(v) for v in vals):
        return "INT" if max(abs(int(v)) for v in vals) < 2**31 else "BIGINT"
    if not keeps_leading_zero and all(_is_float(v) for v in vals):
        return "DOUBLE"
    if all(DATE_RE.fullmatch(v) for v in vals):
        return "DATE"
    if all(DATETIME_RE.fullmatch(v) for v in vals):
        return "DATETIME"
    return "VARCHAR(255)" if max(len(v) for v in vals) <= 255 else "TEXT"


def convert(value: str, col_type: str):
    if value == "":
        return None
    if col_type in ("INT", "BIGINT"):
        return int(value)
    if col_type == "DOUBLE":
        return float(value)
    return value


# ------------------------------------------------------------------ 1) CSV files
def from_csv_files(files: list[tuple[str, bytes]]) -> Dataset:
    if not files:
        raise DatasetError("Choose at least one CSV file.")
    if len(files) > MAX_TABLES:
        raise DatasetError(f"Please upload at most {MAX_TABLES} files at a time.")

    tables: dict[str, Table] = {}
    for filename, content in files:
        if not filename.lower().endswith(".csv"):
            raise DatasetError(f"'{filename}' is not a CSV file.")
        if len(content) > MAX_CSV_BYTES:
            raise DatasetError(f"'{filename}' is larger than {MAX_CSV_BYTES // (1024 * 1024)} MB.")

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        records = [r for r in csv.reader(io.StringIO(text), dialect) if any(cell.strip() for cell in r)]
        if len(records) < 2:
            raise DatasetError(f"'{filename}' needs a header row and at least one data row.")
        if len(records) - 1 > MAX_ROWS:
            raise DatasetError(f"'{filename}' has more than {MAX_ROWS:,} rows. Please upload a smaller sample.")

        header = records[0]
        if len(header) > MAX_COLUMNS:
            raise DatasetError(f"'{filename}' has more than {MAX_COLUMNS} columns.")
        names: list[str] = []
        for i, raw in enumerate(header):
            names.append(unique(clean_name(raw, f"column_{i + 1}", "c_"), names))

        body = [(r + [""] * len(names))[: len(names)] for r in records[1:]]
        body = [[cell.strip() for cell in r] for r in body]
        types = [infer_type([r[i] for r in body]) for i in range(len(names))]
        rows = [[convert(r[i], types[i]) for i in range(len(names))] for r in body]

        stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0]
        table_name = unique(clean_name(stem, "table", "t_"), tables)
        tables[table_name] = Table(table_name, dict(zip(names, types)), rows)

    return Dataset(tables, "csv")


# ------------------------------------------------------------------ 2) pasted text
def split_top_level(text: str) -> list[str]:
    """Split on commas, but not the commas inside brackets, like decimal(10,2)."""
    parts, depth, current = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    return parts + [current]


def parse_ddl(text: str) -> dict[str, dict[str, str]]:
    try:
        statements = sqlglot.parse(text, dialect="mysql")
    except sqlglot.errors.ParseError as e:
        first_line = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).splitlines()[0]
        raise DatasetError(f"I could not read the CREATE TABLE text: {first_line}") from None

    found: dict[str, dict[str, str]] = {}
    for st in statements:
        if not isinstance(st, exp.Create) or str(st.args.get("kind", "")).upper() != "TABLE":
            continue
        schema = st.this
        if not isinstance(schema, exp.Schema):
            continue
        columns = {}
        for item in schema.expressions:
            if isinstance(item, exp.ColumnDef):   # skips PRIMARY KEY(...), FOREIGN KEY(...) lines
                kind = item.args.get("kind")
                columns[item.name] = kind.sql("mysql") if kind else ""
        found[schema.this.name] = columns
    return found


def parse_simple(text: str) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for raw in text.splitlines():
        line = raw.strip().rstrip(";")
        if not line or line.startswith(("--", "#")):
            continue
        m = re.match(r"^([A-Za-z_]\w*)\s*(:|\()\s*(.*)$", line)
        if not m:
            raise DatasetError(f'I could not read this line: "{line[:60]}". Use the form  customers: id, name, city')
        name, opener, rest = m.group(1), m.group(2), m.group(3)
        if opener == "(" and rest.endswith(")"):
            rest = rest[:-1]
        columns = {}
        for part in split_top_level(rest):
            tokens = part.strip().split(None, 1)
            if tokens:
                columns[tokens[0].strip("`\"'")] = tokens[1].strip().upper() if len(tokens) > 1 else ""
        found[name] = columns
    return found


def from_schema_text(text: str) -> Dataset:
    text = text.strip()
    if not text:
        raise DatasetError("Type or paste your table and column names first.")
    if len(text) > 20_000:
        raise DatasetError("That text is too long. Please paste only the table definitions.")

    found = parse_ddl(text) if re.search(r"\bcreate\s+table\b", text, re.I) else parse_simple(text)
    found = {n: cols for n, cols in found.items() if cols}
    if not found:
        raise DatasetError("I found no tables. Example:  customers: id, name, city")
    if len(found) > MAX_TABLES:
        raise DatasetError(f"Please describe at most {MAX_TABLES} tables.")
    for name, cols in found.items():
        if len(cols) > MAX_COLUMNS:
            raise DatasetError(f"Table '{name}' has more than {MAX_COLUMNS} columns.")

    return Dataset({name: Table(name, cols) for name, cols in found.items()}, "schema")


# ------------------------------------------------------------------ 3) the built-in sample
def sample_dataset() -> Dataset:
    """The demo shop database, so a first-time visitor can try the app without any data."""
    if not settings.db_path.exists():
        raise DatasetError("The sample database is not available on this server.")
    con = sqlite3.connect(f"{settings.db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        tables = {}
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            cols = {}
            rows = [list(r) for r in con.execute(f'SELECT * FROM "{name}"')]
            for i, (_, col, col_type, *_) in enumerate(con.execute(f'PRAGMA table_info("{name}")')):
                if col_type.upper() == "TEXT":   # a text column full of dates is a DATE in MySQL
                    cols[col] = infer_type([str(r[i]) for r in rows if r[i] is not None])
                else:
                    cols[col] = {"INTEGER": "INT"}.get(col_type.upper(), col_type.upper())
            tables[name] = Table(name, cols, rows)
        return Dataset(tables, "sample")
    finally:
        con.close()


# ------------------------------------------------------------------ remembering datasets for a while
class DatasetStore:
    """Keeps each visitor's dataset in memory for a short time."""

    def __init__(self):
        self._items: dict[str, Dataset] = {}

    def _purge(self):
        cutoff = time.time() - SESSION_MINUTES * 60
        for key in [k for k, d in self._items.items() if d.created < cutoff]:
            del self._items[key]
        while len(self._items) > MAX_SESSIONS:
            del self._items[min(self._items, key=lambda k: self._items[k].created)]

    def add(self, dataset: Dataset) -> Dataset:
        self._items[dataset.id] = dataset
        self._purge()
        return dataset

    def get(self, dataset_id: str) -> Dataset | None:
        self._purge()
        return self._items.get(dataset_id)


store = DatasetStore()