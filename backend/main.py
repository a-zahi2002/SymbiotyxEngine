"""
main.py
-------
A working recording prototype for SymbiotixEngine.
Integrates camera access, hand tracking, gesture analysis, 
velocity calculation, and sequence buffering.

Controls:
    r - Start recording
    s - Stop recording and save to JSON
    c - Cancel recording (discard data)
    q - Quit application
"""

import cv2
import sys
import os
import time
import json

# Add project root to path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.camera import CameraManager
from backend.core.tracker import HandTracker
from backend.core.gesture_engine import GestureEngine
from backend.capture.sequence_buffer import SequenceBuffer
import backend.intensity.intensity_analysis as intensity
import backend.config as config

def get_save_metadata():
    """
    Prompt user for metadata for saving the sequence.
    """
    print("\n" + "="*30)
    print("  RECORDING METADATA")
    print("="*30)
    username = input("Username: ").strip() or "default_user"
    gesture_name = input("Gesture Name: ").strip() or "test_gesture"
    hand_used = input("Hand Used (left/right/both): ").strip() or "right"
    speed_label = input("Speed Label (slow/medium/fast): ").strip() or "medium"
    return {
        "username": username,
        "gesture_name": gesture_name,
        "hand_used": hand_used,
        "speed_label": speed_label
    }

def save_sequence_to_json(sequence: list, metadata: dict):
    """
    Saves the buffered sequence to a JSON file.
    
    Path: data/raw/<username>/<gesture_name>/<hand>_<speed>_<timestamp>.json
    """
    if not sequence:
        print("[WARN] No data to save.")
        return

    # 1. Setup path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.path.join(
        project_root, "data", "raw", 
        metadata["username"], 
        metadata["gesture_name"]
    )
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())
    filename = f"{metadata['hand_used']}_{metadata['speed_label']}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # 2. Prepare payload
    payload = {
        "metadata": {
            **metadata,
            "total_frames": len(sequence),
            "timestamp": timestamp,
            "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "frames": sequence
    }

    # 3. Write file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[SUCCESS] Sequence saved to: {filepath}")
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")

def convert_to_dict_list(hand_landmarks) -> list:
    """
    Converts MediaPipe landmarks to a list of dictionaries.
    """
    landmarks = []
    for idx, lm in enumerate(hand_landmarks.landmark):
        landmarks.append({
            "id": idx,
            "x": round(lm.x, 6),
            "y": round(lm.y, 6),
            "z": round(lm.z, 6)
        })
    return landmarks

def run_backend():
    """
    Main loop integrating all SymbiotixEngine components.
    """
    # Initialize Components
    camera = CameraManager(config.CAMERA_INDEX)
    tracker = HandTracker(config.MAX_HANDS)
    engine = GestureEngine()
    buffer = SequenceBuffer()

    is_recording = False
    print("\n--- SymbiotixEngine Backend Prototype ---")
    print("Controls: [R] Start  [S] Save  [C] Cancel  [Q] Quit")

    try:
        while True:
            # 1. Capture Frame
            success, frame = camera.read()
            if not success:
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # 2. Track Hands
            landmarks_list = tracker.process(frame)
            
            current_frame_data = None

            if landmarks_list:
                # For this prototype, we'll focus on the first detected hand
                hand_landmarks = landmarks_list[0]
                
                # Convert landmarks to dictionary format
                landmarks_dict = convert_to_dict_list(hand_landmarks)
                
                # Analyze Gesture
                gesture_info = engine.analyze(landmarks_dict)
                
                # Prepare frame dictionary
                current_frame_data = {
                    "timestamp": round(time.time(), 4),
                    "landmarks": landmarks_dict,
                    "gesture": gesture_info["gesture"],
                    "velocity": 0.0
                }

                # 3. Intensity Analysis (Velocity)
                if len(buffer) > 0:
                    prev_frame = buffer.get_sequence()[-1]
                    # Calculate velocity between previous frame and current
                    velocity = intensity.compute_frame_velocity(prev_frame, current_frame_data)
                    current_frame_data["velocity"] = round(velocity, 4)

                # 4. Buffer logic
                if is_recording:
                    buffer.add_frame(current_frame_data)

                # 5. Visual Feedback (Draw landmarks)
                tracker.draw_landmarks(frame, [hand_landmarks])
                
                # Draw Gesture Info on frame
                cv2.putText(frame, f"Gesture: {gesture_info['gesture']}", 
                            (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Velocity: {current_frame_data['velocity']:.2f}", 
                            (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # 6. HUD - Recording Status
            if is_recording:
                cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)
                cv2.putText(frame, f"RECORDING - Frames: {len(buffer)}", 
                            (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "READY", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 7. Display
            cv2.imshow("SymbiotixEngine Prototype", frame)

            # 8. Keyboard Input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[INFO] Quitting...")
                break
            elif key == ord('r'):
                if not is_recording:
                    is_recording = True
                    buffer.clear()
                    print("[INFO] Recording started...")
            elif key == ord('s'):
                if is_recording:
                    is_recording = False
                    print(f"[INFO] Recording stopped. Total frames: {len(buffer)}")
                    metadata = get_save_metadata()
                    save_sequence_to_json(buffer.get_sequence(), metadata)
                    buffer.clear()
            elif key == ord('c'):
                if is_recording:
                    is_recording = False
                    buffer.clear()
                    print("[INFO] Recording canceled. Buffer cleared.")

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_backend()
