from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from app.auth.google_auth import verify_google_token

security = HTTPBearer()

async def get_current_user(token=Depends(security)):
    decoded = verify_google_token(token.credentials)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid token")
    return decoded.get("email")
