import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def verify_user(email):
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    print(f"\n[NEXUS-VERIFY] Checking performance for: {email}")
    
    # 1. Fetch user global score
    user_doc = await db.users.find_one({"_id": email})
    global_score = user_doc.get("score", 0) if user_doc else "NOT FOUND"
    print(f"Global Score in 'users' collection: {global_score} pts")
    
    # 2. Fetch all session scores
    print("\nDetailed Session Breakdown:")
    print("-" * 60)
    print(f"{'Match ID':<15} | {'Sess':<4} | {'Points':<6}")
    print("-" * 60)
    
    cursor = db.session_scores.find({"user_id": email}).sort([("match_id", 1), ("session_id", 1)])
    total_calculated = 0
    async for score in cursor:
        m_id = score.get("match_id")
        s_id = score.get("session_id")
        pts = score.get("points", 0)
        total_calculated += pts
        print(f"{m_id:<15} | {s_id:<4} | {pts:<6}")
        
    print("-" * 60)
    print(f"Sum of session scores: {total_calculated} pts")
    
    if global_score != total_calculated:
        print(f"\n[WARNING] Score mismatch! Global={global_score}, Calculated={total_calculated}")
    else:
        print("\n[OK] Global score matches session totals.")

    client.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target_email = sys.argv[1]
    else:
        target_email = "swethamuralidharan24@gmail.com"
    asyncio.run(verify_user(target_email))
