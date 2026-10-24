import json
import time

import groq
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.graph.workflow import graph, start_state
from app.limits import ask_limit
from app.services.dataset import store

router = APIRouter()


class AskRequest(BaseModel):
    dataset_id: str
    request: str = Field(min_length=3, max_length=500)


def sse(payload: dict) -> str:
    """Format one Server-Sent Event."""
    return f"data: {json.dumps(payload)}\n\n"


def final_payload(state: dict, started: float) -> dict:
    check = state.get("check")
    return {
        "status": state.get("status", "failed"),
        "message": state.get("answer", ""),          # used when no query could be written
        "explanation": state.get("explanation", ""),
        "sql": check.sql if check else state.get("sql"),
        "kind": check.kind if check else None,
        "warnings": check.warnings if check else [],
        "check_query": check.check_query if check else None,
        "preview": state.get("preview"),
        "attempts": state.get("attempts", 0),
        "steps": state.get("steps", []),
        "latency_ms": int((time.time() - started) * 1000),
    }


@router.post("/ask/stream", dependencies=[Depends(ask_limit)])
def ask_stream(req: AskRequest):
    """Run the workflow and send each step to the screen the moment it finishes."""
    dataset = store.get(req.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Your data has expired. Please add it again.")
    request = req.request.strip()

    def events():
        started = time.time()
        seen = 0
        state = {}
        try:
            # stream_mode="values" gives the full state after every step
            for state in graph.stream(start_state(request, dataset), stream_mode="values"):
                for step in state.get("steps", [])[seen:]:
                    yield sse({"type": "step", "step": step})
                seen = len(state.get("steps", []))
            yield sse({"type": "final", "result": final_payload(state, started)})
        except groq.RateLimitError:
            yield sse({"type": "error", "message": "The AI model is rate limited. Wait a minute and try again."})
        except groq.APIError:
            yield sse({"type": "error", "message": "The AI model returned an error. Please try again."})
        except Exception:
            yield sse({"type": "error", "message": "Something went wrong while writing the query. Please try again."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )