import operator
from typing import Annotated, TypedDict

from app.services.dataset import Dataset
from app.services.sqlcheck import CheckResult


class State(TypedDict, total=False):
    """Everything the workflow remembers while it runs. Each step reads it and returns updates."""
    request: str             # what the user asked for, in plain English
    dataset: Dataset         # the user's tables (and data, if they uploaded any)
    sql: str                 # the latest query the AI wrote
    check: CheckResult | None  # the checked, neatly formatted query with its warnings
    error: str | None        # why the last query was rejected (None if it was accepted)
    attempts: int            # how many queries the AI has written so far
    preview: dict | None     # what the query would do on a copy of the data
    explanation: str         # the query explained in plain English
    answer: str              # the message when the AI could not write a query
    status: str              # "success", "failed", "unanswerable" or "needs_info"
    steps: Annotated[list, operator.add]  # a log of what happened. "operator.add" means new entries are appended