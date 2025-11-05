from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi import Request
from nlip_sdk.nlip import NLIP_Factory, AllowedFormats
from app.nlip_adapter import from_dict, to_dict
from app.registry import AgentRegistry
from app.agents.swarm_manager import SwarmManager
from app.agents.translation import OllamaTranslationAgent
from langchain_ollama import ChatOllama
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
ROUTER_TEMPERATURE = 0

router_llm = ChatOllama(
    base_url=OLLAMA_URL,
    model=OLLAMA_MODEL,
    temperature=ROUTER_TEMPERATURE,
)

translation_agent = (OllamaTranslationAgent(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
))


registry = AgentRegistry([
    translation_agent,
])

swarm_manager = SwarmManager(registry=registry, router_llm=router_llm, translator=translation_agent)

app = FastAPI()

@app.get("/capabilities")
def capabilities():
    """
    Report all registered agents + capabilities in an NLIP JSON message.
    """
    caps = {
        agent.name: agent.capabilities
        for agent in registry.agents
    }
    msg = NLIP_Factory.create_json(caps, messagetype="response")
    return JSONResponse(msg.to_dict())


@app.post("/nlip")
async def nlip(request: Request):
    """
    Entry point. Receives NLIP messages.
    Always delegates to Swarm Manager.
    """
    payload = await request.json()
    incoming = from_dict(payload)
    result = await swarm_manager.handle(incoming)
    return JSONResponse(to_dict(result))
