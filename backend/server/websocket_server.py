"""
websocket_server.py
-------------------
FastAPI WebSocket server for SymbiotixEngine.

Sends real-time gesture commands to Unity (AetherUI) over WebSocket.
Runs on localhost:8000 with a /ws endpoint that any number of Unity
clients can connect to simultaneously.

Architecture (Windows-safe):
  - The FastAPI server runs the WebSocket and HTTP endpoints.
  - When the first Unity client connects, a SEPARATE PROCESS is spawned
    to run the camera/inference loop. This is required on Windows because
    OpenCV imshow() windows MUST run on the main thread of a process —
    they cannot run inside a threading.Thread spawned inside an asyncio app.
  - The subprocess communicates back to this server via a named pipe / stdin
    or via HTTP POST to /send_command endpoint.

Usage:
    # From the project root (SymbiotixEngine/):
    python -m backend.server.websocket_server

Dependencies:
    pip install fastapi uvicorn

Compatible with Python 3.10+
"""

import asyncio
import json
import time
import threading
import subprocess
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.capture.sequence_buffer import SequenceBuffer

# ─────────────────────────────────────────────────────────────
#  Connection Manager
# ─────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        client = websocket.client
        print(f"[WS] Client connected: {client.host}:{client.port}  "
              f"(total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        client = websocket.client
        print(f"[WS] Client disconnected: {client.host}:{client.port}  "
              f"(total: {len(self.active_connections)})")

    async def send_to(self, websocket: WebSocket, data: dict) -> None:
        await websocket.send_json(data)

    async def broadcast(self, data: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                stale.append(connection)
        for ws in stale:
            if ws in self.active_connections:
                self.active_connections.remove(ws)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Global manager instance
manager = ConnectionManager()

# Global state for subprocess
inference_proc: subprocess.Popen | None = None
inference_lock = threading.Lock()
app_loop = None  # asyncio event loop reference

# ─────────────────────────────────────────────────────────────
#  Real Inference Model Integration
# ─────────────────────────────────────────────────────────────

# Set to False to disable camera and use a random fallback for testing
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
    """Fallback: sends random fake gestures to Unity when camera is unavailable."""
    import random
    import traceback

    print("[INFO] Running in fallback test mode (no camera/inference available)...")
    gestures = ["zoom_in", "zoom_out", "swipe_left", "swipe_right", "rotate_cw", "rotate_ccw"]

    try:
        while True:
            time.sleep(3.0)
            if manager.client_count > 0:
                gesture = random.choice(gestures)
                intensity = random.uniform(0.8, 2.5)
                print(f"[FALLBACK] Sending fake gesture: {gesture} ({intensity:.2f})")
                asyncio.run_coroutine_threadsafe(
                    send_gesture_command(gesture, intensity),
                    loop
                )
    except Exception as e:
        print(f"[ERROR] Fallback loop crashed: {e}")
        traceback.print_exc()


def launch_inference_subprocess():
    """
    Launches the camera/inference loop as a SEPARATE PROCESS.

    The subprocess runs inference_runner.py which:
      - Opens the webcam (main thread of subprocess → OpenCV works on Windows)
      - Runs MediaPipe hand tracking
      - POSTs gesture commands to this server via /send_command
    """
    global inference_proc

    runner_path = os.path.join(SCRIPT_DIR, "inference_runner.py")

    if not os.path.exists(runner_path):
        print(f"[WARN] inference_runner.py not found at {runner_path}. "
              "Starting fallback thread instead.")
        return False

    try:
        python_exe = sys.executable
        inference_proc = subprocess.Popen(
            [python_exe, runner_path],
            cwd=PROJECT_ROOT,
            stdout=None,  # Let subprocess print to same terminal
            stderr=None,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        print(f"[INFO] Inference subprocess launched (PID: {inference_proc.pid})")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch inference subprocess: {e}")
        return False


def start_inference(loop):
    """Thread-safe: launch subprocess or fallback thread."""
    global inference_proc

    with inference_lock:
        # Don't start again if already running
        if inference_proc is not None and inference_proc.poll() is None:
            return  # subprocess still alive

        if ENABLE_INFERENCE_LOOP:
            success = launch_inference_subprocess()
            if not success:
                # Fallback: run fake gestures in a background thread
                t = threading.Thread(target=run_fallback_loop, args=(loop,), daemon=True)
                t.start()
        else:
            print("[INFO] Inference disabled. Starting fallback loop.")
            t = threading.Thread(target=run_fallback_loop, args=(loop,), daemon=True)
            t.start()


# ─────────────────────────────────────────────────────────────
#  FastAPI Application
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_loop
    app_loop = asyncio.get_running_loop()

    print("=" * 50)
    print("  SymbiotixEngine WebSocket Server")
    print("  Listening on  ws://localhost:8000/ws")
    print("  Inference commands come via /send_command")
    print("=" * 50)
    yield
    print("[WS] Server shutting down...")
    if inference_proc is not None and inference_proc.poll() is None:
        print("[WS] Terminating inference subprocess...")
        inference_proc.terminate()
        try:
            inference_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            inference_proc.kill()
    print("[WS] Shutdown complete.")


app = FastAPI(
    title="SymbiotixEngine WebSocket Server",
    version="0.2.0",
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
    """
    await manager.connect(websocket)

    # Spawn inference process when first client connects
    if ENABLE_INFERENCE_LOOP and app_loop is not None:
        loop = app_loop
        t = threading.Thread(target=start_inference, args=(loop,), daemon=True)
        t.start()

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WS] Received from Unity: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────
#  REST Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/send_command")
async def send_command(
    command: str = "idle",
    intensity: float = 0.0,
    gesture: str = "UNKNOWN",
    dynamic_gesture: str = "none",
    rune: str = "NONE",
    spell: str = "NONE",
    state: str = "IDLE",
    velocity: float = 0.0,
    confidence: float = 0.0,
    hand_x: float = 0.5,
    hand_y: float = 0.5,
    hand_z: float = 0.0,
    has_hand: bool = False
):
    """
    HTTP POST endpoint to broadcast a gesture command to all Unity clients.
    The inference subprocess posts here to avoid threading issues with OpenCV.
    """
    payload = {
        "command": command,
        "intensity": round(intensity, 4),
        "gesture": gesture,
        "dynamic_gesture": dynamic_gesture,
        "rune": rune,
        "spell": spell,
        "state": state,
        "velocity": round(velocity, 4),
        "confidence": round(confidence, 4),
        "hand_x": round(hand_x, 4),
        "hand_y": round(hand_y, 4),
        "hand_z": round(hand_z, 4),
        "has_hand": has_hand
    }
    await manager.broadcast(payload)
    return JSONResponse(content={
        "status": "sent",
        "clients": manager.client_count,
        "payload": payload
    })


@app.get("/status")
async def server_status():
    """Quick health-check endpoint."""
    proc_alive = (inference_proc is not None and inference_proc.poll() is None)
    return {
        "status": "running",
        "connected_clients": manager.client_count,
        "inference_loop_enabled": ENABLE_INFERENCE_LOOP,
        "inference_subprocess_alive": proc_alive,
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
        reload=False,
        log_level="info",
    )
