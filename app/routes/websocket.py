from fastapi import APIRouter, WebSocket
import json
from app.auth.google_auth import verify_google_token
from app.db.redis import redis_client
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

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"match:{match_id}:channel")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                ws_logger.info(f"Relaying live update to {user_email} for match {match_id}")
                await websocket.send_text(message["data"])
    except Exception as e:
        ws_logger.error(f"WebSocket stream interrupted for {user_email}: {str(e)}")
    finally:
        await pubsub.unsubscribe()
        ws_logger.info(f"WebSocket closed: {user_email} disconnected from match {match_id}")
