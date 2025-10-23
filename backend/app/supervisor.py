from .messages import NLIPMessage, NLIPResponse

def process_nlip(payload: NLIPMessage) -> NLIPResponse:
    # Echos back the received messages in the response
    return NLIPResponse(
        id=payload.id,
        receiver=payload.sender,
        messages=payload.messages
    )