from datetime import datetime
from app.db.mongo import users_collection
from app.logger import auth_logger

async def create_or_get_user(email: str):
    auth_logger.info(f"Database sync check for user: {email}")
    user = await users_collection.find_one({"_id": email})
    if not user:
        auth_logger.warning(f"User {email} not found in database. Initializing new Nexus profile...")
        username = email.split("@")[0]
        user = {
            "_id": email,
            "username": username,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        await users_collection.insert_one(user)
        auth_logger.info(f"New profile successfully committed: {username}")
    else:
        auth_logger.info(f"Existing profile found for {email}. Updating timestamp.")
        await users_collection.update_one(
            {"_id": email},
            {"$set": {"last_login": datetime.utcnow()}}
        )
    return user
