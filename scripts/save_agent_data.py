import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def save_data():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    matches_collection = db["matches"]
    
    # We query flexibly since the PDF import might show SRH vs RCBW or RCB vs SRH
    cursor = matches_collection.find({"$or": [{"team1": "RCB", "team2": "SRH"}, {"team1": "SRH", "team2": "RCB"}]})
    match = await cursor.to_list(1)
    
    if match:
        target_id = match[0]["_id"]
        match_id = match[0]["match_id"]
        
        agent_data = {
            "balls": ["0", "1", "0", "6", "0", "0"],
            "total_runs": 7
        }
        
        await matches_collection.update_one(
            {"_id": target_id},
            {"$set": {"over_1_agent_data": agent_data}}
        )
        print(f"NEXUS DB: Agent data successfully injected into Match ID: {match_id}")
    else:
        print("NEXUS DB: Could not locate SRH vs RCB to inject agent data.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(save_data())
