from fastapi import APIRouter

router = APIRouter(prefix="/earnings", tags=["Earnings"])

@router.get("/summary")
def earnings_summary():
    return {"message": "Earnings summary endpoint placeholder"}
