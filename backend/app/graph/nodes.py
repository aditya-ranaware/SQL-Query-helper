import re

from app.config import settings
from app.graph.llm import get_llm
from app.graph.prompts import EXPLAIN_SYSTEM, SQL_SYSTEM
from app.graph.state import State
from app.services.sandbox import preview as run_preview
from app.services.sqlcheck import SqlProblem, check_sql


def clean_sql(text: str) -> str:
    """Remove markdown fences if the model added them anyway."""
    text = re.sub(r"^```(?:sql|mysql)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return text.strip()


def write_sql(state: State) -> dict:
    """Step 1: the AI writes a MySQL query. If the last one was rejected, it also sees why and fixes it."""
    attempt = state.get("attempts", 0) + 1

    if state.get("error"):
        user_message = (
            f"Request: {state['request']}\n\n"
            f"Your previous query:\n{state['sql']}\n\n"
            f"It was rejected for this reason:\n{state['error']}\n\n"
            "Write a corrected query."
        )
    else:
        user_message = f"Request: {state['request']}"

    reply = get_llm().invoke([
        ("system", SQL_SYSTEM.format(schema=state["dataset"].schema_text())),
        ("human", user_message),
    ])
    text = clean_sql(reply.content)

    for prefix, status in (("UNANSWERABLE", "unanswerable"), ("NEEDS_INFO", "needs_info")):
        if text.upper().startswith(prefix):
            message = text.split(":", 1)[1].strip() if ":" in text else "Please give me more details."
            return {
                "attempts": attempt,
                "status": status,
                "answer": message,
                "steps": [{"node": "write_sql", "attempt": attempt, status: message}],
            }

    return {
        "sql": text,
        "attempts": attempt,
        "error": None,
        "steps": [{"node": "write_sql", "attempt": attempt, "sql": text}],
    }


def check(state: State) -> dict:
    """Step 2: check the query against the user's tables. A rejection is saved so the AI can fix it."""
    try:
        result = check_sql(state["sql"], state["dataset"].schema_for_checker())
    except SqlProblem as e:
        return {
            "check": None,
            "error": str(e),
            "steps": [{"node": "check", "attempt": state["attempts"], "ok": False, "error": str(e)}],
        }
    return {
        "check": result,
        "error": None,
        "steps": [{"node": "check", "attempt": state["attempts"], "ok": True, "kind": result.kind,
                   "warnings": len(result.warnings)}],
    }


def preview(state: State) -> dict:
    """Step 3: try the query on a throwaway copy of the user's data (only if they uploaded data)."""
    c = state["check"]
    table = c.tables[0] if len(c.tables) == 1 else None
    result = run_preview(state["dataset"], c.kind, c.sql, c.check_query, table)
    return {
        "preview": result,
        "steps": [{"node": "preview", "ran": bool(result and result.get("available"))}],
    }


def explain(state: State) -> dict:
    """Step 4: the AI explains the query in plain English."""
    c = state["check"]
    reply = get_llm().invoke([
        ("system", EXPLAIN_SYSTEM),
        ("human", f"The user asked: {state['request']}\n\nThe query:\n{c.sql}"),
    ])
    return {
        "explanation": reply.content.strip(),
        "status": "success",
        "steps": [{"node": "explain"}],
    }


def give_up(state: State) -> dict:
    """The AI used all its attempts without an accepted query."""
    return {
        "status": "failed",
        "answer": f"I couldn't write a query that passes the checks after {state['attempts']} attempts. "
                  f"The last problem was: {state['error']}",
        "steps": [{"node": "give_up"}],
    }


# ---- decisions: which step comes next? ----
def after_write(state: State) -> str:
    return "end" if state.get("status") in ("unanswerable", "needs_info") else "check"


def after_check(state: State) -> str:
    if not state.get("error"):
        return "preview"
    if state["attempts"] <= settings.max_fix_attempts:  # the first query plus up to 3 fixes
        return "write_sql"                               # loop back and fix it
    return "give_up"