from fastapi import APIRouter
from ..messages import NLIPMessage, NLIPResponse
from ..supervisor import process_nlip

router = APIRouter(prefix="", tags=["nlip"])

@router.post("/process", response_model=NLIPResponse)
def process_endpoint(paylod: NLIPMessage) -> NLIPResponse:
    return process_nlip(paylod)