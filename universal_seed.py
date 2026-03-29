import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def seed_all():
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    
    # 1. Source database
    db_source = client["ipl_game"]
    matches = await db_source.matches.find({}).to_list(1000)
    
    if not matches:
        print("Source ipl_game.matches is empty. Re-importing from PDF...")
        # (This should not happen now since I just seeded it)
    
    # 2. Sync to ipl_game
    db_target = client["ipl_game"]
    await db_target.matches.delete_many({})
    if matches:
        await db_target.matches.insert_many(matches)
        print(f"Synced {len(matches)} matches to ipl_game.matches")
    
    # 3. Double check local ipl_game again
    count = await db_source.matches.count_documents({})
    print(f"Original ipl_game.matches count: {count}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_all())
