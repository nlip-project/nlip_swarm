from __future__ import annotations

"""
Coordinator NLIP Agent

Per-session agent that discovers available NLIP agents from MOUNT_SPEC
and uses two tools to communicate:
 - connect_to_server(url)
 - send_to_server(url, message)

The coordinator learns agent NAME and capabilities by asking each URL
"What are your NLIP Capabilities?" and parsing the deterministic response:

AGENT:Name\n
CAP1:desc, CAP2:desc, ...
"""

import asyncio
from typing import Any, Dict, List
from urllib.parse import urlparse

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.base import Agent
from app.http_client.nlip_async_client import NlipAsyncClient
from app.system.mount_spec import MOUNT_SPEC


CAP_QUERY = "What are your NLIP Capabilities?"


class CoordinatorNlipAgent(Agent):
    def __init__(self, name: str = "Coordinator", model: str | None = None):
        super().__init__(name=name, model=(model or self.model))

        # url hashkey -> client
        self._clients: Dict[str, NlipAsyncClient] = {}
        # learned directory: name -> { url, capabilities: [str] }
        self._directory: Dict[str, Dict[str, Any]] = {}

        # Add a guiding instruction for tool usage
        self.add_instruction(
            "You can contact NLIP Agents using two tools: connect_to_server(url) then send_to_server(url, message)."
        )

        # Register tools
        self.add_tool(self.connect_to_server)  # type: ignore[arg-type]
        self.add_tool(self.send_to_server)     # type: ignore[arg-type]

        # Perform discovery lazily before first request
        self._discovered = False

    # ------------- tools -------------
    async def connect_to_server(self, url: str) -> str:
        """Connect to an NLIP Agent server at the given URL and cache the session."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https", "mem"):
                return f"Unsupported scheme: {parsed.scheme}"
            key = f"{parsed.scheme}://{parsed.netloc if parsed.netloc else parsed.hostname}"
            base = f"{parsed.scheme}://{parsed.netloc if parsed.netloc else parsed.hostname}/nlip"
            self._clients[key] = NlipAsyncClient.create_from_url(base)
            return f"Connected to {key}/"
        except Exception as e:
            return f"Exception: {e}"

    async def send_to_server(self, url: str, message: str) -> str:
        """Send a text NLIP message to a connected server and return its response as text."""
        parsed = urlparse(url)
        key = f"{parsed.scheme}://{parsed.netloc if parsed.netloc else parsed.hostname}"
        client = self._clients.get(key)
        if client is None:
            # Attempt implicit connect
            ok = await self.connect_to_server(url)
            if not ok.startswith("Connected to "):
                return ok
            client = self._clients.get(key)
            if client is None:
                return "Connection error"

        msg = NLIP_Factory.create_text(message)
        resp = await client.async_send(msg)
        # Return text view for simplicity
        try:
            return resp.extract_text()
        except Exception:
            # Fallback to raw dict
            return str(resp.model_dump())

    # ------------- discovery -------------
    async def _discover_agents(self) -> None:
        if self._discovered:
            return
        learned: List[str] = []
        for addr in MOUNT_SPEC:
            try:
                # Connect and ask for capabilities
                ok = await self.connect_to_server(addr)
                if not ok.startswith("Connected to "):
                    continue
                info = await self.send_to_server(addr, CAP_QUERY)
                name, caps = self._parse_capabilities(info)
                if name:
                    self._directory[name] = {"url": addr, "capabilities": caps}
                    learned.append(f"{name} -> {addr} (Capabilities: {', '.join(caps)})")
            except Exception:
                continue

        if learned:
            self.add_instruction(
                "Known NLIP Agents:\n" + "\n".join(learned) +
                "\nUse connect_to_server(url) then send_to_server(url, message) to collaborate."
            )
        self._discovered = True

    def _parse_capabilities(self, text: str) -> tuple[str | None, list[str]]:
        name: str | None = None
        caps: list[str] = []
        if not text:
            return (None, caps)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return (None, caps)
        if lines[0].lower().startswith("agent:"):
            name = lines[0].split(":", 1)[1].strip() or None
            if len(lines) > 1:
                # Comma-separated cap:desc pairs
                parts = [p.strip() for p in lines[1].split(",") if p.strip()]
                for p in parts:
                    k = p.split(":", 1)[0].strip()
                    if k:
                        caps.append(k)
        return (name, caps)

    # ------------- NLIP entry -------------
    async def handle(self, message: NLIP_Message) -> NLIP_Message:
        # Ensure discovery is performed once per session
        await self._discover_agents()

        text = message.extract_text()
        results = await self.process_query(text)
        out = "\n".join(results)
        resp = NLIP_Factory.create_text(out, label=getattr(message, "label", ""))
        resp.messagetype = "response"
        return resp

