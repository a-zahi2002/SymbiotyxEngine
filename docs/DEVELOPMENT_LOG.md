# Development Log

This document serves as a chronological record of the development process for the **Symbiotix Engine**. It tracks features implemented, bugs resolved, and architectural decisions made over the course of the project.

## Phase 1: Foundational Setup & Architecture
- **Environment Initialization:** Set up standard project structure separating Python backend (`backend/`) and Unity frontend (`unity/AetherUI/`).
- **Dependencies Installed:** Configured Python 3.11 environment with `fastapi`, `uvicorn`, `opencv-python`, `mediapipe`, `torch`, and `websockets`. Resolved Windows C++ redistributable compatibility issues for MediaPipe and PyTorch.
- **Git Setup:** Configured `.gitignore` targeting Python and Unity builds.

## Phase 2: Computer Vision & Real-Time Tracking
- **MediaPipe Hookup:** Wrote `webcam_capture.py` to interface with OpenCV, flip the camera for a mirror perspective, and extract 21 3D hand coordinates.
- **Sequence Buffer:** Designed `SequenceBuffer.py` to hold temporal "windows" of hand coordinates to allow tracking of gestures over time, rather than static frame poses.
- **Live Intensity Tracking:** Implemented logic within the main capture loop to extract the active bounding box scale of the hand. This is dynamically converted into a live "tracking intensity" value (0.5 to 3.0) to provide real-time distance and scale metrics before a gesture finishes.

## Phase 3: Backend Server & Threading
- **FastAPI / WebSocket Setup:** Built `websocket_server.py` to route events to connected Unity clients.
- **Asynchronous Threading Fix:** Identified that OpenCV's blocking `cap.read()` would throttle the asynchronous FastAPI loop. Rewrote `inference_worker_sync` to run independently inside a daemon thread (`threading.Thread`).
- **Mock Fallback System:** Added a defensive fallback layer so that if the PyTorch AI model (`gesture_model.pth`) is missing or fails to load, the server naturally degrades into a simulation mode. It still tracks hands and keeps the camera open, but generates simulated ML predictions (e.g., random swipes/zooms) for frontend testing.

## Phase 4: Unity Client Integration (AetherUI)
- **WebSocket Receiver:** Created `CommandReceiver.cs` using bridging NativeWebSocket functions to securely parse incoming JSON strings (`{"command": "swipe", "intensity": 2.5}`).
- **Focus Loss Fix:** Unity naturally suspends its main `Update()` loop when the game window loses focus (e.g., when clicking the OpenCV Python window). Added `Application.runInBackground = true` to the Awake loop to force continuous networking polling.
- **Thread Safety:** Bound NativeWebSocket's `DispatchMessageQueue()` directly into the Unity `Update()` loop to prevent asynchronous networking payloads from triggering `MissingReferenceException` crashes on Scene objects.

## Phase 5: Visual Feedback & 3D Mapping
- **Gesture Mappings (`OrbEffects.cs`):** Hooked the parsed JSON events into physical 3D transforms for a "GestureOrb".
  - Transformed string semantic commands into localized movements (Swipes = Local translation, Rotations = Quaternion.Slerp, Zooms = Z-Axis pushing).
- **Procedural VFX:** Rewrote the UI response to automatically instantiate and scale visual polish based on raw tracking intensity:
  - Added a `TrailRenderer` that interpolates color and width during movement.
  - Added an HDR `_EmissionColor` glow MaterialPropertyBlock.
  - Added a `ParticleSystem` that emits a burst upon reaching a high-intensity threshold from a distinct UI command.
