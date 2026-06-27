import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as aioredis

from app.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.websocket.connection_manager import manager
from app.api.routes import router as api_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    await connect_to_mongo()
    
    # Connect to Redis
    logger.info(f"Connecting to Redis at {settings.redis_url}...")
    app.state.redis = aioredis.from_url(settings.redis_url)
    await app.state.redis.ping()
    logger.info("Connected to Redis successfully.")
    
    # Start Redis listener background task for WebSockets
    await manager.start_redis_listener(app.state.redis)
    
    yield
    
    # Shutdown lifecycle
    await manager.stop_redis_listener()
    await app.state.redis.close()
    await close_mongo_connection()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title="OpsPulse API",
    description="Real-Time Production Monitoring & Intelligent Alerting Platform backend",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API router
app.include_router(api_router, prefix="/api")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect data from the client, but keep the connection open
            # and detect client disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error on connection: {e}")
        manager.disconnect(websocket)
