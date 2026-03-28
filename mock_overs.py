import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

async def mock_death_overs():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    match_id = "ipl_2026_01"
    
    # Over 19 - Session 1
    o19 = {
        "match_id": match_id,
        "session_id": 1,
        "over": 19,
        "balls": ["1", "4", "W", "0", "6", "1"],
        "total_runs": 12
    }
    
    # Over 20 - Session 1
    o20 = {
        "match_id": match_id,
        "session_id": 1,
        "over": 20,
        "balls": ["0", "W", "6", "6", "4", "W"],
        "total_runs": 16
    }
    
    for o in [o19, o20]:
        await db.live_match_overs.update_one(
            {"match_id": o["match_id"], "session_id": o["session_id"], "over": o["over"]},
            {"$set": o},
            upsert=True
        )
    
    print("Injected Mock Death Overs (19 & 20) for ipl_2026_01 Session 1.")
    client.close()

if __name__ == '__main__':
    asyncio.run(mock_death_overs())
