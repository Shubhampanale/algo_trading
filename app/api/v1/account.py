from fastapi import APIRouter

router = APIRouter()


@router.get("/balance")
async def balance():
    return {"message": "Balance API"}
