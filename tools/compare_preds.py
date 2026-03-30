import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import json

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def compare_user_predictions(email):
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    print(f"Comparing predictions for: {email}\n")
    
    cursor = db.predictions.find({"user_id": email}).sort("match_id", 1)
    results = await cursor.to_list(10)
    
    for doc in results:
        match_id = doc.get("match_id")
        sessions = doc.get("sessions", {})
        print(f"Match: {match_id}")
        for s_id, data in sessions.items():
            preds = data.get("predictions", [])
            # Extract only the 'runs' values for quick comparison
            run_sequence = [p.get("runs") for p in preds]
            print(f"  Session {s_id}: {run_sequence}")

    if len(results) >= 2:
        p1 = results[0].get("sessions", {})
        p2 = results[1].get("sessions", {})
        if p1 == p2:
            print("\n🚨 WARNING: Predictions are IDENTICAL across matches!")
        else:
            print("\n✅ Predictions are unique per match.")

    client.close()

if __name__ == "__main__":
    target = "swethamuralidharan24@gmail.com"
    asyncio.run(compare_user_predictions(target))
