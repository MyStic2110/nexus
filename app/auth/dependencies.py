from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from app.auth.google_auth import verify_google_token

security = HTTPBearer()

async def get_current_user(token=Depends(security)):
    # Demo Bypass for Nova Onboarding
    if token.credentials == "nexus_demo_token":
        print(f"[AUTH] Nova Demo Bypass active for muralicruze121@gmail.com")
        return "muralicruze121@gmail.com"
        
    decoded = verify_google_token(token.credentials)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid token")
    return decoded.get("email")
