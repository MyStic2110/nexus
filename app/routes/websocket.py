from fastapi import APIRouter, WebSocket
import json
from app.auth.google_auth import verify_google_token
from app.logger import ws_logger

router = APIRouter()

@router.websocket("/ws/{match_id}")
async def ws_endpoint(websocket: WebSocket, match_id: str):
    token = websocket.query_params.get("token")
    decoded = verify_google_token(token)
    
    if not decoded:
        ws_logger.warning(f"WebSocket connection rejected for match {match_id}: Invalid Token")
        await websocket.close()
        return

    user_email = decoded.get('email')
    await websocket.accept()
    ws_logger.info(f"WebSocket established: {user_email} connected to Nexus Match {match_id}")

    try:
        # Without Redis, we can either use Mongo Change Streams or just keep the connection alive
        # For now, we will simply wait for the client to close the connection
        while True:
            # Keep connection alive, wait for any message from client (though we don't expect any)
            await websocket.receive_text()
    except Exception as e:
        ws_logger.info(f"WebSocket session ended for {user_email}: {str(e)}")
    finally:
        ws_logger.info(f"WebSocket closed: {user_email} disconnected from match {match_id}")
