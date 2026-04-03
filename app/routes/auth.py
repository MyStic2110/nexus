from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.services.user_service import create_or_get_user
from app.logger import auth_logger

router = APIRouter()

@router.post("/login")
async def login(user=Depends(get_current_user)):
    auth_logger.info(f"Processing Nexus Login for user: {user}")
    user_data, is_new = await create_or_get_user(user)
    auth_logger.info(f"User {user} successfully authorized and session established.")
    return {
        "user": {
            "id": user_data["_id"],
            "username": user_data["username"],
            "email": user_data["_id"],
            "score": user_data.get("score", 0),
            "is_new_user": is_new
        }
    }
