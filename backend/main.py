from fastapi import FastAPI
from app.routers.scenarios import router as scenarios_router
from app.routers.negotiation import router as negotiation_router
from app.routers.websocket import router as websocket_router
app = FastAPI(
    title="Multi-Agent Negotiation Simulator",
    description="Backend API for Multi-Agent Negotiation",
    version="1.0.0"
)
# Register negotiation routes
app.include_router(negotiation_router)
app.include_router(scenarios_router)
app.include_router(websocket_router)

@app.get("/")
def home():
    return {
        "message": "Multi-Agent Negotiation Simulator Backend Running!"
    }
