import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

async def sync_production_prep():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    match_id = "ipl_2026_01"
    
    # 1. Clear Mock Overs (19, 20) for session 1
    # Note: In a real match, these would be overwritten by the Cricbuzz agent eventually,
    # but we'll clear them now to be safe.
    res_overs = await db.live_match_overs.delete_many(
        {"match_id": match_id, "over": {"$in": [19, 20]}}
    )
    print(f"Cleared {res_overs.deleted_count} mock over records.")
    
    # 2. Reset All User Scores to 0
    res_users = await db.users.update_many({}, {"$set": {"score": 0}})
    print(f"Reset {res_users.modified_count} user scores to 0.")
    
    # 3. Clear All Session Scores
    res_session = await db.session_scores.delete_many({})
    print(f"Cleared {res_session.deleted_count} session-level score history.")

    client.close()

if __name__ == '__main__':
    asyncio.run(sync_production_prep())
