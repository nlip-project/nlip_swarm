import os
import httpx
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from .agents.translation import OllamaTranslationAgent

class TaskDelegation(BaseModel):
    """
    Structured Commands for delegating tasks to specific agents
    """
    agent_name: str = Field(description="Name of the agent to handle the task.")
    reasoning: str = Field(description="Reasoning behind the delegation.")
    details: str = Field(description="Specific instructions or parsed data for agent.")

class Agent(ABC):
    def __init__(self, name, description, manager=None):
        self.name = name
        self.description = description
        self.manager = manager
        self.llm = ChatOllama(model="llama3", temperature=0)

    @abstractmethod
    def handle_task(self, details: str):
        pass

class TranslationAgent(Agent):
    def __init__(self, manager=None):
        super().__init__("TranslationAgent", "Handles translation of text between languages.", manager)
        self.translator_agent = OllamaTranslationAgent()

    def handle_task(self, details: str):
        print(f"[{self.name}] handling translation task: {details}")

        try:
            translated_text = self.translator_agent.translate(details, target_locale="en")
            return f"Translated Text: {translated_text}"
        except Exception as e:
            return f"Translation failed: {str(e)}"
    


class SwarmManager:
    def __init__(self):
        self.agents = {}
        self.history = []
        self.llm = ChatOllama(model="llama3.1", temperature=0)
        self.router_chain = self._setup_router_chain()


    def register_agent(self, agent):
        self.agents[agent.name] = agent
        agent.manager = self

    def _get_agent_descriptions(self):
        descriptions = "\n".join([
            f"- **{name}**: {agent.description}" for name, agent in self.agents.items()
        ])
        return descriptions

    def _setup_router_chain(self):
        parser = JsonOutputParser(pydantic_object=TaskDelegation)
        format_instructions = parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a world-class AI Swarm Manager. Your job is to analyze user requests recieved via a frontend and route them
             to the single most appropriate specialist agent. You must output a structured JSON object according to the provided schema
             that clearly states which agent to use, your reasoning, and the specific details for the agent.
             
             Available Agents:
             {agent_descriptions}

             {format_instructions}
             """),
             ("human", "User Request: {request}")
        ])

        prompt = prompt.partial(format_instructions=format_instructions)
        router = prompt | self.llm | parser
        return router

    def route_task(self, request_from_frontend: str):
        """
        Proccesses the request and delegates using the LangChain router.
        """
        descriptions = self._get_agent_descriptions()

        raw_output = self.router_chain.invoke({
            "agent_descriptions": descriptions,
            "request": request_from_frontend
        })
        delegation_command = TaskDelegation.model_validate(raw_output)

        agent_name = delegation_command.agent_name
        details = delegation_command.details
        reasoning = delegation_command.reasoning

        print(f"[Manager] Decision: Routed to {agent_name} with reasoning: {reasoning}")
        next_agent = self.agents.get(agent_name)

        if next_agent:
            self.history.append(f"Routed to {agent_name}: {details}")
            return next_agent.handle_task(details)
        else:
            return f"Task completion failed: Agent '{agent_name}' not found."
        

swarm_manager = SwarmManager()
swarm_manager.register_agent(TranslationAgent())