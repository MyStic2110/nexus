from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.logger import db_logger

if not settings.MONGO_URI:
    db_logger.error("MONGO_URI is not set! Check your environment variables.")
    raise ValueError("MONGO_URI environment variable is required")

db_logger.info(f"Connecting to MongoDB cluster: {settings.DB_NAME}")
try:
    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.DB_NAME]
except Exception as e:
    db_logger.error(f"Failed to initialize MongoDB client: {str(e)}")
    raise e

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
