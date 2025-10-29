import logging

from fastapi import FastAPI
from nlip_sdk.nlip import NLIP_Message
from nlip_sdk import errors as err
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
        response_correlator = self.execute(message)
        response = await response_correlator if inspect.isawaitable(response_correlator) else response_correlator

        token = response.extract_conversation_token()
        if other_correlator is not None:
            response.add_conversation_token(other_correlator, True)
        else:
            if token is not None:
                local_correlator = self.get_correlator()
            if local_correlator is not None:
                response.add_conversation_token(local_correlator)
        return response
    
    async def end(self):
        self._print_withcorrelator("NLIP Session ended")

    def get_logger(self):
        return logger
    
class NLIP_Application:
    async def startup(self):
        raise err.UnImplementedError(f"startup", self.__class__.__name__)
    
    async def shutdown(self):
        raise err.UnImplementedError(f"shutdown", self.__class__.__name__)
    
    def get_logger(self):
        return logger
    
def register_nlip_routes(app: FastAPI, nlip_app: NLIP_Application):