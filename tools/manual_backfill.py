import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.auto_agent_cricbuzz import run_cricbuzz_pulse

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def force_backfill():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Correcting CIDs based on match schedule
    print("Correcting match registry for Backfill...")
    
    # Match 1: RCB vs SRH (CID 149618)
    await db.matches.update_one(
        {"match_id": "ipl_2026_01"},
        {"$set": {"cricbuzz_id": "149618", "status": "LIVE"}} # Temporarily LIVE to trigger sync
    )
    
    # Match 2: MI vs KKR (CID 149629)
    await db.matches.update_one(
        {"match_id": "ipl_2026_02"},
        {"$set": {"cricbuzz_id": "149629", "status": "LIVE"}}
    )

    print("Executing Nexus API Pulse with Backfill...")
    await run_cricbuzz_pulse()
    
    print("\nVerifying Gaps for Match 1...")
    overs1 = await db.live_match_overs.distinct("over", {"match_id": "ipl_2026_01", "session_id": 1})
    print(f"Match 1 (Inn 1) Overs: {sorted(overs1)}")
    
    overs2 = await db.live_match_overs.distinct("over", {"match_id": "ipl_2026_01", "session_id": 2})
    print(f"Match 1 (Inn 2) Overs: {sorted(overs2)}")

    client.close()

if __name__ == "__main__":
    asyncio.run(force_backfill())
