# Parser to create new servers + agents from a json spec and add them to coordinator. Allowing user to customize agents without changing code.
# Each object is a server to be created, with an agent to be added to the coordinator. The coordinator will route requests to the appropriate agent based on the URL path.

# Example spec:
# {
#     "scheme": "url scheme to use for mounting the agent, e.g. mem or http",
#     "suffix": "suffix to identify server, e.g. NLIPCoordinatorCookie
#     "identifier": "if scheme is mem, this is the identifier for the in-memory server, if http, this is ip and port to bind to, e.g. 127.0.0.1:8000",
#     "session_manager": "can pick from predefined session managers with different capabilities. Custom session managers are not supported in this implementation as they would require code changes. Options are coordinator, image, text, translate, sound, or default.",
#      "agent":
#         {
#           "name": "Name of Agent",
#           "model": "LLM model to use",
#           "instruction": "System instructions for the agent",
#           "tools": ["list", "of", "tool", "names"],
#          }
#
import json
from typing import Callable

from app.agents.base import Agent
from app.agents.coordinator_nlip_agent import connect_to_server, send_to_server, get_all_capabilities
from app.http_server.nlip_session_server import SessionManager as baseSessionManager, NlipSessionServer

# New servers can be created via combinations of existing session managers and agents
# Possibly allow custom session manager and agent code but not sure how to implement without direct code changes
from app.servers.coordinator_server import NlipManager
from app.servers.image_server import ImageSessionManager
from app.servers.text_server import TextSessionManager
from app.servers.translate_server import TranslationManager
from app.servers.sound_server import SoundSessionManager
from app.system.config import MODELS

TOOL_REGISTRY: dict[str, Callable] = {
    "connect_to_server": connect_to_server,
    "send_to_server": send_to_server,
    "get_all_capabilities": get_all_capabilities,
}


def _resolve_tools(raw_tools: list) -> list[Callable]:
    resolved: list[Callable] = []
    for entry in raw_tools:
        if callable(entry):
            resolved.append(entry)
            continue
        if not isinstance(entry, str):
            continue
        fn = TOOL_REGISTRY.get(entry)
        if fn:
            resolved.append(fn)
        else:
            print(f"Skipping unknown tool '{entry}' in agent spec")
    return resolved


def add_agents_from_spec(spec_json_file: str) -> list[tuple[NlipSessionServer, str]]:
    print(f"Adding agents from spec file: {spec_json_file}")
    custom_servers = []

    with open(spec_json_file, 'r') as file:
        spec = json.load(file)
    for server_spec in spec:
        # Parse server specifications
        scheme = server_spec.get("scheme")
        suffix = server_spec.get("suffix")
        identifier = server_spec.get("identifier")
        session_manager_type = server_spec.get("session_manager", "default")
        if not scheme or not suffix or not identifier or not session_manager_type:
            raise ValueError("Each server spec must include 'scheme', 'suffix', 'identifier', and 'session_manager'")

        # Define the URL based on the scheme and identifier
        if scheme == "mem":
            url = f"{scheme}://{identifier}/"
        elif scheme == "http":
            url = f"http://{identifier}/"
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")

        if session_manager_type == "default":
            SessionManager = baseSessionManager
        else: # For simplicity, we only allow choosing from predefined session managers. Custom session manager code would require code changes and is not supported in this implementation.
            SessionManager = {
                "coordinator": NlipManager,
                "image": ImageSessionManager,
                "text": TextSessionManager,
                "translate": TranslationManager,
                "sound": SoundSessionManager,
            }.get(session_manager_type)


        # Parse agent specifications
        agent_spec = server_spec.get("agent", {})
        name = agent_spec.get("name")
        if not name:
            raise ValueError("Each server spec agent must include 'name'")
        model = agent_spec.get("model") or MODELS.get('base_model', 'cerebras/llama3.3-70b')
        instruction = agent_spec.get("instruction", "")
        tools = _resolve_tools(agent_spec.get("tools", []))

        class SpecSessionManager(SessionManager):
            def __init__(
                self,
                _name=name,
                _model=model,
                _instruction=instruction,
                _tools=tools,
                **kwargs,
            ):
                super().__init__(**kwargs)
                # Per-session agent instance prevents cross-agent state bleed.
                self.agent = Agent(_name, _model, _instruction, list(_tools))

        # Create the server app using the session manager
        app = NlipSessionServer(suffix, SpecSessionManager)

        # Return list of servers to be mounted by the coordinator
        custom_servers.append((app, url))
    return custom_servers
        
