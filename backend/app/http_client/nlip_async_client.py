import httpx
from urllib.parse import urlparse
from nlip_sdk.nlip import NLIP_Message
from app import MEM_APP_TBL

class NlipAsyncClient:
    def __init__(self, base_url: str):
        u = urlparse(base_url)

        if u.scheme == "mem":
            new_url = u._replace(scheme="http").geturl()
            self.base_url = new_url

            app = MEM_APP_TBL.get(u.hostname, None)
            if app is None:
                raise Exception(f"App named {u.hostname} in {base_url} not found.")
            transport = httpx.ASGITransport(app=app)
            self.client = httpx.AsyncClient(transport=transport)
        else:
            self.base_url = base_url
            self.client = httpx.AsyncClient()

    @classmethod
    def create_from_url(cls, base_url: str):
        return NlipAsyncClient(base_url)
    
    async def async_send(self, msg: NLIP_Message) -> NLIP_Message:
        msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg.model_dump()
        response = await self.client.post(self.base_url, json=msg_dict, timeout=120.0, follow_redirects=True)

        # Capture body before parsing so we can include it in any error.
        text_body = await response.aread()
        body_str = text_body.decode(errors="replace") if isinstance(text_body, (bytes, bytearray)) else str(text_body)

        # Raise HTTP errors with body context for easier debugging.
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            preview = body_str[:500] if body_str else "(empty body)"
            raise Exception(f"HTTP {response.status_code} from {self.base_url}: {preview}") from exc

        if not body_str.strip():
            raise Exception(f"Empty response from {self.base_url}; expected NLIP JSON.")

        try:
            data = response.json()
        except Exception as exc:
            preview = body_str[:500]
            raise Exception(f"Non-JSON response from {self.base_url}: {preview}") from exc

        return NLIP_Message(**data)