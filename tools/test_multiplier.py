import asyncio
import os
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.getcwd())

from app.config import settings
from scripts.calculate_points import run_for_match

async def run_test():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    
    match_id = "MOCK_MATCH_2026"
    inviter_email = "inviter@test.com"
    
    print("\033[94m[1/4] Cleaning existing test data...\033[0m")
    await db.users.delete_many({"_id": {"$regex": "@test.com"}})
    await db.matches.delete_many({"match_id": match_id})
    await db.predictions.delete_many({"match_id": match_id})
    await db.session_scores.delete_many({"match_id": match_id})
    await db.live_match_overs.delete_many({"match_id": match_id})

    print("\033[94m[2/4] Injecting mock users and match metadata...\033[0m")
    # Inviter & Referrals
    await db.users.insert_many([
        {"_id": inviter_email, "username": "Inviter", "referral_code": "TEST_INVITE", "device_fingerprint": "DEV_INVITER", "score": 0},
        {"_id": "friend_1@test.com", "username": "Friend_1", "referred_by": inviter_email, "device_fingerprint": "DEV_FRIEND_1", "score": 0},
        {"_id": "friend_2@test.com", "username": "Friend_2", "referred_by": inviter_email, "device_fingerprint": "DEV_FRIEND_2", "score": 0},
        {"_id": "fraud_copy@test.com", "username": "Fraud_Copy", "referred_by": inviter_email, "device_fingerprint": "DEV_FRIEND_2", "score": 0}, # Duplicate FP
        {"_id": "inactive@test.com", "username": "Inactive", "referred_by": inviter_email, "device_fingerprint": "DEV_INACTIVE", "score": 0}
    ])
    
    # Mock Match: COMPLETED to trigger scoring
    await db.matches.insert_one({
        "match_id": match_id,
        "team1": "WARRIORS", "team2": "TITANS",
        "date": "2026-04-05", "status": "COMPLETED",
        "innings": 1
    })
    
    # Actual Ball Results for Overs 19 & 20
    # Pattern: [4, 0, W, 1, 6, 1] [0, W, 4, 2, 6, 0]
    results = ["4", "0", "W", "1", "6", "1", "0", "W", "4", "2", "6", "0"]
    await db.live_match_overs.insert_one({"match_id": match_id, "session_id": 1, "over": 19, "balls": results[0:6]})
    await db.live_match_overs.insert_one({"match_id": match_id, "session_id": 1, "over": 20, "balls": results[6:12]})

    print("\033[94m[3/4] Injecting predictions for inviter and active friends...\033[0m")
    # Predictions: Every user predicts "4" for all 12 balls.
    # Correct balls: Ball 1 and Ball 9.
    # Base Points: 10 + 10 = 20.
    test_emails = [inviter_email, "friend_1@test.com", "friend_2@test.com", "fraud_copy@test.com"]
    for email in test_emails:
        await db.predictions.insert_one({
            "match_id": match_id,
            "user_id": email,
            "sessions": {
                "1": {
                    "predictions": [{"ball": i+1, "runs": "4"} for i in range(12)],
                    "updated_at": datetime.utcnow()
                }
            }
        })

    print("\033[94m[4/4] Executing Nexus Scoring Engine...\033[0m")
    from scripts.calculate_points import run_for_match # Import here to ensure sys.path is set
    await run_for_match(db, match_id, 1)

    # Validate Results
    score_doc = await db.session_scores.find_one({"match_id": match_id, "user_id": inviter_email})
    
    print("\n" + "="*40)
    print(" NEXUS REWARD MULTIPLIER TEST RESULTS ")
    print("="*40)
    if score_doc:
        m = score_doc.get("multiplier", 1)
        base = score_doc.get("base_points", 0)
        final = score_doc.get("points", 0)
        
        print(f" User: {inviter_email}")
        print(f" Base Points: {base} (Expected: 20)")
        print(f" Multiplier:  {m}x (Expected: 2x)")
        print(f" Total Points: {final} (Expected: 40)")
        
        if m == 2 and final == 40:
            print("\n \033[92mTEST PASSED: Multiple unique referrals detected & anti-fraud fingerprint blocking successful.\033[0m")
        else:
            print("\n \033[91mTEST FAILED: Logic mismatch.\033[0m")
    else:
        print("\033[91mERROR: No score record generated.\033[0m")
    print("="*40 + "\n")

    print("\033[94m[CLEANUP] Purging all test data...\033[0m")
    await db.users.delete_many({"_id": {"$regex": "@test.com"}})
    await db.matches.delete_many({"match_id": match_id})
    await db.predictions.delete_many({"match_id": match_id})
    await db.session_scores.delete_many({"match_id": match_id})
    await db.live_match_overs.delete_many({"match_id": match_id})
    print("\033[92mCleaned successfully.\033[0m")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run_test())
