import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from nlip_sdk.nlip import NLIP_Message
from nlip_sdk import errors as err
from ..routes.nlip import router as nlip_router
from ..routes.health import router as health_router
import secrets
import inspect

logger = logging.getLogger('uvicorn.error')

class NLIP_Session:

    def set_correlator(self):
        self.correlator = secrets.token_urlsafe()

    def get_correlator(self):
        if hasattr(self, 'correlator'):
            return self.correlator
        return None
    
    def _print_withcorrelator(self, message: str):
        correlator = self.get_correlator()
        if correlator is not None:
            message = message + f" [correlator={self.correlator}]"
        logger.info(message)

    def log_info(self, message: str):
        self._print_withcorrelator(message)

    async def start(self):
        self._print_withcorrelator("NLIP Session started")

    async def execute(self, message: NLIP_Message) -> NLIP_Message:
        raise err.UnImplementedError("execute", self.__class__.__name__)
    
    async def correlated_execute(self, message: NLIP_Message) -> NLIP_Message:
        other_correlator = message.extract_conversation_token()
        response__or_correlator = self.execute(message)
        response = await response__or_correlator if inspect.isawaitable(response__or_correlator) else response__or_correlator

        existing_token = response.extract_conversation_token()
        if other_correlator is not None:
            response.add_conversation_token(other_correlator, True)
        else:
            if existing_token is None:
                local_correlator = self.get_correlator()
                if local_correlator is not None:
                    response.add_conversation_token(local_correlator)
        return response
    
    async def stop(self):
        self._print_withcorrelator("NLIP Session stopped")

    def get_logger(self):
        return logger
    
class NLIP_Application:
    async def startup(self):
        raise err.UnImplementedError(f"startup", self.__class__.__name__)
    
    async def shutdown(self):
        raise err.UnImplementedError(f"shutdown", self.__class__.__name__)
    
    def get_logger(self):
        return logger

    def create_session(self) -> NLIP_Session:
        raise err.UnImplementedError(f"create_session", self.__class__.__name__)
    
    def add_session(self, session: NLIP_Session) -> None:
        if hasattr(self, 'sessions'):
            if self.sessions is None:
                self.sessions = list()
        else:
            self.sessions = list()
        self.sessions.append(session)

    def remove_session(self, session: NLIP_Session) -> None:
        if hasattr(self, 'sessions'):
            self.sessions.remove(session)

class SafeApplication(NLIP_Application):

    async def startup(self):
        logger.info(f"Called startup on {self.__class__.__name__}")

    async def shutdown(self):
        logger.info(f"Called shutdown on {self.__class__.__name__}")


def create_app(client: NLIP_Application) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        startup_res = client.startup()
        if inspect.isawaitable(startup_res):
            await startup_res
        
        client.sessions = list()
        app.state.client_app = client
        yield

        for session in client.sessions:
            try:
                stop_res = session.stop()
                if inspect.isawaitable(stop_res):
                    await stop_res
            except Exception as e:
                logger.error(f"Error stopping session: {e}")

        client.sessions = list()

        shutdown_res = client.shutdown()
        if inspect.isawaitable(shutdown_res):
            await shutdown_res
        
    app = FastAPI(lifespan=lifespan)
    app.include_router(nlip_router, prefix="/nlip")
    app.include_router(health_router, prefix="/health")

    return app
    
def setup_server(client: NLIP_Application) -> FastAPI:
    return create_app(client)