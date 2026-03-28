import json
from fastapi import APIRouter, Depends, HTTPException
from app.models.prediction import UserPrediction
from app.auth.dependencies import get_current_user
from app.db.redis import redis_client
from app.db.mongo import predictions_collection, matches_collection, users_collection
from app.logger import match_logger
from datetime import datetime, timedelta
import pytz

router = APIRouter()

@router.get("")
async def list_matches():
    match_logger.info("Fetching active matches from Nexus Arena.")
    try:
        # Sorting sequentially by specific match day & time
        cursor = matches_collection.find({}).sort([("date", 1), ("time", 1)])
        matches = await cursor.to_list(length=100)
        
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        
        for m in matches:
            m["_id"] = str(m["_id"])
            
            # Transition match dynamically based on elapsed time if current status is UPCOMING or if it should be completed
            current_status = m.get("status")
            if current_status in ["UPCOMING", "LIVE"] and m.get("date") and m.get("time"):
                try:
                    match_start_str = f"{m['date']} {m['time']}"
                    match_start_time = ist.localize(datetime.strptime(match_start_str, "%Y-%m-%d %I:%M %p"))
                    
                    if now_ist >= match_start_time + timedelta(hours=4):
                        m["status"] = "COMPLETED"
                    elif now_ist >= match_start_time:
                        m["status"] = "LIVE"
                    # If it's already explicitly LIVE (by scraper or manual), we don't force it back to UPCOMING here
                except Exception:
                    pass
                    
        match_logger.info(f"Retrieved {len(matches)} matches.")
        return matches
    except Exception as e:
        match_logger.error(f"Failed to fetch matches: {str(e)}")
        raise HTTPException(status_code=500, detail="Arena sync failed")

@router.post("/{match_id}/sessions/{session_id}/predict")
async def predict(match_id: str, session_id: int, payload: UserPrediction, user=Depends(get_current_user)):
    match_logger.info(f"User {user} submitting predictions for match: {match_id}, Session: {session_id}")
    try:
        # Governance: Check if predictions are locked (> 15.0 overs)
        match = await matches_collection.find_one({"match_id": match_id})
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # We assume match has 'innings' tracking, lock if past 15 in this session
        if match.get("innings", 1) == session_id and match.get("current_over", 0) >= 15.0:
            match_logger.warning(f"Prediction attempt by {user} REJECTED: Match {match_id} Session {session_id} is past Over 15.")
            raise HTTPException(status_code=403, detail=f"Predictions locked: Session {session_id} has passed the 15th over cutoff.")
            
        if session_id not in [1, 2]:
            raise HTTPException(status_code=400, detail="Invalid session ID. Must be 1 or 2.")

        # Persistence in Redis (Speed)
        key = f"match:{match_id}:session:{session_id}:predictions:{user}"
        await redis_client.set(key, json.dumps([p.dict() for p in payload.predictions]))
        await redis_client.sadd(f"match:{match_id}:session:{session_id}:users", user)

        # Persistence in MongoDB (Safety)
        await predictions_collection.update_one(
            {"match_id": match_id, "user_id": user},
            {"$set": {
                f"sessions.{session_id}.predictions": [p.dict() for p in payload.predictions],
                f"sessions.{session_id}.updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        match_logger.info(f"Predictions for user {user} on match {match_id} Session {session_id} successfully locked.")
        return {"status": "success", "message": f"Predictions locked for Session {session_id} in Nexus."}
    except Exception as e:
        match_logger.error(f"Prediction lock failed for user {user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Nexus prediction relay failed")

@router.get("/{match_id}/sessions/{session_id}/predict")
async def get_prediction(match_id: str, session_id: int, user=Depends(get_current_user)):
    try:
        record = await predictions_collection.find_one({"match_id": match_id, "user_id": user})
        if record and "sessions" in record and str(session_id) in record["sessions"]:
            return {"status": "success", "predictions": record["sessions"][str(session_id)]["predictions"]}
        return {"status": "not_found", "predictions": []}
    except Exception as e:
        match_logger.error(f"Failed to fetch existing prediction for user {user}: {str(e)}")
        return {"status": "error", "predictions": []}

def mask_email(email: str) -> str:
    """Masks email for privacy (e.g., mur***@****.com)."""
    try:
        user_part, domain_part = email.split("@")
        # Mask user part
        if len(user_part) <= 3:
            user_masked = f"{user_part}***"
        else:
            user_masked = f"{user_part[:3]}***"
            
        # Mask domain part (e.g., gmail.com -> ****.com)
        if "." in domain_part:
            domain_name, tld = domain_part.rsplit(".", 1)
            domain_masked = f"****.{tld}"
        else:
            domain_masked = "****"
            
        return f"{user_masked}@{domain_masked}"
    except:
        return email

@router.get("/{match_id}/sessions/{session_id}/leaderboard")
async def leaderboard(match_id: str, session_id: int):
    match_logger.info(f"Fetching Nexus Leaderboard for Match: {match_id}, Session: {session_id}")
    try:
        data = await redis_client.zrevrange(
            f"match:{match_id}:session:{session_id}:leaderboard",
            0, 50,
            withscores=True
        )
        return [{"user": mask_email(u), "score": int(s)} for u, s in data]
    except Exception as e:
        match_logger.error(f"Failed to fetch leaderboard: {str(e)}")
        return []

@router.get("/leaderboard/global")
async def global_leaderboard():
    match_logger.info("Fetching Nexus Global Standings.")
    try:
        cursor = users_collection.find({}).sort("score", -1).limit(50)
        users = await cursor.to_list(length=50)
        return [{"user": mask_email(u["_id"]), "score": u.get("score", 0)} for u in users]
    except Exception as e:
        match_logger.error(f"Failed to fetch global leaderboard: {str(e)}")
        return []

@router.get("/{match_id}/sessions/{session_id}/score-breakdown")
async def get_score_breakdown(match_id: str, session_id: int, user=Depends(get_current_user)):
    """Nexus Analytical Engine: Fetches detailed score analysis for transparency."""
    from app.db.mongo import db
    try:
        score_record = await db.session_scores.find_one({
            "match_id": match_id, 
            "session_id": session_id, 
            "user_id": user
        })
        
        if not score_record:
            return {"status": "not_calculated", "points": 0, "breakdown": []}
            
        return {
            "status": "success",
            "points": score_record.get("points", 0),
            "breakdown": score_record.get("breakdown", []),
            "updated_at": score_record.get("updated_at")
        }
    except Exception as e:
        match_logger.error(f"Breakdown analysis failed for user {user}: {str(e)}")
        return {"status": "error", "message": "Failed to retrieve analysis from Nexus"}
