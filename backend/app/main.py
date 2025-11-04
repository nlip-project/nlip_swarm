from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .manager import swarm_manager
from nlip_sdk.nlip import NLIP_Message

app = FastAPI(
    title="Local Agent Swarm API",
    description="API for managing a swarm of local AI agents using NLIP SDK"
)

@app.post("/nlip")
def process_frontend_request(payload: NLIP_Message):
    try:
        result = swarm_manager.route_task(payload.to_json())
        return {
            "status": "success",
            "request_recieved": payload.to_dict(),
            "response": result,
            "history": swarm_manager.history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)