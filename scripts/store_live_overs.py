import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def create_new_collection_and_store():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game
    match_data_collection = db["live_match_overs"]
    
    # We locate the match ID first to be absolutely sure
    cursor = db.matches.find({"$or": [{"team1": "RCB", "team2": "SRH"}, {"team1": "SRH", "team2": "RCB"}]})
    match_record = await cursor.to_list(1)
    
    if match_record:
        match_id = match_record[0]["match_id"]
        
        agent_data = {
            "match_id": match_id,
            "over": 1,
            "balls": ["0", "1", "0", "6", "0", "0"],
            "total_runs": 7
        }
        
        # Insert into the new collection
        await match_data_collection.update_one(
            {"match_id": match_id, "over": 1},
            {"$set": agent_data},
            upsert=True
        )
        print(f"NEXUS DB: Payload officially stored inside NEW collection 'live_match_overs' for Match ID: {match_id}")
    else:
        print("NEXUS DB: Could not locate SRH vs RCB to inject agent data.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(create_new_collection_and_store())
