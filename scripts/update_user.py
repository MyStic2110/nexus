import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def update():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client.ipl_game
    res = await db.users.update_one(
        {"_id": "muralidharan@evvotechnology.com"},
        {"$set": {"score": 485}}
    )
    if res.matched_count:
        print("SYNC: User 'muralidharan' performance points locked at 485 PTS.")
    else:
        # Create user if not exists to demo
        await db.users.insert_one({"_id": "muralidharan@evvotechnology.com", "username": "Murali", "score": 485})
        print("SEED: User 'muralidharan' created in Nexus Registry with 485 PTS.")
    client.close()

if __name__ == "__main__":
    asyncio.run(update())
