from langgraph.graph import END, START, StateGraph

from app.graph.nodes import after_check, after_write, check, explain, give_up, preview, write_sql
from app.graph.state import State
from app.services.dataset import Dataset


def build_graph():
    builder = StateGraph(State)

    # the steps
    builder.add_node("write_sql", write_sql)
    builder.add_node("check", check)
    builder.add_node("preview", preview)
    builder.add_node("explain", explain)
    builder.add_node("give_up", give_up)

    # the arrows
    builder.add_edge(START, "write_sql")
    builder.add_conditional_edges("write_sql", after_write, {"check": "check", "end": END})
    builder.add_conditional_edges("check", after_check,
                                  {"preview": "preview", "write_sql": "write_sql", "give_up": "give_up"})
    builder.add_edge("preview", "explain")
    builder.add_edge("explain", END)
    builder.add_edge("give_up", END)

    return builder.compile()


graph = build_graph()


def start_state(request: str, dataset: Dataset) -> State:
    return {"request": request, "dataset": dataset, "attempts": 0}


def ask(request: str, dataset: Dataset) -> State:
    """Run the whole workflow for one request and return the final state."""
    return graph.invoke(start_state(request, dataset))