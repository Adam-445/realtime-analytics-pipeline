import time

from fastapi import APIRouter

router = APIRouter()
_start_time = time.time()
_ready = False
_first_event_time: float | None = None


def mark_first_event():
    global _first_event_time, _ready
    if _first_event_time is None:
        _first_event_time = time.time()
        _ready = True


@router.get("/health")
def health():
    return {"status": "ok", "uptime_s": time.time() - _start_time}


@router.get("/ready")
def ready():
    return {
        "ready": _ready,
        "since_first_event_s": (
            None if _first_event_time is None else time.time() - _first_event_time
        ),
    }
