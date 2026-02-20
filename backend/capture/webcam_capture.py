"""
SymbiotixEngine - Webcam Gesture Capture Module

Captures hand gesture data using OpenCV and MediaPipe Hands.
Tracks up to 2 hands with 21 landmarks each, records per-frame
landmark data, and saves structured JSON files for downstream processing.

Controls:
    r - Start recording gesture
    s - Stop recording and save data
    q - Quit application

Usage:
    python webcam_capture.py
"""

import cv2
import mediapipe as mp
import json
import os
import time
import sys


# ─────────────────────────── Constants ───────────────────────────

CAMERA_INDEX = 0
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
MAX_NUM_HANDS = 2

# Resolve data output path relative to project root
# Assumes script is run from project root or via `backend/capture/webcam_capture.py`
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

VALID_HANDS = ("left", "right", "both")
VALID_SPEEDS = ("slow", "medium", "fast")


# ─────────────────────────── Camera Setup ───────────────────────────

def initialize_camera(index=CAMERA_INDEX):
    """Open the webcam and attempt to set 1080p resolution.

    Args:
        index: Camera device index (default 0).

    Returns:
        cv2.VideoCapture object.

    Raises:
        RuntimeError: If the camera cannot be opened.
    """
    print(f"[INFO] Opening camera {index}...")
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        raise RuntimeError(
            f"[ERROR] Cannot open camera at index {index}. "
            "Check that a webcam is connected and not in use by another application."
        )

    # Attempt 1080p — camera will fall back to its best supported resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera opened at {actual_w}x{actual_h}")

    return cap


# ─────────────────────────── MediaPipe Setup ───────────────────────────

def initialize_hands():
    """Create and return a configured MediaPipe Hands instance.

    Returns:
        Tuple of (mp_hands.Hands instance, mp_drawing, mp_hands module).
    """
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=MAX_NUM_HANDS,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
    )

    print("[INFO] MediaPipe Hands initialized")
    return hands, mp_drawing, mp_hands


# ─────────────────────────── Frame Processing ───────────────────────────

def process_frame(frame, hands):
    """Run MediaPipe hand detection on a single BGR frame.

    Args:
        frame: BGR image from OpenCV.
        hands: MediaPipe Hands instance.

    Returns:
        MediaPipe results object.
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb_frame.flags.writeable = False
    results = hands.process(rgb_frame)
    rgb_frame.flags.writeable = True
    return results


def extract_landmarks(results):
    """Extract landmark data from MediaPipe results.

    Produces a list of dicts, one per detected hand, each containing
    the hand label and 21 landmarks with normalized coordinates.

    Args:
        results: MediaPipe detection results.

    Returns:
        List of dicts with keys: hand, landmarks.
        Empty list if no hands detected.
    """
    if not results.multi_hand_landmarks or not results.multi_handedness:
        return []

    hands_data = []

    for hand_landmarks, handedness in zip(
        results.multi_hand_landmarks, results.multi_handedness
    ):
        # MediaPipe labels are mirrored (Classification label "Right" means
        # the user's right hand when facing the camera).
        label = handedness.classification[0].label.lower()

        landmarks = []
        for idx, lm in enumerate(hand_landmarks.landmark):
            landmarks.append({
                "id": idx,
                "x": round(lm.x, 6),
                "y": round(lm.y, 6),
                "z": round(lm.z, 6),
            })

        hands_data.append({
            "hand": label,
            "landmarks": landmarks,
        })

    return hands_data


def draw_landmarks(frame, results, mp_drawing, mp_hands):
    """Draw detected hand landmarks and connections on the frame.

    Args:
        frame: BGR image to draw on (modified in-place).
        results: MediaPipe detection results.
        mp_drawing: MediaPipe drawing utilities module.
        mp_hands: MediaPipe hands module (for connection spec).
    """
    if not results.multi_hand_landmarks:
        return

    for hand_landmarks in results.multi_hand_landmarks:
        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
            mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2),
        )


# ─────────────────────────── Recording & Saving ───────────────────────────

def get_recording_metadata():
    """Prompt the user for recording metadata via terminal input.

    Returns:
        Dict with keys: username, gesture_name, hand_used, speed_label.
        Returns None if the user cancels (empty username).
    """
    print("\n" + "=" * 50)
    print("  SAVE RECORDING")
    print("=" * 50)

    username = input("  Username: ").strip()
    if not username:
        print("[WARN] Empty username — recording discarded.")
        return None

    gesture_name = input("  Gesture name: ").strip()
    if not gesture_name:
        print("[WARN] Empty gesture name — recording discarded.")
        return None

    hand_used = input(f"  Hand used ({'/'.join(VALID_HANDS)}): ").strip().lower()
    if hand_used not in VALID_HANDS:
        print(f"[WARN] Invalid hand '{hand_used}'. Defaulting to 'right'.")
        hand_used = "right"

    speed_label = input(f"  Speed ({'/'.join(VALID_SPEEDS)}): ").strip().lower()
    if speed_label not in VALID_SPEEDS:
        print(f"[WARN] Invalid speed '{speed_label}'. Defaulting to 'medium'.")
        speed_label = "medium"

    return {
        "username": username,
        "gesture_name": gesture_name,
        "hand_used": hand_used,
        "speed_label": speed_label,
    }


def save_recording(frames_data, metadata):
    """Save recorded frames data as a formatted JSON file.

    Output path: data/raw/<username>/<gesture_name>/<hand>_<speed>_<timestamp>.json

    Args:
        frames_data: List of per-frame dicts (timestamp, hand, landmarks).
        metadata: Dict from get_recording_metadata().

    Returns:
        Path to the saved file, or None on failure.
    """
    if not frames_data:
        print("[WARN] No frame data to save.")
        return None

    output_dir = os.path.join(
        DATA_RAW_DIR,
        metadata["username"],
        metadata["gesture_name"],
    )
    os.makedirs(output_dir, exist_ok=True)

    timestamp_str = str(int(time.time()))
    filename = (
        f"{metadata['hand_used']}_{metadata['speed_label']}_{timestamp_str}.json"
    )
    filepath = os.path.join(output_dir, filename)

    output_payload = {
        "metadata": {
            "username": metadata["username"],
            "gesture_name": metadata["gesture_name"],
            "hand_used": metadata["hand_used"],
            "speed_label": metadata["speed_label"],
            "total_frames": len(frames_data),
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "frames": frames_data,
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved recording to: {filepath}")
        return filepath
    except OSError as e:
        print(f"[ERROR] Failed to save recording: {e}")
        return None


# ─────────────────────────── HUD Overlay ───────────────────────────

def draw_hud(frame, is_recording, frame_count):
    """Draw heads-up display info on the preview frame.

    Args:
        frame: BGR image to draw on (modified in-place).
        is_recording: Whether recording is active.
        frame_count: Number of frames recorded so far.
    """
    h, w = frame.shape[:2]

    # Status bar background
    cv2.rectangle(frame, (0, 0), (w, 40), (30, 30, 30), -1)

    # Title
    cv2.putText(
        frame, "SymbiotixEngine Capture",
        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1,
    )

    # Controls hint
    cv2.putText(
        frame, "R:Record  S:Stop  Q:Quit",
        (w - 320, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1,
    )

    if is_recording:
        # Red recording indicator
        cv2.circle(frame, (w - 340, 22), 8, (0, 0, 255), -1)
        cv2.putText(
            frame, f"REC  Frames: {frame_count}",
            (w - 325, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
        )


# ─────────────────────────── Main Loop ───────────────────────────

def main():
    """Main application loop: capture → detect → display → record."""
    print("=" * 50)
    print("  SymbiotixEngine — Webcam Gesture Capture")
    print("=" * 50)
    print("  Controls:")
    print("    r — Start recording")
    print("    s — Stop recording & save")
    print("    q — Quit")
    print("=" * 50 + "\n")

    cap = None
    hands = None

    try:
        cap = initialize_camera()
        hands, mp_drawing, mp_hands = initialize_hands()

        is_recording = False
        frames_data = []

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame from camera.")
                break

            # Flip horizontally for a mirror-view experience
            frame = cv2.flip(frame, 1)

            # Process hand detection
            results = process_frame(frame, hands)

            # Draw landmarks on preview
            draw_landmarks(frame, results, mp_drawing, mp_hands)

            # Record if active
            if is_recording:
                hand_data_list = extract_landmarks(results)
                for hand_data in hand_data_list:
                    frame_record = {
                        "timestamp": round(time.time(), 4),
                        "hand": hand_data["hand"],
                        "landmarks": hand_data["landmarks"],
                    }
                    frames_data.append(frame_record)

            # Draw HUD overlay
            draw_hud(frame, is_recording, len(frames_data))

            # Show preview
            cv2.imshow("SymbiotixEngine Capture", frame)

            # Handle keypresses (1ms wait for smooth preview)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("r") and not is_recording:
                is_recording = True
                frames_data = []
                print("[INFO] Recording started — perform your gesture now.")

            elif key == ord("s") and is_recording:
                is_recording = False
                print(f"[INFO] Recording stopped — {len(frames_data)} frames captured.")

                metadata = get_recording_metadata()
                if metadata:
                    save_recording(frames_data, metadata)
                else:
                    print("[INFO] Recording discarded.")
                frames_data = []

            elif key == ord("q"):
                print("[INFO] Quitting...")
                break

    except RuntimeError as e:
        print(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Graceful cleanup
        if hands:
            hands.close()
            print("[INFO] MediaPipe Hands released.")
        if cap and cap.isOpened():
            cap.release()
            print("[INFO] Camera released.")
        cv2.destroyAllWindows()
        print("[INFO] All windows closed. Goodbye!")


# ─────────────────────────── Entry Point ───────────────────────────

if __name__ == "__main__":
    main()
