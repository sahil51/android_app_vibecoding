from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from signaling import manager
from schemas import SignalingMessage, RegistrationMessage
import logging
import shutil
import os
import uuid

app = FastAPI(title="E2EE Signaling Server")

# Create uploads directory if not exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files to serve uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

@app.get("/")
async def health():
    return {"status": "healthy", "version": "0.1.0"}

@app.get("/users/{user_id}/key")
async def get_user_key(user_id: str):
    key = manager.get_public_key(user_id)
    if not key:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "public_identity_key": key}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_ext = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return full URL for the uploaded file
        # In a real app, you'd get the base URL from config
        return {"url": f"http://127.0.0.1:8000/uploads/{file_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.websocket("/ws/{user_id}")
async def signaling_websocket(websocket: WebSocket, user_id: str):
    logging.info(f"Incoming WebSocket connection attempt for: {user_id}")
    try:
        public_key = websocket.query_params.get("pub_key")
        if not public_key:
            logging.warning(f"Connection rejected: Move pub_key missing for {user_id}")
            await websocket.close(code=1008)
            return

        logging.info(f"Connecting user {user_id} with key {public_key[:10]}...")
        await manager.connect(user_id, websocket, public_key)
        
        while True:
            data = await websocket.receive_json()
            logging.info(f"Received msg from {user_id}: {data.get('type')}")
            try:
                msg = SignalingMessage(**data)
                # Route the message
                await manager.send_message(msg.dict(by_alias=True), msg.to_user)
            except Exception as e:
                logging.error(f"Error processing message from {user_id}: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logging.error(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)
