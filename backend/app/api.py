from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.nlip import router as nlip_router

def create_app() -> FastAPI:
    app = FastAPI(title="NLIP Swarm Registrar", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "nlip_swarm_registrar"}
    
    app.include_router(nlip_router)
    return app

app = create_app()