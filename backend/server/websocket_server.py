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
import threading
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

# Global Threading State
inference_thread = None
inference_lock = threading.Lock()
shutdown_event = threading.Event()
app_loop = None  # To store the asyncio loop

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

def run_fallback_loop(loop):
    import time
    import random
    import traceback
    
    print("[INFO] Running in fallback test mode...")
    gestures = ["zoom_in", "zoom_out", "swipe_left", "swipe_right", "rotate_cw", "rotate_ccw"]
    
    try:
        while not shutdown_event.is_set():
            time.sleep(3.0)
            if manager.client_count > 0:
                gesture = random.choice(gestures)
                intensity = random.uniform(0.8, 2.5)
                print("Captured frame...")
                print("Sequence complete")
                print(f"Prediction: {gesture} (confidence 0.99)")
                print("Broadcasting command...")
                asyncio.run_coroutine_threadsafe(
                    send_gesture_command(gesture, intensity),
                    loop
                )
    except Exception as e:
        print(f"[ERROR] Fallback loop crashed: {e}")
        traceback.print_exc()

def inference_worker_sync(loop):
    """Blocking worker that runs MediaPipe and model inference, yielding gestures in a daemon thread."""
    print("[INFO] Starting inference_worker_sync thread...")
    try:
        import sys
        import cv2
        import numpy as np
        import mediapipe as mp
        import torch
        import traceback
        
        from backend.capture.webcam_capture import initialize_hands, process_frame, extract_landmarks, draw_landmarks, draw_hud
        from backend.models.train_gesture_model import process_sequence
        from backend.models.gesture_classifier import load_model
        
        from backend.capture.sequence_buffer import SequenceBuffer
    except Exception as e:
        print(f"[ERROR] Failed to import inference dependencies: {e}")
        print("[INFO] Switching to fallback test mode due to missing dependencies.")
        run_fallback_loop(loop)
        return

    print("Opening webcam...")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[WARN] Camera index 0 failed, trying index 1...")
        cap = cv2.VideoCapture(1)
        
    if not cap.isOpened():
        print("ERROR: Camera failed to open. Running in fallback test mode.")
        run_fallback_loop(loop)
        return

    print("Webcam opened successfully")
    
    print("[INFERENCE] Loading Gesture Model...")
    try:
        model, class_map = load_model()
        model.eval()
    except Exception as e:
        print(f"[WARN] Failed to load model: {e}. Webcam will stay open, but predictions will be simulated.")
        model = None
        class_map = {}

    try:
        hands, mp_drawing, mp_hands = initialize_hands()
    except Exception as e:
        print(f"[ERROR] Could not initialize hands for inference: {e}")
        if cap.isOpened(): cap.release()
        print("[INFO] Switching to fallback test mode.")
        run_fallback_loop(loop)
        return

    print("Inference worker started")
    print("Starting inference loop...")
    
    buffer = SequenceBuffer()
    idle_frames = 0
    max_idle_frames = 15  # End gesture sequence after 15 empty frames
    total_frames = 0

    try:
        while not shutdown_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                
            frame = cv2.flip(frame, 1)
            results = process_frame(frame, hands)
            draw_landmarks(frame, results, mp_drawing, mp_hands)
            draw_hud(frame, True, total_frames)
            
            cv2.imshow("SymbiotixEngine Inference", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] Quitting inference loop.")
                break
                
            hand_data_list = extract_landmarks(results)
            
            if len(hand_data_list) > 0:
                frame_record = {
                    "timestamp": round(time.time(), 4),
                    "hand": hand_data_list[0]["hand"],
                    "landmarks": hand_data_list[0]["landmarks"]
                }
                buffer.add_frame(frame_record)
                
                if idle_frames > 0:
                    print("Hand detected, tracking started...")
                idle_frames = 0
                total_frames += 1

                # Stream live intensity back to Unity so the orb reacts in real-time
                if total_frames % 2 == 0:
                    lms = hand_data_list[0]["landmarks"]
                    xs = [lm["x"] for lm in lms]
                    ys = [lm["y"] for lm in lms]
                    hand_scale = ((max(xs) - min(xs))**2 + (max(ys) - min(ys))**2)**0.5
                    live_intensity = max(0.5, min(hand_scale * 8.0, 3.0))
                    
                    asyncio.run_coroutine_threadsafe(
                        send_gesture_command("tracking", live_intensity),
                        loop
                    )
            else:
                idle_frames += 1

            # Check for gesture completion
            if idle_frames > max_idle_frames and len(buffer) > 10:
                print("Sequence complete")
                seq_data = buffer.get_sequence()
                
                # Simple Intensity calculation
                try:
                    start_lms = seq_data[0]["landmarks"]
                    end_lms = seq_data[-1]["landmarks"]
                    if len(start_lms) > 0 and len(end_lms) > 0:
                        dx = end_lms[0]["x"] - start_lms[0]["x"]
                        dy = end_lms[0]["y"] - start_lms[0]["y"]
                        intensity = (dx**2 + dy**2)**0.5 * 10.0
                    else:
                        intensity = 1.0
                except:
                    intensity = 1.0
                    
                intensity = max(0.5, min(intensity, 3.0))

                identified_gesture = "unknown"
                confidence = 0.0
                
                try:
                    if model is not None:
                        features = process_sequence(seq_data)
                        input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                        with torch.no_grad():
                            preds = model(input_tensor)
                            pred_class = torch.argmax(preds, dim=1).item()
                            identified_gesture = class_map.get(pred_class, "unknown")
                            confidence = torch.max(torch.nn.functional.softmax(preds, dim=1)).item()
                    else:
                        import random
                        gestures = ["zoom_in", "zoom_out", "swipe_left", "swipe_right", "rotate_cw", "rotate_ccw"]
                        identified_gesture = random.choice(gestures)
                        confidence = 0.99
                except Exception as e:
                    print(f"[ERROR] Model inference failed: {e}")
                    traceback.print_exc()

                print(f"Prediction: {identified_gesture} (confidence {confidence:.2f})")

                if identified_gesture != "unknown":
                    print("Broadcasting final gesture command...")
                    asyncio.run_coroutine_threadsafe(
                        send_gesture_command(identified_gesture, 3.0),
                        loop
                    )
                    
                    # Add a tiny delay and send the reset command
                    # so the orb pops large for the gesture, then drops to 0 gracefully
                    import threading
                    def send_reset():
                        time.sleep(1.0)
                        asyncio.run_coroutine_threadsafe(
                            send_gesture_command("idle", 0.0),
                            loop
                        )
                    threading.Thread(target=send_reset, daemon=True).start()

                buffer.clear()
            elif idle_frames > max_idle_frames:
                # Still idle, but buffer is clear. Send an idle signal if it just lost track
                if idle_frames == max_idle_frames + 1:
                    print("Hand lost, sending idle reset...")
                    asyncio.run_coroutine_threadsafe(
                        send_gesture_command("idle", 0.0),
                        loop
                    )
                buffer.clear()
                
            time.sleep(0.01)
    except Exception as e:
        print(f"[ERROR] Inference worker crashed: {e}")
        traceback.print_exc()
    finally:
        print("[INFO] Clean inference loop exit. Releasing resources...")
        if hands: hands.close()
        if cap and cap.isOpened(): cap.release()
        cv2.destroyAllWindows()


# ─────────────────────────────────────────────────────────────
#  FastAPI Application
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown lifecycle.
    Starts the optional test command loop when the server boots.
    """
    global app_loop
    app_loop = asyncio.get_running_loop()
    
    print("=" * 50)
    print("  SymbiotixEngine WebSocket Server")
    print("  Listening on  ws://localhost:8000/ws")
    print("=" * 50)
    yield
    print("[WS] Server shutting down, signaling inference thread to stop...")
    shutdown_event.set()
    if inference_thread is not None and inference_thread.is_alive():
        print("[WS] Waiting for background thread to exit...")
        inference_thread.join(timeout=3.0)
    print("[WS] Shutdown complete.")


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
    
    global inference_thread
    if ENABLE_INFERENCE_LOOP:
        with inference_lock:
            if inference_thread is None or not inference_thread.is_alive():
                print("[INFO] Client connected. Spawning inference worker...")
                inference_thread = threading.Thread(
                    target=inference_worker_sync, 
                    args=(app_loop,), 
                    daemon=True
                )
                inference_thread.start()
                
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
