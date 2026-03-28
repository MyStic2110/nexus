import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.ipl_game

async def run():
    print("Fetching scores for current match (ipl_2026_01)...")
    
    # User's Session 1 Score
    s1 = await db.session_scores.find_one({"match_id": "ipl_2026_01", "session_id": 1, "user_id": "muralidharan@evvotechnology.com"})
    print("Session 1 Points:", s1.get("points") if s1 else "No record")
    
    # User's Session 2 Score
    s2 = await db.session_scores.find_one({"match_id": "ipl_2026_01", "session_id": 2, "user_id": "muralidharan@evvotechnology.com"})
    print("Session 2 Points:", s2.get("points") if s2 else "No record")
    
    # Match Global Score
    match = await db.matches.find_one({"match_id": "ipl_2026_01"})
    print("\nLive Match Current Score:", match.get("current_score", "N/A"))
    print("Live Match Current Over:", match.get("current_over", "N/A"))
    print("Live Match Current Innings:", match.get("innings", "N/A"))
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
