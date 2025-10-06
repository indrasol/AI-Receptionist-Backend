from typing import Optional
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from app.config.settings import REDIS_URL

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scrape Progress"])

@router.get("/")
async def progress_root():
    """Test endpoint for progress router"""
    return {"message": "Progress router is working"}

@router.websocket("/scrape/{task_id}")
async def scrape_progress_ws(websocket: WebSocket, task_id: str):
    # Check origin for CORS
    origin = websocket.headers.get("origin")
    allowed_origins = [
        "http://localhost:8080",
        "http://localhost:8081", 
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://myaireceptionist.indrasol.com"
    ]
    
    if origin not in allowed_origins and origin is not None:
        logger.warning(f"WebSocket connection rejected from origin: {origin}")
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    logger.info(f"WebSocket connected for task {task_id} from origin: {origin}")
    
    try:
        r = aioredis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        channel = f"scrape:{task_id}"
        await pubsub.subscribe(channel)
        
        # First send cached log list
        past_logs = await r.lrange(f"{channel}:log", 0, -1)
        logger.info(f"Sending {len(past_logs)} cached logs for task {task_id}")
        
        for log_line in past_logs:
            await websocket.send_text(log_line.decode())
            
        # Stream live messages
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"].decode())
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except:
            pass
