import secrets
import string
from datetime import datetime
from app.db.mongo import users_collection
from app.logger import auth_logger

def generate_referral_code(length=8):
    """Generates a unique high-entropy referral token for Nexus identification."""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

async def create_or_get_user(email: str, referred_by: str = None, fingerprint: str = None):
    auth_logger.info(f"Database sync check for user: {email}")
    user = await users_collection.find_one({"_id": email})
    is_new = False
    
    if not user:
        auth_logger.warning(f"User {email} not found in database. Initializing new Nexus profile...")
        username = email.split("@")[0]
        
        # Security: Validate referral code if provided
        inviter_email = None
        if referred_by:
            inviter = await users_collection.find_one({"referral_code": referred_by.upper()})
            if inviter:
                inviter_email = inviter["_id"]
                auth_logger.info(f"Referral match found: {email} invited by {inviter_email}")
            else:
                auth_logger.warning(f"Invalid referral code '{referred_by}' provided for {email}")

        user = {
            "_id": email,
            "username": username,
            "referral_code": generate_referral_code(),
            "referred_by": inviter_email,
            "device_fingerprint": fingerprint,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
            "score": 0
        }
        await users_collection.insert_one(user)
        auth_logger.info(f"New profile successfully committed: {username} (Code: {user['referral_code']})")
        is_new = True
    else:
        auth_logger.info(f"Existing profile found for {email}. Updating metadata.")
        update_data = {"last_login": datetime.utcnow()}
        
        # Backfill: Generate referral code for legacy users if they don't have one
        if not user.get("referral_code"):
            new_code = generate_referral_code()
            update_data["referral_code"] = new_code
            user["referral_code"] = new_code
            auth_logger.info(f"Backfilled missing referral code for {email}: {new_code}")

        if fingerprint:
            update_data["device_fingerprint"] = fingerprint
        
        await users_collection.update_one(
            {"_id": email},
            {"$set": update_data}
        )
        
    return user, is_new
