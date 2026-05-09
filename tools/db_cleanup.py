import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def force_cleanup():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["live_match_overs"]
    
    print("Nexus Database Sanitization & Deduplication...")

    # 1. Deduplication
    pipeline = [
        {"$group": {
            "_id": {"match_id": "$match_id", "session_id": "$session_id", "over": "$over"},
            "uniqueIds": {"$addToSet": "$_id"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = await collection.aggregate(pipeline).to_list(100)
    for dupe in duplicates:
        # Keep the first one, delete the rest
        ids_to_delete = dupe["uniqueIds"][1:]
        print(f"Deleting {len(ids_to_delete)} duplicates for Match {dupe['_id']['match_id']} Over {dupe['_id']['over']}")
        await collection.delete_many({"_id": {"$in": ids_to_delete}})

    # 2. Trim 7-ball artifacts
    # Any over with > 6 legal balls where the last ball is '0'
    cursor = collection.find({})
    async for doc in cursor:
        balls = doc.get("balls", [])
        legal = [b for b in balls if b not in ['Wd', 'Nb']]
        if len(legal) > 6 and balls[-1] == '0':
            new_balls = balls[:-1]
            print(f"Trimming artifact from Match {doc['match_id']} Over {doc['over']}")
            await collection.update_one({"_id": doc["_id"]}, {"$set": {"balls": new_balls}})

    # 3. Final Match Registry Correction
    # Match 1 (RCB vs SRH) -> Completed
    # Match 2 (MI vs KKR) -> Completed
    print("Finalizing match statuses...")
    await db.matches.update_one({"match_id": "ipl_2026_01"}, {"$set": {"status": "COMPLETED", "cricbuzz_id": "149618"}})
    await db.matches.update_one({"match_id": "ipl_2026_02"}, {"$set": {"status": "COMPLETED", "cricbuzz_id": "149629"}})

    client.close()
    print("Sanitization complete.")

if __name__ == "__main__":
    asyncio.run(force_cleanup())
