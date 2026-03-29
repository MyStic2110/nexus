import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check():
    load_dotenv()
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DB_NAME", "ipl_game")
    
    print(f"Connecting to {MONGO_URI} [{DB_NAME}]")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    count = await db.matches.count_documents({})
    print(f"Seeded Matches Count: {count}")
    
    if count > 0:
        first = await db.matches.find_one({})
        print(f"Sample: {first['team1']} vs {first['team2']} on {first['date']}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
