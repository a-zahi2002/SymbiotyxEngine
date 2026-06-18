"""
dataset_capture.py
------------------
Interactive utility to capture hand gesture sequences and perform automatic data augmentation.
Saves raw data and augmented variants (noise, scaling, temporal stretching) for training.
"""

import cv2
import mediapipe as mp
import json
import os
import time
import sys
import numpy as np
from scipy.interpolate import interp1d

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.capture.sequence_buffer import SequenceBuffer
from backend.capture.webcam_capture import initialize_camera, initialize_hands, process_frame, extract_landmarks, draw_landmarks, draw_hud

DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
os.makedirs(DATA_RAW_DIR, exist_ok=True)
os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)

TARGET_FRAMES = 50

def augment_sequence(frames: list[dict]) -> list[list[dict]]:
    """
    Applies Gaussian noise, spatial scaling, and temporal stretching to a sequence.
    """
    augmented_sequences = []

    # Extract raw trajectory
    coords = []
    for f in frames:
        frame_coords = []
        for lm in f["landmarks"]:
            frame_coords.append([lm["x"], lm["y"], lm["z"]])
        coords.append(frame_coords)
    coords = np.array(coords) # shape (num_frames, 21, 3)
    num_frames = coords.shape[0]

    # --- 1. Gaussian Noise Augmentation ---
    noise = np.random.normal(0, 0.008, coords.shape)
    noise_coords = coords + noise
    augmented_sequences.append(("noise", noise_coords))

    # --- 2. Spatial Scaling Augmentation (0.9x and 1.1x) ---
    augmented_sequences.append(("scale_down", coords * 0.9))
    augmented_sequences.append(("scale_up", coords * 1.1))

    # --- 3. Temporal Stretching & Compression ---
    # Interpolate along time axis to stretch (1.2x slower) and compress (0.8x faster)
    for name, factor in [("stretch", 1.25), ("compress", 0.75)]:
        new_len = int(num_frames * factor)
        if new_len < 10: new_len = 10
        
        old_indices = np.arange(num_frames)
        new_indices = np.linspace(0, num_frames - 1, new_len)
        
        stretched_coords = np.zeros((new_len, 21, 3))
        for lm in range(21):
            for dim in range(3):
                f_interp = interp1d(old_indices, coords[:, lm, dim], kind='linear')
                stretched_coords[:, lm, dim] = f_interp(new_indices)
                
        augmented_sequences.append((name, stretched_coords))

    # Convert numpy arrays back to list of frame dicts
    results = []
    for aug_name, aug_coords in augmented_sequences:
        aug_frames = []
        for f_idx in range(len(aug_coords)):
            lms = []
            for lm_idx in range(21):
                lms.append({
                    "id": lm_idx,
                    "x": round(float(aug_coords[f_idx, lm_idx, 0]), 6),
                    "y": round(float(aug_coords[f_idx, lm_idx, 1]), 6),
                    "z": round(float(aug_coords[f_idx, lm_idx, 2]), 6)
                })
            aug_frames.append({
                "timestamp": round(time.time() + f_idx * 0.03, 4),
                "hand": frames[0]["hand"],
                "landmarks": lms
            })
        results.append((aug_name, aug_frames))

    return results

def save_sequence(username: str, gesture_name: str, hand: str, speed: str, frames: list[dict], suffix: str = ""):
    """
    Saves a frame sequence to data/raw or data/processed.
    """
    folder = os.path.join(DATA_RAW_DIR if not suffix else DATA_PROCESSED_DIR, username, gesture_name)
    os.makedirs(folder, exist_ok=True)

    timestamp = int(time.time())
    file_suffix = f"_{suffix}" if suffix else ""
    filename = f"{hand}_{speed}_{timestamp}{file_suffix}.json"
    filepath = os.path.join(folder, filename)

    payload = {
        "metadata": {
            "username": username,
            "gesture_name": gesture_name,
            "hand_used": hand,
            "speed_label": speed,
            "total_frames": len(frames),
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "augmentation": suffix or "none"
        },
        "frames": frames
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def main():
    print("=" * 60)
    print("  🌌 SymbiotixEngine Cultivation Mudra Capture Tool")
    print("=" * 60)

    username = input("Username (default: cultivator): ").strip() or "cultivator"
    gesture_name = input("Gesture Mudra to capture (e.g. LOTUS_SEAL): ").strip().upper()
    if not gesture_name:
        print("[ERROR] Mudra name is required!")
        return

    hand = input("Hand used (left/right, default: right): ").strip().lower() or "right"
    speed = input("Speed (slow/medium/fast, default: medium): ").strip().lower() or "medium"
    
    samples_to_capture = int(input("How many samples to capture? (default: 15): ") or 15)

    cap = initialize_camera()
    hands, mp_drawing, mp_hands = initialize_hands()

    print("\n[INFO] Setup complete! Press SPACE to start capturing a sample, or Q to quit.")
    
    current_sample = 0
    try:
        while current_sample < samples_to_capture:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.flip(frame, 1)
            results = process_frame(frame, hands)
            draw_landmarks(frame, results, mp_drawing, mp_hands)

            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, 0), (w, 50), (20, 20, 20), -1)
            cv2.putText(
                frame, f"Mudra: {gesture_name} | Sample: {current_sample + 1}/{samples_to_capture}",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 215, 0), 2
            )
            cv2.putText(
                frame, "Press SPACE to record. Q to Quit.",
                (w - 350, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1
            )

            cv2.imshow("Mudra Capture", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord(' '):
                # Start countdown
                for count in [3, 2, 1]:
                    temp_ret, temp_frame = cap.read()
                    if temp_ret:
                        temp_frame = cv2.flip(temp_frame, 1)
                        cv2.rectangle(temp_frame, (0, 0), (w, 50), (20, 20, 20), -1)
                        cv2.putText(
                            temp_frame, f"Starting in {count}...",
                            (w // 2 - 100, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3
                        )
                        cv2.imshow("Mudra Capture", temp_frame)
                        cv2.waitKey(1000)

                # Capture loop
                print(f"[CAPTURE] Recording sample {current_sample+1}...")
                buffer = SequenceBuffer()
                
                while len(buffer) < TARGET_FRAMES:
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.flip(frame, 1)
                    results = process_frame(frame, hands)
                    draw_landmarks(frame, results, mp_drawing, mp_hands)
                    
                    hand_data_list = extract_landmarks(results)
                    # Filter for our specific hand if multiple are detected
                    target_hand_data = None
                    for hd in hand_data_list:
                        if hd["hand"] == hand:
                            target_hand_data = hd
                            break
                            
                    # Default to first hand if specific hand not found
                    if not target_hand_data and hand_data_list:
                        target_hand_data = hand_data_list[0]

                    if target_hand_data:
                        frame_record = {
                            "timestamp": round(time.time(), 4),
                            "hand": target_hand_data["hand"],
                            "landmarks": target_hand_data["landmarks"],
                            "wrist_absolute": target_hand_data["wrist_absolute"]
                        }
                        buffer.add_frame(frame_record)

                    # HUD progress
                    cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 150), -1)
                    cv2.putText(
                        frame, f"RECORDING MUDRA... Frames: {len(buffer)}/{TARGET_FRAMES}",
                        (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
                    )
                    cv2.imshow("Mudra Capture", frame)
                    cv2.waitKey(20)

                # Save raw and augmented sequences
                raw_frames = buffer.get_sequence()
                if len(raw_frames) == TARGET_FRAMES:
                    # Save raw
                    save_sequence(username, gesture_name, hand, speed, raw_frames)
                    
                    # Augment and save
                    try:
                        aug_results = augment_sequence(raw_frames)
                        for aug_name, aug_frames in aug_results:
                            save_sequence(username, gesture_name, hand, speed, aug_frames, suffix=aug_name)
                        print(f"[SUCCESS] Sample {current_sample+1} saved with 5 augmentations.")
                        current_sample += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to augment sample: {e}")
                else:
                    print("[WARN] Sample capture incomplete or dropped. Please retry.")
                time.sleep(1.0)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if hands: hands.close()

if __name__ == "__main__":
    main()
