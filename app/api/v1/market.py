from fastapi import APIRouter

router = APIRouter()


@router.get("/option-chain")
async def option_chain():
    return {"message": "Option Chain API"}
