from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.auth.dependencies import get_current_user
from app.services.user_service import create_or_get_user
from app.db.mongo import users_collection, predictions_collection
from app.logger import auth_logger
from datetime import datetime
import pytz

router = APIRouter()

class LoginRequest(BaseModel):
    ref: Optional[str] = None
    fingerprint: Optional[str] = None

@router.post("/login")
async def login(payload: LoginRequest, user=Depends(get_current_user)):
    auth_logger.info(f"Processing Nexus Login for user: {user} (Ref: {payload.ref})")
    user_data, is_new = await create_or_get_user(user, referred_by=payload.ref, fingerprint=payload.fingerprint)
    auth_logger.info(f"User {user} successfully authorized and session established.")
    return {
        "user": {
            "id": user_data["_id"],
            "username": user_data["username"],
            "email": user_data["_id"],
            "referral_code": user_data.get("referral_code"),
            "score": user_data.get("score", 0),
            "is_new_user": is_new
        }
    }

@router.get("/multiplier")
async def get_multiplier(user=Depends(get_current_user)):
    """
    Nexus Reward Engine: Calculates the live multiplier based on active referrals.
    Multiplier = count of unique referrals who predicted for a match today.
    """
    user_doc = await users_collection.find_one({"_id": user})
    if not user_doc:
        return {"multiplier": 1, "referral_count": 0, "active_today": 0}

    # Find all users referred by current user
    referrals_cursor = users_collection.find({"referred_by": user})
    referrals = await referrals_cursor.to_list(length=1000)
    
    if not referrals:
        return {
            "multiplier": 1, 
            "referral_count": 0, 
            "active_today": 0,
            "referral_code": user_doc.get("referral_code")
        }

    # Get today's date in IST
    ist = pytz.timezone('Asia/Kolkata')
    today_str = datetime.now(ist).strftime("%Y-%m-%d")

    # Anti-fraud fingerprint tracking
    valid_referral_emails = []
    squad_members = []
    seen_fingerprints = {user_doc.get("device_fingerprint")} # Exclude inviter's own device
    
    for ref in referrals:
        ref_email = ref["_id"]
        ref_username = ref.get("username", ref_email.split("@")[0])
        ref_fp = ref.get("device_fingerprint")
        
        is_active = False
        is_fraud = False

        # Security Check: Skip if fingerprint matches inviter or another referral
        if ref_fp and ref_fp in seen_fingerprints:
            is_fraud = True
        
        if not is_fraud and ref_fp:
            seen_fingerprints.add(ref_fp)
        
        # Check if they predicted today
        prediction = await predictions_collection.find_one({
            "user_id": ref_email,
            "updated_at": {"$gte": datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        
        if prediction and not is_fraud:
            is_active = True
            valid_referral_emails.append(ref_email)

        squad_members.append({
            "username": ref_username.upper(),
            "active_today": is_active,
            "is_fraud": is_fraud
        })

    active_count = len(valid_referral_emails)
    multiplier = max(1, active_count)

    return {
        "multiplier": multiplier,
        "referral_count": len(referrals),
        "active_today": active_count,
        "referral_code": user_doc.get("referral_code"),
        "squad_members": squad_members
    }
