import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def check():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    doc = await db.live_match_overs.find_one({"match_id": "ipl_2026_07", "session_id": 2, "over": 20})
    if doc:
        print(f"Record found: {doc.get('over')} over with {len(doc.get('balls', []))} balls")
    else:
        print("Record NOT found.")
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
