from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import settings
from app.logger import auth_logger

def verify_google_token(token: str):
    try:
        # id_token.verify_oauth2_token verifies the JWT's signature and expiration
        # Added clock_skew_in_seconds=10 to prevent "Token used too early" if system clock is 1s off
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        auth_logger.info(f"Verified Google token for: {idinfo.get('email')}")
        return idinfo
    except ValueError as e:
        auth_logger.warning(f"Google token verification failed: {str(e)}")
        return None
