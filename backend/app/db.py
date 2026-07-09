from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGO_URI)
db: AsyncIOMotorDatabase = client[settings.DB_NAME]
