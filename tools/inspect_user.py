import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import json

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipl_game")

async def inspect_user_data(email):
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    print(f"Inspection for: {email}\n")
    
    # Check user record
    user = await db.users.find_one({"_id": email})
    if user:
        print(f"User Record: {user}")
    else:
        print("User not found in users collection.")

    # Check predictions
    print("\nPredictions Summary:")
    cursor = db.predictions.find({"user_id": email})
    async for pred in cursor:
        match_id = pred.get("match_id")
        sessions = pred.get("sessions", {})
        print(f"Match: {match_id}")
        for s_id, data in sessions.items():
            preds = data.get("predictions", [])
            print(f"  Session {s_id}: {len(preds)} predictions")

    client.close()

if __name__ == "__main__":
    target = "swethamuralidharan24@gmail.com"
    asyncio.run(inspect_user_data(target))
