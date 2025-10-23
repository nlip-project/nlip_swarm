from .messages import NLIPMessage, NLIPResponse

def process_nlip(payload: NLIPMessage) -> NLIPResponse:
    return NLIPResponse(
        id=payload.id,
        receiver=payload.sender,
        messages=payload.messages
    )