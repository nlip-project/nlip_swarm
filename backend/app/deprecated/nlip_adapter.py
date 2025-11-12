from __future__ import annotations
from typing import Dict, Any
from nlip_sdk.nlip import (
    NLIP_Message,
    NLIP_SubMessage,
    NLIP_Factory,
    AllowedFormats,
    ReservedTokens,
)

__all__ = [
    "NLIP_Message",
    "NLIP_SubMessage",
    "NLIP_Factory",
    "AllowedFormats",
    "ReservedTokens",
    "from_dict",
    "to_dict",
]

"""
Helper functions to convert NLIP messages to/from dicts.
Just making parsing easier.
"""


def from_dict(payload: Dict[str, Any]) -> NLIP_Message:
    return NLIP_Message.model_validate(payload)

def to_dict(message: NLIP_Message) -> Dict[str, Any]:
    return message.to_dict()