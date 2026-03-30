import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(os.getcwd())
from app.config import settings

async def main():
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.DB_NAME]
        
        match = await db.matches.find_one({"match_id": "ipl_2026_03"})
        if match:
             print(f"Match ID: {match.get('match_id')}")
             print(f"Status: {match.get('status')}")
             print(f"Current Score: {match.get('current_score')}")
             print(f"Current Over: {match.get('current_over')}")
             print(f"Innings: {match.get('innings')}")
             print(f"Team1: {match.get('team1')} vs Team2: {match.get('team2')}")
             print(f"Live Stats: {match.get('live_stats')}")
        else:
             print("Match not found.")

        # Check live overs
        overs = await db.live_match_overs.find({"match_id": "ipl_2026_03"}).sort("over", -1).to_list(5)
        print("\nLast 5 Overs In DB:")
        for o in overs:
             print(f"Over {o.get('over')}, Score: {o.get('current_score')}, Balls: {o.get('balls')}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
