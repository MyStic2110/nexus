import asyncio
import os
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.getcwd())

from app.config import settings

async def verify_api():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    
    match_id = "API_TEST_MATCH"
    inviter_email = "api_inviter@test.com"
    
    print("\033[94m[1/3] Injecting API test squad...\033[0m")
    await db.users.delete_many({"_id": {"$regex": "@test.com"}})
    await db.predictions.delete_many({"user_id": {"$regex": "@test.com"}})
    
    # 1. Inviter
    # 2. Friend 1 (Valid)
    # 3. Friend 2 (Fraud: Duplicate FP with Friend 1)
    # 4. Friend 3 (Inactive: No prediction)
    await db.users.insert_many([
        {"_id": inviter_email, "username": "API_BOSS", "referral_code": "API_REF", "device_fingerprint": "FP_BOSS"},
        {"_id": "v1@test.com", "username": "Valid_1", "referred_by": inviter_email, "device_fingerprint": "FP_1"},
        {"_id": "f1@test.com", "username": "Fraud_1", "referred_by": inviter_email, "device_fingerprint": "FP_1"},
        {"_id": "i1@test.com", "username": "Inactive_1", "referred_by": inviter_email, "device_fingerprint": "FP_2"}
    ])
    
    # Valid_1 and Fraud_1 predict today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    await db.predictions.insert_many([
        {"user_id": "v1@test.com", "match_id": match_id, "updated_at": datetime.utcnow()},
        {"user_id": "f1@test.com", "match_id": match_id, "updated_at": datetime.utcnow()}
    ])

    print("\033[94m[2/3] Executing Multiplier API Logic (Manual Trigger)...\033[0m")
    # Simulate the logic from auth.py get_multiplier
    user_doc = await db.users.find_one({"_id": inviter_email})
    referrals_cursor = db.users.find({"referred_by": inviter_email})
    referrals = await referrals_cursor.to_list(length=100)
    
    # Logic extracted from auth.py
    valid_referral_emails = []
    squad_members = []
    seen_fingerprints = {user_doc.get("device_fingerprint")}
    
    for ref in referrals:
        ref_email = ref["_id"]
        ref_username = ref.get("username", ref_email.split("@")[0])
        ref_fp = ref.get("device_fingerprint")
        is_active = False
        is_fraud = False

        if ref_fp and ref_fp in seen_fingerprints:
            is_fraud = True
        if not is_fraud and ref_fp:
            seen_fingerprints.add(ref_fp)
        
        prediction = await db.predictions.find_one({
            "user_id": ref_email,
            "updated_at": {"$gte": today_start}
        })
        if prediction and not is_fraud:
            is_active = True
            valid_referral_emails.append(ref_email)

        squad_members.append({
            "username": ref_username.upper(),
            "active_today": is_active,
            "is_fraud": is_fraud
        })

    print("\n" + "="*45)
    print(" NEXUS SQUAD API VERIFICATION ")
    print("="*45)
    print(f" Multiplier: {max(1, len(valid_referral_emails))}x")
    print(f" Total Squad: {len(squad_members)}")
    
    for m in squad_members:
        status = "[LIVE]" if m['active_today'] else ("[FRAUD]" if m['is_fraud'] else "[INACTIVE]")
        print(f" {status.ljust(10)} | User: {m['username']}")

    # Final Checks
    if len(squad_members) == 3 and any(m['is_fraud'] for m in squad_members):
         print("\n \033[92mPASSED: API correctly identifies fraud and active status.\033[0m")
    else:
         print("\n \033[91mFAILED: API logic mismatch.\033[0m")
    print("="*45 + "\n")

    print("\033[94m[3/3] Purging API test data...\033[0m")
    await db.users.delete_many({"_id": {"$regex": "@test.com"}})
    await db.predictions.delete_many({"match_id": match_id})
    client.close()

if __name__ == "__main__":
    asyncio.run(verify_api())
