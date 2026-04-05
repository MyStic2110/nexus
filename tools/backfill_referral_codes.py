import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import secrets
import string

# Add project root to path
sys.path.append(os.getcwd())

from app.config import settings

def generate_referral_code(length=8):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

async def backfill_referral_codes():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    
    print("\033[94m[Nexus] Scanning for legacy users missing referral codes...\033[0m")
    
    # Find users missing referral_code or where referral_code is None
    cursor = db.users.find({"$or": [{"referral_code": {"$exists": False}}, {"referral_code": None}]})
    users = await cursor.to_list(length=1000)
    
    if not users:
        print("\033[92m[Nexus] No legacy users found. Database is synchronized.\033[0m")
        return

    print(f"\033[94m[Nexus] Found {len(users)} users. Backfilling...\033[0m")
    
    for user in users:
        new_code = generate_referral_code()
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"referral_code": new_code}}
        )
        print(f" -> Backfilled {user['_id']} with code: {new_code}")

    print("\033[92m[Nexus] Backfill complete. All users now have unique Nexus identities.\033[0m")
    client.close()

if __name__ == "__main__":
    asyncio.run(backfill_referral_codes())
