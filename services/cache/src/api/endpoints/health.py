from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request):
    try:
        pong = await request.app.state.redis.ping()
        return {"status": "ok", "redis": pong}
    except Exception as e:
        return Response(status_code=503, content=str(e))


@router.get("/readyz")
async def readyz(request: Request):
    if request.app.state.ready_event.is_set():
        return {"status": "ready"}
    return Response(status_code=503, content="not ready")
