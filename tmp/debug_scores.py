import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def check_matches():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    cursor = db.matches.find({"status": "COMPLETED"})
    async for m in cursor:
        print(f"Match: {m['match_id']} ({m['team1']} vs {m['team2']})")
        print(f"  T1 Score: {m.get('team1_final_score')}")
        print(f"  T2 Score: {m.get('team2_final_score')}")
        print(f"  Winner: {m.get('winner_team')}")
        print(f"  Innings in API: {m.get('innings')}")
        print("-" * 30)
    client.close()

if __name__ == "__main__":
    asyncio.run(check_matches())
