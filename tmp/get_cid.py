import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def get_cid():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    m = await db.matches.find_one({"status": "COMPLETED"})
    if m:
        print(f"Match: {m['match_id']} ({m['team1']} vs {m['team2']}) CID: {m.get('cricbuzz_id')}")
    client.close()

if __name__ == "__main__":
    asyncio.run(get_cid())
