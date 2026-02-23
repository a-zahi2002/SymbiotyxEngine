# Computer Vision & Capture Pipeline

## Overview
The computer vision pipeline is the sensory organ of the Symbiotix Engine. Its primary goal is to reliably extract human intent from raw video streams with minimal latency, transforming pixels into structured contextual data.

## Core Technologies
- **OpenCV (`cv2`):** Handles camera interfacing, frame reading, and image flipping (to create a mirror effect for intuitive interaction).
- **MediaPipe Hands:** A highly optimized machine learning framework by Google capable of inferring 21 3D landmarks of a hand from a single frame.

## The Capture Loop (`inference_worker_sync`)
Because computer vision is notoriously CPU-intensive and blocking, the capture loop is isolated within a dedicated Python daemon thread (`threading.Thread`). This prevents the heavy OpenCV `cap.read()` operations from freezing the concurrent asynchronous WebSocket server.

### 1. Frame Processing
For every frame captured:
1. The image is flipped horizontally for a mirror effect.
2. The image is passed to `process_frame(frame, hands)` which executes the MediaPipe inference.
3. Features are optionally drawn onto a debug HUD using `draw_landmarks`.

### 2. Live Tracking Intensity
To provide continuous, organic feedback in Unity before a gesture even finishes, the system calculates a "live intensity". 
- It extracts the bounding box of the detected hand landmarks.
- The diagonal scale of this bounding box is calculated: `hand_scale = sqrt(dx^2 + dy^2)`.
- This scale is clamped and normalized into an intensity value between `0.5` and `3.0`.
- This allows the 3D Engine to physically pulse and breathe in direct synchronization with the user's hand distance.

### 3. The Sequence Buffer
Static poses form only a fraction of natural human gestures. Therefore, historical context is required.
- As landmarks are detected, they are pushed into a `SequenceBuffer` alongside their timestamp.
- The pipeline tracks an `idle_frames` counter. If the hand leaves the frame (or tracking fails) for more than `max_idle_frames` (e.g., 15 frames), the system considers the current gesture "complete".
- The buffered sequence of frames is then extracted as a single, unified temporal gesture, ready to be passed into a Neural Network for classification.

### 4. Graceful Degradation
To ensure system stability during development, the pipeline includes a robust fallback mode. If the PyTorch model (`gesture_model.pth`) is entirely missing, the system gracefully degrades:
- It keeps the OpenCV webcam live and continues to track the hand.
- Instead of crashing, it simulates a gesture prediction randomly from a predefined list (`"swipe_right"`, `"zoom_in"`, etc.).
- This allows frontend UI research and development to continue uninterrupted without requiring a fully trained neural network.
