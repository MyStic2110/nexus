import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

async def fix_and_verify():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    
    # 1. Fix missing session_ids for overs
    res = await db.live_match_overs.update_many(
        {"match_id": "ipl_2026_01", "session_id": {"$exists": False}},
        {"$set": {"session_id": 1}}
    )
    print(f"Fixed {res.modified_count} overs by adding session_id=1.")
    
    # 2. Reset user total scores to 0 (to re-calculate clean)
    await db.users.update_many({}, {"$set": {"score": 0}})
    print("Reset all user scores to 0 for a clean test run.")
    
    # 3. Clear session_scores too
    await db.session_scores.delete_many({"match_id": "ipl_2026_01"})
    print("Cleared session_scores for ipl_2026_01.")

    client.close()

if __name__ == '__main__':
    asyncio.run(fix_and_verify())
