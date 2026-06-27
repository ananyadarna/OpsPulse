import asyncio
import json
import logging
from typing import List
from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.pubsub_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)

    async def start_redis_listener(self, redis_client: Redis):
        """
        Starts a background task that listens to Redis channels
        and broadcasts messages to all connected clients.
        """
        self.pubsub_task = asyncio.create_task(self._listen_redis(redis_client))
        logger.info("Started Redis Pub/Sub background listener task.")

    async def stop_redis_listener(self):
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped Redis Pub/Sub background listener task.")

    async def _listen_redis(self, redis_client: Redis):
        pubsub = redis_client.pubsub()
        # Listen to both parsed logs and anomaly alerts
        await pubsub.subscribe("opspulse:logs", "opspulse:alerts")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"].decode()
                    data = message["data"].decode()
                    
                    # Wrap message in standard packet format
                    packet = {
                        "event": "log" if channel == "opspulse:logs" else "alert",
                        "data": json.loads(data)
                    }
                    await self.broadcast(json.dumps(packet))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Redis listener loop: {e}")
        finally:
            await pubsub.unsubscribe("opspulse:logs", "opspulse:alerts")
            await pubsub.close()

manager = ConnectionManager()
