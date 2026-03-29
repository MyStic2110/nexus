import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def drop():
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    await client.drop_database("ipl_nexus")
    print("ipl_nexus database deleted successfully.")
    client.close()

if __name__ == "__main__":
    asyncio.run(drop())
