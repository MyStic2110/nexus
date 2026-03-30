import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def check_leaderboard():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    
    print("Database Collections:")
    cols = await db.list_collection_names()
    print(cols)
    
    # Check users and their scores
    print("\nUsers Leaderboard (Top 5):")
    users = await db.users.find({}).sort("score", -1).limit(5).to_list(10)
    for u in users:
        print(f"  {u.get('_id')} -> {u.get('score')} pts")
    
    # Check if there is a 'leaderboard' collection
    if 'leaderboard' in cols:
        print("\nLeaderboard Collection entries:")
        entries = await db.leaderboard.find({}).limit(5).to_list(5)
        for e in entries:
            print(f"  {e}")
    else:
        print("\nNo 'leaderboard' collection found.")
        
    # Check session_scores again
    print("\nSession Scores Count for today's match:")
    sc_count = await db.session_scores.count_documents({"match_id": "ipl_2026_03"})
    print(sc_count)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_leaderboard())
