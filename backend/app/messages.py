from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class NLIPSubMessage(BaseModel):
    format: Literal["text", "image", "video", "audio"]
    subformat: Optional[str] = None
    content: str
    label: Optional[str] = None

class NLIPMessage(BaseModel):
    schema: Literal["nlip/v1"] = "nlip/v1"
    id: Optional[str] = None
    sender: str
    receiver: Optional[str] = None
    locale: Optional[str] = None
    messages: List[NLIPSubMessage] = Field(default_factory=list)

class NLIPResponse(BaseModel):
    schema: Literal["nlip/v1"] = "nlip/v1"
    id: Optional[str] = None
    sender: str = "supervisor"
    receiver: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[NLIPSubMessage] = Field(default_factory=list)