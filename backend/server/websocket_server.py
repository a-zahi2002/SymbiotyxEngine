"""
websocket_server.py
-------------------
FastAPI WebSocket server for SymbiotixEngine.

Sends real-time gesture commands to Unity (AetherUI) over WebSocket.
Runs on localhost:8000 with a /ws endpoint that any number of Unity
clients can connect to simultaneously.

Usage:
    # From the project root (SymbiotixEngine/):
    python -m backend.server.websocket_server

    # Or directly:
    python backend/server/websocket_server.py

Dependencies:
    pip install fastapi uvicorn

Compatible with Python 3.10+
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.capture.sequence_buffer import SequenceBuffer

# ─────────────────────────────────────────────────────────────
#  Connection Manager
#  Tracks all active Unity WebSocket clients and provides
#  broadcast / unicast helpers.
# ─────────────────────────────────────────────────────────────

class ConnectionManager:
    """
    Manages a set of active WebSocket connections.

    Methods:
        connect    – Register a new client.
        disconnect – Remove a disconnected client.
        send_to    – Send a message to a specific client.
        broadcast  – Send a message to ALL connected clients.
    """

    def __init__(self) -> None:
        # Using a list to preserve insertion order; a set would also work.
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept the WebSocket handshake and register the client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        client = websocket.client
        print(f"[WS] Client connected: {client.host}:{client.port}  "
              f"(total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client after disconnect."""
        self.active_connections.remove(websocket)
        client = websocket.client
        print(f"[WS] Client disconnected: {client.host}:{client.port}  "
              f"(total: {len(self.active_connections)})")

    async def send_to(self, websocket: WebSocket, data: dict) -> None:
        """Send a JSON message to a single client."""
        await websocket.send_json(data)

    async def broadcast(self, data: dict) -> None:
        """
        Send a JSON message to every connected client.
        Silently removes clients that error during send.
        """
        stale: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                stale.append(connection)
        # Clean up any broken connections
        for ws in stale:
            self.active_connections.remove(ws)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Global manager instance
manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────
#  Real Inference Model Integration
# ─────────────────────────────────────────────────────────────

# Change this to False if you don't have a webcam or want to disable real inference
ENABLE_INFERENCE_LOOP: bool = True

async def send_gesture_command(command: str, intensity: float) -> None:
    """Broadcasts a recognized gesture and its computed intensity to Unity."""
    payload = {
        "command": command,
        "intensity": round(intensity, 4)
    }
    await manager.broadcast(payload)
    print(f"[INFERENCE] Broadcast → {json.dumps(payload)} ({manager.client_count} clients)")

async def inference_worker():
    """Blocking worker that runs MediaPipe and model inference, yielding gestures."""
    import cv2
    import numpy as np
    import mediapipe as mp
    import torch
    from backend.capture.webcam_capture import initialize_camera, initialize_hands, process_frame, extract_landmarks
    from backend.models.train_gesture_model import process_sequence
    from backend.models.gesture_classifier import load_model

    print("[INFERENCE] Loading Gesture Model...")
    try:
        model, class_map = load_model()
        model.eval()
    except Exception as e:
        print(f"[WARN] Failed to load model: {e}. Falling back to default test mode.")
        model = None

    try:
        cap = initialize_camera()
        hands, _, _ = initialize_hands()
    except Exception as e:
        print(f"[ERROR] Could not initialize camera/hands for inference: {e}")
        return

    buffer = SequenceBuffer()
    idle_frames = 0
    max_idle_frames = 15  # End gesture sequence after 15 empty frames

    while True:
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue
            
        frame = cv2.flip(frame, 1)
        results = process_frame(frame, hands)
        hand_data_list = extract_landmarks(results)
        
        if len(hand_data_list) > 0:
            # We add frame record
            frame_record = {
                "timestamp": round(time.time(), 4),
                "hand": hand_data_list[0]["hand"],
                "landmarks": hand_data_list[0]["landmarks"]
            }
            buffer.add_frame(frame_record)
            idle_frames = 0
        else:
            idle_frames += 1

        # Check for gesture completion
        if idle_frames > max_idle_frames and len(buffer) > 10:
            # Process gesture sequence and run model
            seq_data = buffer.get_sequence()
            
            # Simple Intensity calculation: Total movement of wrist across sequence
            try:
                start_lms = seq_data[0]["landmarks"]
                end_lms = seq_data[-1]["landmarks"]
                if len(start_lms) > 0 and len(end_lms) > 0:
                    dx = end_lms[0]["x"] - start_lms[0]["x"]
                    dy = end_lms[0]["y"] - start_lms[0]["y"]
                    intensity = (dx**2 + dy**2)**0.5 * 10.0  # arbitrary scaling
                else:
                    intensity = 1.0
            except:
                intensity = 1.0
                
            intensity = max(0.5, min(intensity, 3.0)) # clamp between 0.5 and 3.0

            identified_gesture = "zoom_in"
            
            if model is not None:
                try:
                    features = process_sequence(seq_data)
                    input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                    with torch.no_grad():
                        preds = model(input_tensor)
                        pred_class = torch.argmax(preds, dim=1).item()
                        identified_gesture = class_map.get(pred_class, "unknown")
                except Exception as e:
                    print(f"[ERROR] Model inference failed: {e}")

            buffer.clear()
            
            if identified_gesture != "unknown":
                await send_gesture_command(identified_gesture, intensity)

        elif idle_frames > max_idle_frames:
            buffer.clear()
            
        await asyncio.sleep(0.01)

async def real_inference_loop() -> None:
    # Run the blocking camera loop in a threaded executor to not block asyncio Loop
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: asyncio.run(inference_worker()))

# ─────────────────────────────────────────────────────────────
#  FastAPI Application
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown lifecycle.
    Starts the optional test command loop when the server boots.
    """
    task = None
    if ENABLE_INFERENCE_LOOP:
        task = asyncio.create_task(inference_worker())
    print("=" * 50)
    print("  SymbiotixEngine WebSocket Server")
    print("  Listening on  ws://localhost:8000/ws")
    print("=" * 50)
    yield
    # Shutdown: cancel the background task if running
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    print("[WS] Server shutting down.")


app = FastAPI(
    title="SymbiotixEngine WebSocket Server",
    version="0.1.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────
#  WebSocket Endpoint  —  /ws
#  Unity's CommandReceiver connects here.
# ─────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for Unity clients.

    • Accepts the connection and registers it with the manager.
    • Listens for any incoming messages from Unity (currently
      logged but not processed — extend as needed).
    • Cleans up on disconnect.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by listening for messages.
            # Unity doesn't send anything by default, but this allows
            # future bi-directional communication (e.g., Unity sending
            # confirmation or requesting specific data).
            data = await websocket.receive_text()
            print(f"[WS] Received from Unity: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────
#  REST Endpoints  —  for pushing commands from other systems
# ─────────────────────────────────────────────────────────────

@app.post("/send_command")
async def send_command(command: str = "zoom_in", intensity: float = 1.5):
    """
    HTTP POST endpoint to broadcast a gesture command to all
    connected Unity clients.

    This allows any part of the backend (gesture pipeline, CLI
    tools, tests) to push a command without needing its own
    WebSocket connection.

    Query params:
        command   (str):   The gesture command name.
        intensity (float): The intensity value (0.0+).

    Example:
        curl -X POST "http://localhost:8000/send_command?command=zoom_in&intensity=2.0"
    """
    payload = {
        "command": command,
        "intensity": round(intensity, 4)
    }
    await manager.broadcast(payload)
    return JSONResponse(content={
        "status": "sent",
        "clients": manager.client_count,
        "payload": payload
    })


@app.get("/status")
async def server_status():
    """
    Quick health-check endpoint.

    Returns the number of connected clients and server uptime info.
    """
    return {
        "status": "running",
        "connected_clients": manager.client_count,
        "inference_loop_enabled": ENABLE_INFERENCE_LOOP,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }


# ─────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("\n[INFO] Starting SymbiotixEngine WebSocket Server...")
    print("[INFO] Unity CommandReceiver should connect to ws://localhost:8000/ws\n")

    uvicorn.run(
        "backend.server.websocket_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,        # Set True during development for hot-reload
        log_level="info",
    )
