from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_client = MongoDB()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db_client.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_client.db = db_client.client[settings.MONGO_DB]
    logger.info("Connected to MongoDB.")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_client.client:
        db_client.client.close()
    logger.info("MongoDB connection closed.")

def get_database():
    return db_client.db
