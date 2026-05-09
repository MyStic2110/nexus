import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.getcwd())

from app.config import settings

async def list_referrals():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    
    print("\n" + "="*60)
    print(" NEXUS SQUAD - REFERRAL RELATIONSHIPS ")
    print("="*60)
    
    users_cursor = db.users.find({}, {"_id": 1, "username": 1, "referred_by": 1, "referral_code": 1})
    users = await users_cursor.to_list(length=1000)
    
    if not users:
        print("No users found in database.")
        return

    # Map for easy lookup
    user_map = {u["_id"]: u.get("username", "Unknown") for u in users}
    
    found_referrals = False
    for user in users:
        inviter_email = user.get("referred_by")
        if inviter_email:
            found_referrals = True
            inviter_name = user_map.get(inviter_email, inviter_email)
            print(f" 👤 {user.get('username', user['_id']).ljust(15)} | Invited By: {inviter_name}")
    
    if not found_referrals:
        print(" No referral links established yet.")
    
    print("="*60 + "\n")
    client.close()

if __name__ == "__main__":
    asyncio.run(list_referrals())
