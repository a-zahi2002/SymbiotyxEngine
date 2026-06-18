"""
inference_runner.py
-------------------
SymbiotixEngine — Camera Inference Runner (Standalone Process)

This script MUST run as its own process (not a thread) because:
  - OpenCV imshow() windows require the MAIN THREAD on Windows.
  - FastAPI / uvicorn uses the main thread, so we cannot call imshow() there.

This script:
  1. Opens the webcam on its main thread (works on Windows with CAP_DSHOW).
  2. Runs MediaPipe hand tracking frame-by-frame.
  3. Applies all gesture engines: static mudras, dynamic gestures,
     rune recognition, dual-hand analysis, combo engine, spell engine.
  4. POSTS results to the FastAPI server at http://localhost:8000/send_command
     (the server then broadcasts them over WebSocket to Unity).
  5. Shows a live OpenCV window with hand landmarks, HUD, and rune traces.

Launch:
    python backend/server/inference_runner.py
    (Or launched automatically by websocket_server.py)
"""

import sys
import os
import time
import traceback
import json

# ── Path setup ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── HTTP Client for posting to WebSocket server ──────────────────────────────
import urllib.request
import urllib.parse

SERVER_URL = "http://localhost:8000/send_command"

def post_command(payload: dict) -> bool:
    """POST a gesture payload to the FastAPI server via HTTP."""
    try:
        params = urllib.parse.urlencode({k: str(v) for k, v in payload.items()})
        url = f"{SERVER_URL}?{params}"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return resp.status == 200
    except Exception:
        return False  # Server not ready yet, silently skip


def run_inference():
    print("[INFERENCE] Starting SymbiotixEngine Inference Runner...")

    # ── Import dependencies ──────────────────────────────────────────────────
    try:
        import cv2
        import numpy as np
        import mediapipe as mp

        from backend.capture.webcam_capture import initialize_hands, process_frame, extract_landmarks, draw_landmarks
        from backend.capture.sequence_buffer import SequenceBuffer

        from backend.filters.one_euro_filter import HandLandmarksFilter
        from backend.core.gesture_engine import GestureEngine
        from backend.gestures.dynamic_gesture_engine import HybridDynamicGestureEngine
        from backend.runes.dollar_one_recognizer import DollarOneRecognizer
        from backend.dual_hand.dual_hand_engine import DualHandEngine
        from backend.combos.combo_engine import ComboEngine
        from backend.spells.spell_engine import SpellEngine
        from backend.events.event_bus import event_bus
        import backend.intensity.intensity_analysis as intensity_analysis

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        traceback.print_exc()
        print("[INFERENCE] Running in DEMO mode — sending fake gestures to test Unity connection...")
        run_demo_mode()
        return

    # ── Open Camera (MUST be on main thread on Windows) ─────────────────────
    print("[INFERENCE] Opening webcam...")
    cap = None

    # Try CAP_DSHOW first on Windows (fastest, avoids DirectShow hang)
    if sys.platform == "win32":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[WARN] CAP_DSHOW index 0 failed. Trying default...")
            cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[WARN] Camera index 0 failed. Trying index 1...")
        if sys.platform == "win32":
            cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(1)
        else:
            cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[ERROR] Could not open any camera. Running DEMO mode.")
        run_demo_mode()
        return

    print("[INFERENCE] ✅ Webcam opened successfully!")

    # Set a reasonable resolution (720p is a good balance of quality & speed)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFERENCE] Camera resolution: {actual_w}x{actual_h}")

    # ── Initialize MediaPipe ─────────────────────────────────────────────────
    try:
        hands, mp_drawing, mp_hands = initialize_hands()
    except Exception as e:
        print(f"[ERROR] MediaPipe init failed: {e}")
        if cap.isOpened():
            cap.release()
        run_demo_mode()
        return

    # ── Initialize Cultivation Engines ──────────────────────────────────────
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

    buffer = SequenceBuffer()

    # ── Event Bus → POST to server ───────────────────────────────────────────
    # We keep a mutable dict so inner functions can update shared state
    shared = {
        "hand_x": 0.5,
        "hand_y": 0.5,
        "hand_z": 0.0,
        "has_hand": False
    }

    def on_spell_cast(payload):
        """Called by SpellEngine when a spell is cast. POSTs to server."""
        unity_payload = {
            "command": payload.get("command", "idle"),
            "intensity": payload.get("intensity", 0.0),
            "gesture": payload.get("gesture", "UNKNOWN"),
            "dynamic_gesture": payload.get("dynamic_gesture", "none"),
            "rune": payload.get("rune", "NONE"),
            "spell": payload.get("spell", "NONE"),
            "state": payload.get("state", "CASTING"),
            "velocity": payload.get("velocity", 0.0),
            "confidence": payload.get("confidence", 0.95),
            "hand_x": shared["hand_x"],
            "hand_y": shared["hand_y"],
            "hand_z": shared["hand_z"],
            "has_hand": shared["has_hand"]
        }
        post_command(unity_payload)
        print(f"[SPELL] Cast → {unity_payload.get('spell')} (intensity={unity_payload.get('intensity'):.2f})")

    event_bus.subscribe("spell_cast", on_spell_cast)

    # ── Tracking State ───────────────────────────────────────────────────────
    drawing_trajectory = []
    is_drawing = False
    idle_frames = 0
    max_idle_frames = 15
    total_frames = 0

    print("[INFERENCE] ✅ Starting inference loop. Press Q in the camera window to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)
            results = process_frame(frame, hands)
            draw_landmarks(frame, results, mp_drawing, mp_hands)

            # Tick spell engine (for cooldown decay)
            spell_engine.update()

            hand_data_list = extract_landmarks(results)
            timestamp = time.time()

            if len(hand_data_list) > 0:
                # Filter landmarks to remove jitter
                for hd in hand_data_list:
                    h_label = hd["hand"]
                    hd["landmarks"] = hand_filters[h_label].filter(hd["landmarks"], timestamp)

                primary_hand = hand_data_list[0]
                h_label = primary_hand["hand"]

                # Update shared hand coordinates
                shared["hand_x"] = round(primary_hand["wrist_absolute"]["x"], 4)
                shared["hand_y"] = round(primary_hand["wrist_absolute"]["y"], 4)
                shared["hand_z"] = round(primary_hand["wrist_absolute"]["z"], 4)
                shared["has_hand"] = True

                # Analyze static mudras
                gesture_res = static_engine.analyze(primary_hand["landmarks"])
                primary_gesture = gesture_res["gesture"]
                primary_confidence = gesture_res["confidence"]

                event_bus.publish("gesture_detected",
                                  hand=h_label,
                                  gesture=primary_gesture,
                                  confidence=primary_confidence)

                # Add to Sequence Buffer
                frame_record = {
                    "timestamp": round(timestamp, 4),
                    "hand": h_label,
                    "landmarks": primary_hand["landmarks"],
                    "wrist_absolute": primary_hand["wrist_absolute"]
                }
                buffer.add_frame(frame_record)
                idle_frames = 0
                total_frames += 1

                # Calculate frame velocity
                velocity = 0.0
                if len(buffer) > 1:
                    prev_frame = buffer.get_sequence()[-2]
                    velocity = intensity_analysis.compute_frame_velocity(prev_frame, frame_record)

                live_intensity = max(0.5, min(velocity * 8.0, 5.0))
                event_bus.publish("intensity_changed", velocity=velocity, intensity_val=live_intensity)

                # Handle Rune Drawing (POINTING or PINCH gesture)
                if primary_gesture in ("POINTING", "PINCH"):
                    if not is_drawing:
                        is_drawing = True
                        drawing_trajectory = []
                        print(f"[RUNE] Drawing seal with {h_label} hand...")

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
                                event_bus.publish("rune_detected",
                                                  rune=rune_res["rune"],
                                                  confidence=rune_res["confidence"])
                        drawing_trajectory = []

                # Dual Hand Mudras
                if len(hand_data_list) >= 2:
                    left_hd = next((h for h in hand_data_list if h["hand"] == "left"), None)
                    right_hd = next((h for h in hand_data_list if h["hand"] == "right"), None)
                    if left_hd and right_hd:
                        left_res = static_engine.analyze(left_hd["landmarks"])
                        right_res = static_engine.analyze(right_hd["landmarks"])
                        dual_spell = dual_hand_engine.analyze(left_res["gesture"], right_res["gesture"])
                        if dual_spell:
                            event_bus.publish("dual_hand_detected", spell_name=dual_spell)

                # Combo sequences over time
                combo_spell = combo_engine.update(primary_gesture)
                if combo_spell:
                    event_bus.publish("combo_detected", spell_name=combo_spell)

                # Draw rune trace on frame
                if is_drawing and len(drawing_trajectory) > 1:
                    for i in range(1, len(drawing_trajectory)):
                        p1 = (int(drawing_trajectory[i-1][0] * frame.shape[1]),
                              int(drawing_trajectory[i-1][1] * frame.shape[0]))
                        p2 = (int(drawing_trajectory[i][0] * frame.shape[1]),
                              int(drawing_trajectory[i][1] * frame.shape[0]))
                        cv2.line(frame, p1, p2, (0, 215, 255), 3)

                # Send live tracking payload to Unity every other frame
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
                        "confidence": primary_confidence,
                        "hand_x": shared["hand_x"],
                        "hand_y": shared["hand_y"],
                        "hand_z": shared["hand_z"],
                        "has_hand": True
                    }
                    post_command(live_payload)

                # HUD overlay on camera frame
                hud_line1 = f"Mudra: {primary_gesture}  |  Qi State: {spell_engine.state}  |  Spell: {getattr(spell_engine, 'current_spell', 'NONE')}"
                hud_line2 = f"Qi Energy: {getattr(spell_engine, 'qi_level', 0.0):.1f}  |  Intensity: {live_intensity:.2f}  |  Confidence: {primary_confidence:.2f}"
                cv2.rectangle(frame, (0, frame.shape[0] - 75), (frame.shape[1], frame.shape[0]), (15, 15, 25), -1)
                cv2.putText(frame, hud_line1, (15, frame.shape[0] - 48),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 2)
                cv2.putText(frame, hud_line2, (15, frame.shape[0] - 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            else:
                # No hand detected
                shared["has_hand"] = False
                idle_frames += 1

                if is_drawing:
                    is_drawing = False
                    if len(drawing_trajectory) >= 12:
                        rune_res = rune_recognizer.recognize(drawing_trajectory)
                        if rune_res["confidence"] > 0.75:
                            event_bus.publish("rune_detected",
                                              rune=rune_res["rune"],
                                              confidence=rune_res["confidence"])
                    drawing_trajectory = []

            # Check for completed gesture sequence (dynamic)
            if idle_frames > max_idle_frames and len(buffer) > 10:
                print("[INFERENCE] Sequence complete — running dynamic classification...")
                seq_data = buffer.get_sequence()
                motion_res = dynamic_engine.recognize(seq_data)

                if motion_res["motion"] != "unknown":
                    print(f"[INFERENCE] Dynamic Gesture: {motion_res['motion']} "
                          f"(confidence {motion_res['confidence']:.2f})")
                    event_bus.publish("dynamic_gesture_detected",
                                      motion=motion_res["motion"],
                                      confidence=motion_res["confidence"])
                buffer.clear()

            elif idle_frames > max_idle_frames:
                if idle_frames == max_idle_frames + 1:
                    print("[INFERENCE] Hand lost — sending idle reset to Unity...")
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
                        "confidence": 0.0,
                        "hand_x": 0.5,
                        "hand_y": 0.5,
                        "hand_z": 0.0,
                        "has_hand": False
                    }
                    post_command(idle_payload)
                buffer.clear()

            # ── Show camera window (MAIN THREAD — works on Windows!) ─────────
            cv2.imshow("SymbiotixEngine — Hand Tracking", frame)

            # Check for Q key to quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q or Escape
                print("[INFERENCE] Quit signal received. Exiting.")
                break

            time.sleep(0.005)  # ~200Hz cap (camera driver limits actual rate)

    except KeyboardInterrupt:
        print("\n[INFERENCE] Interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Inference loop crashed: {e}")
        traceback.print_exc()
    finally:
        print("[INFERENCE] Cleaning up resources...")
        try:
            if hands:
                hands.close()
        except Exception:
            pass
        try:
            if cap and cap.isOpened():
                cap.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[INFERENCE] ✅ Cleanup complete.")


def run_demo_mode():
    """
    Demo/fallback: sends fake gestures to the server so Unity can still be tested
    even without a working camera or all Python dependencies.
    """
    import random
    print("[DEMO] Running in demo mode. Sending fake gestures to Unity every 3s.")
    print("[DEMO] (Camera or dependencies unavailable)")

    gestures = ["zoom_in", "zoom_out", "swipe_left", "swipe_right", "rotate_cw", "rotate_ccw"]
    spells = ["NONE", "FIREBALL", "SHIELD", "ENERGY_SLASH", "LIGHTNING", "AURA"]

    while True:
        time.sleep(3.0)
        gesture = random.choice(gestures)
        spell = random.choice(spells)
        intensity = round(random.uniform(0.8, 2.5), 4)

        payload = {
            "command": gesture,
            "intensity": intensity,
            "gesture": "OPEN_PALM",
            "dynamic_gesture": gesture,
            "rune": "NONE",
            "spell": spell,
            "state": "CASTING" if spell != "NONE" else "IDLE",
            "velocity": round(random.uniform(0.1, 0.8), 4),
            "confidence": 0.95,
            "hand_x": round(random.uniform(0.3, 0.7), 4),
            "hand_y": round(random.uniform(0.3, 0.7), 4),
            "hand_z": round(random.uniform(0.0, 0.1), 4),
            "has_hand": True
        }
        result = post_command(payload)
        if result:
            print(f"[DEMO] Sent: {gesture} (spell={spell}, intensity={intensity:.2f})")
        else:
            print(f"[DEMO] Server not ready yet (waiting)...")


if __name__ == "__main__":
    run_inference()
