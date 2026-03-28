import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.ipl_game

async def run():
    match = await db.matches.find_one({"match_id": "ipl_2026_01"})
    print("Match current over:", match.get('current_over'))
    s1 = await db.live_match_overs.count_documents({'match_id': 'ipl_2026_01', 'session_id': 1})
    s2 = await db.live_match_overs.count_documents({'match_id': 'ipl_2026_01', 'session_id': 2})
    print('S1 count:', s1)
    print('S2 count:', s2)
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
