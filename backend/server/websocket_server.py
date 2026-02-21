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
#  Test-Mode Background Task
#  Sends a "zoom_in" command every 2 seconds so Unity can be
#  tested without needing the full gesture pipeline running.
# ─────────────────────────────────────────────────────────────

# Set this to False (or remove the task) when using real gesture data.
ENABLE_TEST_LOOP: bool = True

async def test_command_loop() -> None:
    """
    Background coroutine that broadcasts a test gesture command
    every 2 seconds to all connected Unity clients.

    The intensity oscillates between 0.5 and 2.5 using a simple
    sine-like pattern so you can visually verify that OrbEffects
    reacts to changing values.
    """
    import math

    print("[TEST] Test command loop started (sending every 2s)")
    tick = 0
    while True:
        await asyncio.sleep(2.0)

        if manager.client_count == 0:
            # No clients connected; skip sending.
            continue

        # Oscillate intensity: range [0.5 … 2.5]
        intensity = 1.5 + math.sin(tick * 0.5)
        tick += 1

        payload = {
            "command": "zoom_in",
            "intensity": round(intensity, 4)
        }

        await manager.broadcast(payload)
        print(f"[TEST] Broadcast → {json.dumps(payload)}  "
              f"({manager.client_count} client(s))")


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
    if ENABLE_TEST_LOOP:
        task = asyncio.create_task(test_command_loop())
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
        "test_loop_enabled": ENABLE_TEST_LOOP,
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
