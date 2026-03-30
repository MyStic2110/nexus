import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def check_schema():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    
    # Check session_scores record
    score = await db.session_scores.find_one()
    print("Session Score Example:")
    print(score)
    
    # Check match record for reference
    match = await db.matches.find_one({"match_id": score.get("match_id")})
    print("\nMatch Example:")
    print(match)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
