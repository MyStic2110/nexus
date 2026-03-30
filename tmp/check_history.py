import asyncio
import os
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
import sys
sys.path.append(os.getcwd())
from app.config import settings

async def check():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    doc = await db.match_over_history.find_one(sort=[("synced_at", -1)])
    if doc:
        print(f"Latest History Doc: {doc.get('match_id')} Over {doc.get('over')} at {doc.get('synced_at')}")
        print(f"Raw Data Keys: {list(doc.get('raw_data', {}).keys())}")
        print(f"Striker Names: {doc.get('raw_data', {}).get('batStrikerNames')}")
    else:
        print("No documents found in match_over_history.")
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
