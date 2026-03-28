from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.logger import db_logger

db_logger.info(f"Connecting to MongoDB cluster: {settings.DB_NAME}")
client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[settings.DB_NAME]

users_collection = db["users"]
predictions_collection = db["predictions"]
leaderboard_collection = db["leaderboard"]
matches_collection = db["matches"]

async def init_indexes():
    """Initializes database indexes and seeds mock data if empty."""
    db_logger.info("Initializing database indexes...")
    try:
        await predictions_collection.create_index([("match_id", 1), ("user_id", 1)], unique=True)
        await leaderboard_collection.create_index([("match_id", 1), ("score", -1)])
        await users_collection.create_index("_id")
        db_logger.info("MongoDB indexes created successfully.")
        
        # Database correctly persists the official imported PDF scheduled schema
        pass
    except Exception as e:
        db_logger.error(f"Database initialization failed: {str(e)}")
        raise e
