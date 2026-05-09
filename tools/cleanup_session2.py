import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def cleanup():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    match_id = "ipl_2026_07"
    session_id = 2
    
    print(f"[NEXUS-CLEANUP] Removing premature points for {match_id} Session {session_id}...")
    
    # 1. Remove from session_scores
    result = await db.session_scores.delete_many({"match_id": match_id, "session_id": session_id})
    print(f"  -> Deleted {result.deleted_count} session score records from 'session_scores'.")

    # 2. Remove incorrect match overs from live_match_overs
    # This is crucial as it prevents calculate_points from re-triggering based on stale data.
    ovr_result = await db.live_match_overs.delete_many({"match_id": match_id, "session_id": session_id})
    print(f"  -> Deleted {ovr_result.deleted_count} stale over records from 'live_match_overs'.")
    
    # 3. Recalculate global user scores to reflect the removal
    print("  -> Recalculating global user standings...")
    users_cursor = db.users.find({})
    async for user in users_cursor:
        u_id = user["_id"]
        pipeline = [
            {"$match": {"user_id": u_id}},
            {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}}}
        ]
        agg_result = await db.session_scores.aggregate(pipeline).to_list(1)
        new_total = agg_result[0]["total"] if agg_result else 0
        
        if user.get("score") != new_total:
             await db.users.update_one({"_id": u_id}, {"$set": {"score": new_total}})
             print(f"     Updated User {u_id}: {user.get('score')} -> {new_total}")

    print("[NEXUS-CLEANUP] Completed.")
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
