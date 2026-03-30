import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def check_inconsistencies():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["live_match_overs"]

    print(f"Checking collection: {DB_NAME}.live_match_overs\n")

    # 1. Total records
    total_docs = await collection.count_documents({})
    print(f"Total over records found: {total_docs}")

    # 2. Group by match and session to check sequences
    pipeline = [
        {"$group": {
            "_id": {"match_id": "$match_id", "session_id": "$session_id"},
            "overs": {"$push": "$over"},
            "count": {"$sum": 1}
        }}
    ]
    
    results = await collection.aggregate(pipeline).to_list(100)
    
    for res in results:
        m_id = res["_id"]["match_id"]
        s_id = res["_id"]["session_id"]
        overs = sorted(res["overs"])
        
        print(f"\nMatch: {m_id} | Session: {s_id}")
        print(f"  Overs recorded: {len(overs)} ({min(overs) if overs else 'N/A'} to {max(overs) if overs else 'N/A'})")
        
        # Check for gaps
        if overs:
            expected = list(range(min(overs), max(overs) + 1))
            missing = [o for o in expected if o not in overs]
            if missing:
                print(f"  [GAP] Gaps detected in over sequence: {missing}")
            else:
                print(f"  [OK] Sequence is continuous.")

        # Check for ball counts in each over
        match_overs = collection.find({"match_id": m_id, "session_id": s_id})
        async for over_doc in match_overs:
            balls = over_doc.get("balls", [])
            legal_balls = [b for b in balls if b not in ["Wd", "Nb"]]
            over_num = over_doc["over"]
            
            if len(legal_balls) < 6:
                # Note: The last recorded over might be incomplete if the match is LIVE
                print(f"  [INCOMPLETE] Over {over_num} has only {len(legal_balls)} legal balls (Raw: {balls})")
            elif len(legal_balls) > 6:
                 print(f"  [ERROR] Over {over_num} has TOO MANY legal balls: {len(legal_balls)} (Raw: {balls})")

    # 3. Check for documents missing required fields
    missing_fields = await collection.count_documents({
        "$or": [
            {"match_id": {"$exists": False}},
            {"session_id": {"$exists": False}},
            {"over": {"$exists": False}},
            {"balls": {"$exists": False}}
        ]
    })
    if missing_fields > 0:
        print(f"\n[ERROR] Detected {missing_fields} documents with missing required fields!")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_inconsistencies())
