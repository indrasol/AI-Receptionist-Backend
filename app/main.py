from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from twilio.twiml.voice_response import VoiceResponse, Start
import vosk
import time
import logging
from app.config import settings
from app.api.v1.router import api_router

# Import voice transcription service
from app.services.voice_transcription import voice_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI Receptionist API with FastAPI and Supabase",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    debug=settings.debug,
    redirect_slashes=False
)

# Allow frontend origins
origins = [
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8080",
    "http://localhost:3000",  # React default port
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:5173",
    "https://myaireceptionist.indrasol.com"
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
# Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.backend_cors_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly for production
)


# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     """Add process time header to responses"""
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(process_time)
#     return response


# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     """Log all requests"""
#     logger.info(f"{request.method} {request.url}")
#     response = await call_next(request)
#     logger.info(f"{request.method} {request.url} - {response.status_code}")
#     return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Receptionist API",
        "version": "1.0.0",
        "docs": f"{settings.api_v1_str}/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)

# Voice transcription endpoints
@app.post('/call')
async def call(request: Request):
    """Accept a phone call."""
    print("\n\n\n call received")
    response = VoiceResponse()
    start = Start()
    start.stream(url=f'wss://{request.base_url.hostname}/stream')
    response.append(start)
    response.say('Please leave a message')
    response.pause(length=60)
    
    # Get form data properly
    form_data = await request.form()
    print(f'Incoming call from {form_data.get("From", "Unknown")}')
    
    return Response(content=str(response), media_type="text/xml")

@app.websocket('/stream')
async def stream(websocket: WebSocket):
    """Receive and transcribe audio stream."""
    await websocket.accept()
    print("\n\n\n WebSocket connection established")
    
    # Import necessary modules
    import json
    import base64
    import audioop
    from app.services.voice_transcription import model, CL, BS
    
    rec = vosk.KaldiRecognizer(model, 16000)
    last_partial = ""
    
    try:
        while True:
            message = await websocket.receive_text()
            packet = json.loads(message)
            
            if packet['event'] == 'start':
                print('Streaming is starting')
            elif packet['event'] == 'stop':
                print('\nStreaming has stopped')
            elif packet['event'] == 'media':
                audio = base64.b64decode(packet['media']['payload'])
                audio = audioop.ulaw2lin(audio, 2)
                audio = audioop.ratecv(audio, 2, 1, 8000, 16000, None)[0]
                
                if rec.AcceptWaveform(audio):
                    r = json.loads(rec.Result())
                    if r['text'].strip():  # Only print if there's actual text
                        print(f"\n✅ Final: {r['text']}")
                else:
                    r = json.loads(rec.PartialResult())
                    partial_text = r['partial'].strip()
                    if partial_text and partial_text != last_partial:  # Only print if text changed
                        print(f"\r🔄 Partial: {partial_text}", end='', flush=True)
                        last_partial = partial_text
                    
    except WebSocketDisconnect:
        print("\nWebSocket disconnected")


# Configure Twilio when module is imported
try:
    import os
    from pyngrok import ngrok, conf
    from app.services.voice_transcription import twilio_client

    if twilio_client:
        try:
            print("\n\n\nConfiguring Twilio")
            # Configure ngrok to use system-installed binary
            ngrok_config = conf.PyngrokConfig(
                ngrok_path='/opt/homebrew/bin/ngrok'
            )
            public_url = ngrok.connect(settings.port, bind_tls=True, pyngrok_config=ngrok_config).public_url
            number = twilio_client.incoming_phone_numbers.list()[0]
            number.update(voice_url=public_url + '/call')
            print(f'Waiting for calls on {number.phone_number}')
        except Exception as e:
            print("\n\n\nConfiguring Twilio failed")
            print(f"Warning: Could not configure Twilio: {e}")
            print("Server will continue without Twilio configuration")
    else:
        print("\n\n\nTwilio not configured")
        print("Warning: Twilio not configured - voice calls won't work")
except Exception as e:
    print(f"\n\n\nError configuring Twilio: {e}")
    print("Server will continue without Twilio configuration")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 
