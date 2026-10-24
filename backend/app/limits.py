import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def limiter(max_calls: int, message: str, window_seconds: int = 60):
    """Make a FastAPI dependency that allows each visitor (by IP address) max_calls per window."""
    hits: dict[str, deque] = defaultdict(deque)

    def check(request: Request) -> None:
        visitor = request.client.host if request.client else "unknown"
        now = time.time()
        recent = hits[visitor]
        while recent and now - recent[0] > window_seconds:
            recent.popleft()
        if len(recent) >= max_calls:
            raise HTTPException(status_code=429, detail=message)
        recent.append(now)

    return check


ask_limit = limiter(8, "Too many requests in a short time. Please wait a minute and try again.")
upload_limit = limiter(20, "Too many uploads in a short time. Please wait a minute and try again.")