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
    """Blocking worker that runs MediaPipe, filters, mudras, combos, runes, and spell engines, yielding gestures."""
    print("[INFO] Starting cultivation-enhanced inference_worker_sync thread...")
    try:
        import sys
        import cv2
        import numpy as np
        import mediapipe as mp
        import torch
        import traceback
        import time
        
        from backend.capture.webcam_capture import initialize_hands, process_frame, extract_landmarks, draw_landmarks, draw_hud
        from backend.models.train_gesture_model import process_sequence
        from backend.models.gesture_classifier import load_model
        from backend.capture.sequence_buffer import SequenceBuffer
        
        # New Target Architecture Imports
        from backend.filters.one_euro_filter import HandLandmarksFilter
        from backend.core.gesture_engine import GestureEngine
        from backend.gestures.dynamic_gesture_engine import HybridDynamicGestureEngine
        from backend.runes.dollar_one_recognizer import DollarOneRecognizer
        from backend.dual_hand.dual_hand_engine import DualHandEngine
        from backend.combos.combo_engine import ComboEngine
        from backend.spells.spell_engine import SpellEngine
        from backend.audio.audio_manager import AudioManager
        from backend.effects.effect_manager import effect_manager
        from backend.events.event_bus import event_bus
        import backend.intensity.intensity_analysis as intensity_analysis
        
    except Exception as e:
        print(f"[ERROR] Failed to import cultivation inference dependencies: {e}")
        traceback.print_exc()
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

    # Start audio and effect visualizers
    audio_mgr = AudioManager()
    effect_manager.run_window()

    # Instantiate cultivation components
    static_engine = GestureEngine()
    dynamic_engine = HybridDynamicGestureEngine()
    rune_recognizer = DollarOneRecognizer()
    dual_hand_engine = DualHandEngine()
    combo_engine = ComboEngine()
    spell_engine = SpellEngine()

    hand_filters = {
        "left": HandLandmarksFilter(),
        "right": HandLandmarksFilter()
    }

    # Tracking states
    drawing_trajectory = []
    is_drawing = False
    active_drawing_hand = None
    
    # Event Bus subscription to broadcast spell casts to Unity
    def on_spell_cast(payload):
        unity_payload = {
            "command": payload.get("command", "idle"),
            "intensity": payload.get("intensity", 0.0),
            "gesture": payload.get("gesture", "UNKNOWN"),
            "dynamic_gesture": payload.get("dynamic_gesture", "none"),
            "rune": payload.get("rune", "NONE"),
            "spell": payload.get("spell", "NONE"),
            "state": payload.get("state", "CASTING"),
            "velocity": payload.get("velocity", 0.0),
            "confidence": payload.get("confidence", 0.95)
        }
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(unity_payload),
            loop
        )
        print(f"[WS] Broadcast spell cast → {json.dumps(unity_payload)}")

    event_bus.subscribe("spell_cast", on_spell_cast)

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
            
            # Periodically tick the spell engine (cooldown decays)
            spell_engine.update()
            
            hand_data_list = extract_landmarks(results)
            timestamp = time.time()
            
            if len(hand_data_list) > 0:
                # 1. Filter landmarks to remove jitter
                for hd in hand_data_list:
                    h_label = hd["hand"]
                    hd["landmarks"] = hand_filters[h_label].filter(hd["landmarks"], timestamp)
                
                primary_hand = hand_data_list[0]
                h_label = primary_hand["hand"]
                
                # 2. Analyze static mudras
                gesture_res = static_engine.analyze(primary_hand["landmarks"])
                primary_gesture = gesture_res["gesture"]
                primary_confidence = gesture_res["confidence"]
                
                # Publish mudra event
                event_bus.publish("gesture_detected", hand=h_label, gesture=primary_gesture, confidence=primary_confidence)
                
                # 3. Add to Sequence Buffer
                frame_record = {
                    "timestamp": round(timestamp, 4),
                    "hand": h_label,
                    "landmarks": primary_hand["landmarks"],
                    "wrist_absolute": primary_hand["wrist_absolute"]
                }
                buffer.add_frame(frame_record)
                
                if idle_frames > 0:
                    print("Hand detected, tracking started...")
                idle_frames = 0
                total_frames += 1

                # Calculate frame velocity
                velocity = 0.0
                if len(buffer) > 1:
                    prev_frame = buffer.get_sequence()[-2]
                    velocity = intensity_analysis.compute_frame_velocity(prev_frame, frame_record)
                
                live_intensity = max(0.5, min(velocity * 8.0, 5.0))
                event_bus.publish("intensity_changed", velocity=velocity, intensity_val=live_intensity)

                # 4. Handle Rune Drawing
                if primary_gesture in ("POINTING", "PINCH"):
                    if not is_drawing:
                        is_drawing = True
                        active_drawing_hand = h_label
                        drawing_trajectory = []
                        print(f"[RUNE] Started drawing seal with {h_label} hand...")
                    
                    # Extract absolute index finger tip (landmark 8) robustly by ID
                    idx_lm = next((lm for lm in primary_hand["landmarks"] if lm["id"] == 8), None)
                    if idx_lm is not None:
                        abs_x = idx_lm["x"] + primary_hand["wrist_absolute"]["x"]
                        abs_y = idx_lm["y"] + primary_hand["wrist_absolute"]["y"]
                        drawing_trajectory.append((abs_x, abs_y))
                else:
                    if is_drawing:
                        is_drawing = False
                        if len(drawing_trajectory) >= 12:
                            rune_res = rune_recognizer.recognize(drawing_trajectory)
                            if rune_res["confidence"] > 0.75:
                                event_bus.publish("rune_detected", rune=rune_res["rune"], confidence=rune_res["confidence"])
                        drawing_trajectory = []

                # 5. Dual Hand Mudras
                if len(hand_data_list) >= 2:
                    left_hd = next((h for h in hand_data_list if h["hand"] == "left"), None)
                    right_hd = next((h for h in hand_data_list if h["hand"] == "right"), None)
                    if left_hd and right_hd:
                        left_res = static_engine.analyze(left_hd["landmarks"])
                        right_res = static_engine.analyze(right_hd["landmarks"])
                        dual_spell = dual_hand_engine.analyze(left_res["gesture"], right_res["gesture"])
                        if dual_spell:
                            event_bus.publish("dual_hand_detected", spell_name=dual_spell)

                # 6. Combo sequences over time
                combo_spell = combo_engine.update(primary_gesture)
                if combo_spell:
                    event_bus.publish("combo_detected", spell_name=combo_spell)

                # 7. Draw HUD and traces on OpenCV frame
                # Draw drawing path (runes) if active
                if is_drawing and len(drawing_trajectory) > 1:
                    for i in range(1, len(drawing_trajectory)):
                        p1 = (int(drawing_trajectory[i-1][0] * frame.shape[1]), int(drawing_trajectory[i-1][1] * frame.shape[0]))
                        p2 = (int(drawing_trajectory[i][0] * frame.shape[1]), int(drawing_trajectory[i][1] * frame.shape[0]))
                        cv2.line(frame, p1, p2, (0, 215, 255), 3) # golden draw line

                # Stream live tracking to Unity
                if total_frames % 2 == 0:
                    live_payload = {
                        "command": "tracking",
                        "intensity": round(live_intensity, 4),
                        "gesture": primary_gesture,
                        "dynamic_gesture": "none",
                        "rune": "NONE",
                        "spell": "NONE",
                        "state": spell_engine.state,
                        "velocity": round(velocity, 4),
                        "confidence": primary_confidence
                    }
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(live_payload),
                        loop
                    )
                    
                # HUD text on frame
                hud_text = f"Mudra: {primary_gesture} | Qi State: {spell_engine.state}"
                cv2.putText(frame, hud_text, (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Qi Energy: {spell_engine.qi_level:.1f}", (20, frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                idle_frames += 1
                if is_drawing:
                    is_drawing = False
                    if len(drawing_trajectory) >= 12:
                        rune_res = rune_recognizer.recognize(drawing_trajectory)
                        if rune_res["confidence"] > 0.75:
                            event_bus.publish("rune_detected", rune=rune_res["rune"], confidence=rune_res["confidence"])
                    drawing_trajectory = []

            # Check for dynamic gesture completion (swipes, etc.)
            if idle_frames > max_idle_frames and len(buffer) > 10:
                print("Sequence complete - running dynamic classification...")
                seq_data = buffer.get_sequence()
                motion_res = dynamic_engine.recognize(seq_data)
                
                if motion_res["motion"] != "unknown":
                    print(f"Prediction: {motion_res['motion']} (confidence {motion_res['confidence']:.2f})")
                    event_bus.publish("dynamic_gesture_detected", motion=motion_res["motion"], confidence=motion_res["confidence"])
                buffer.clear()
                
            elif idle_frames > max_idle_frames:
                if idle_frames == max_idle_frames + 1:
                    print("Hand lost, sending idle reset...")
                    event_bus.publish("spell_idle", spell=None, state="IDLE", qi=0.0)
                    spell_engine.change_state("IDLE")
                    
                    idle_payload = {
                        "command": "idle",
                        "intensity": 0.0,
                        "gesture": "UNKNOWN",
                        "dynamic_gesture": "unknown",
                        "rune": "NONE",
                        "spell": "NONE",
                        "state": "IDLE",
                        "velocity": 0.0,
                        "confidence": 0.0
                    }
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(idle_payload),
                        loop
                    )
                buffer.clear()
                
            cv2.imshow("SymbiotixEngine Inference", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] Quitting inference loop.")
                break
                
            time.sleep(0.01)
    except Exception as e:
        print(f"[ERROR] Inference worker crashed: {e}")
        traceback.print_exc()
    finally:
        print("[INFO] Clean inference loop exit. Releasing resources...")
        if 'hands' in locals() and hands:
            hands.close()
        if 'cap' in locals() and cap and cap.isOpened():
            cap.release()
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
