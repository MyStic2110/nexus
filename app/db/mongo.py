from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.logger import db_logger

raw_uri = settings.MONGO_URI.strip().strip("'").strip('"')

if not raw_uri or not (raw_uri.startswith("mongodb://") or raw_uri.startswith("mongodb+srv://")):
    masked_uri = (raw_uri[:10] + "...") if raw_uri else "EMPTY"
    db_logger.error(f"Invalid MONGO_URI detected (Length: {len(raw_uri)}): {masked_uri}")
    db_logger.error("Ensure your Railway environment variable MONGO_URI starts with 'mongodb://' or 'mongodb+srv://' and has no quotes.")
    raise ValueError(f"Invalid MONGO_URI scheme. Received: {masked_uri}")

db_logger.info(f"Connecting to MongoDB cluster: {settings.DB_NAME}")
try:
    client = AsyncIOMotorClient(raw_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.DB_NAME]
except Exception as e:
    db_logger.error(f"Failed to initialize MongoDB client: {str(e)}")
    raise e

users_collection = db["users"]
predictions_collection = db["predictions"]
leaderboard_collection = db["leaderboard"]
matches_collection = db["matches"]
session_scores_collection = db["session_scores"]

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
