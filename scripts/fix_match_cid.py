import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def check_match_cid():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    print(f"Checking current matches in {DB_NAME}...")
    cursor = db.matches.find({"status": {"$in": ["UPCOMING", "LIVE"]}})
    matches = await cursor.to_list(10)
    
    if not matches:
        print("No upcoming or live matches found.")
    else:
        for m in matches:
            print(f"Match: {m['match_id']} | Teams: {m.get('team1')} vs {m.get('team2')} | CID: {m.get('cricbuzz_id')} | Status: {m.get('status')}")

    # Special check for the one the user mentioned
    target_cid = "149629"
    # Let's find match where current CID is 149618 (based on browser state earlier)
    m18 = await db.matches.find_one({"cricbuzz_id": "149618"})
    if m18:
        print(f"\nFound match with old CID 149618: {m18['match_id']} ({m18.get('team1')} vs {m18.get('team2')})")
        print(f"Updating CID to {target_cid}...")
        result = await db.matches.update_one({"match_id": m18['match_id']}, {"$set": {"cricbuzz_id": target_cid}})
        print(f"Update Result: {result.modified_count} record updated.")
    else:
        print(f"\nCould not find match with CID 149618.")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_match_cid())
