from fastapi import APIRouter
from app.utils.response import ResponseModel

router = APIRouter()


@router.get("/health")
def health():
    return ResponseModel(success=True, data={"status": "ok"})
