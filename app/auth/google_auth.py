from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import settings
from app.logger import auth_logger

def verify_google_token(token: str):
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        auth_logger.info(f"Verified Google token for: {idinfo.get('email')}")
        return idinfo
    except ValueError as e:
        auth_logger.warning(f"Google token verification failed: {str(e)}")
        return None
