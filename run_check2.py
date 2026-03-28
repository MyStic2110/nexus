import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.ipl_game

async def run():
    cursor = db.matches.find({"$or": [{"team1": "RCB", "team2": "SRH"}, {"team1": "SRH", "team2": "RCB"}]})
    matches = await cursor.to_list(10)
    for m in matches:
        print(m.get("match_id"), m.get("date"))
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
