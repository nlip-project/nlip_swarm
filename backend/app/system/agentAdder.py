# Parser to create new servers + agents from a json spec and add them to coordinator. Allowing user to customize agents without changing code.
# Each object is a server to be created, with an agent to be added to the coordinator. The coordinator will route requests to the appropriate agent based on the URL path.

# Example spec:
# {
#     "scheme": "url scheme to use for mounting the agent, e.g. mem or http",
#     "suffix": "suffix to identify server, e.g. NLIPCoordinatorCookie
#     "identifier": "if scheme is mem, this is the identifier for the in-memory server, if http, this is ip and port to bind to, e.g. 127.0.0.1:8000",
#     "session_manager": "just use default one for now, not sure how to specify custom functions here"
#      "agent":
#         {
#           "name": "Name of Agent",
#           "model": "LLM model to use",
#           "instruction": "System instructions for the agent",
#           "tools": ["list", "of", "tool", "names"],
#          }
#
import json

from app.agents.base import Agent
from app.http_server.nlip_session_server import SessionManager as baseSessionManager, NlipSessionServer
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

        # Define the URL based on the scheme and identifier
        if scheme == "mem":
            url = f"{scheme}://{identifier}/"
        elif scheme == "http":
            url = f"http://{identifier}/"
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")


        # For simplicity, we'll just use the default session manager for now, probably best to make a generic functional session manager that can be configured via the spec in the future
        # then won't have to worry about custom session manager code in the backend, just specify the agent and tools in the spec and the coordinator will handle routing and tool calling
        SessionManager = baseSessionManager

        # Parse agent specifications
        agent_spec = server_spec.get("agent", {})
        name = agent_spec.get("name")
        model = agent_spec.get("model")
        instruction = agent_spec.get("instruction", "")
        tools = agent_spec.get("tools", [])

        # Create a new agent instance and add it to the session manager
        agent = Agent(name, model, instruction, tools)
        SessionManager.agent = agent

        # Create the server app using the session manager
        app = NlipSessionServer(suffix, SessionManager)

        # Return list of servers to be mounted by the coordinator
        custom_servers.append((app, url))
    return custom_servers
        
