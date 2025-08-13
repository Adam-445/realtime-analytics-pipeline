from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def heathz():
    return {"status": "ok"}
