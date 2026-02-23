# System Architecture Overview

## Introduction
The **Symbiotix Engine** is designed as a real-time, cross-platform gesture recognition pipeline. It acts as a bridge between computer vision-based human-computer interaction (HCI) and 3D application environments (specifically Unity). 

## High-Level Architecture
The system is divided into two primary environments:
1. **The Python Backend (Server & Computer Vision)**
2. **The Unity Frontend (AetherUI Client)**

### 1. Python Backend
The backend is responsible for all heavy lifting regarding hardware interaction, computer vision, and machine learning inference. It operates entirely off-screen to provide a seamless interface.
- **Hardware Capture:** Interfaces with connected webcams using OpenCV to extract raw video frames.
- **Feature Extraction:** Utilizes Google's MediaPipe framework to detect and track 21 discrete hand landmarks in 3D space.
- **Temporal Buffering:** A custom `SequenceBuffer` class stores these landmarks over time, allowing the system to recognize motion over a sequence of frames rather than static poses.
- **Inference & Processing:** Calculates live tracking intensity based on hand proximity and prepares temporal data for the PyTorch gesture classification model.
- **WebSocket Server:** A FastAPI asynchronous server broadcasts JSON payloads containing the recognized `command` and its `intensity` to any connected clients.

### 2. Unity Frontend (AetherUI)
The frontend serves as the visual and interactive layer of the application, rendering the HCI feedback in a 3D space.
- **Networking (`CommandReceiver`):** A NativeWebSocket client that establishes a persistent connection to the Python backend (`ws://localhost:8000/ws`). It handles reconnects, JSON parsing, and background processing.
- **Visual Feedback (`OrbEffects`):** A physical translation layer that maps discrete string commands (e.g., `"swipe_right"`) and float intensities into physical 3D transforms, particle bursts, and HDR emissive material changes.

## Data Flow Diagram
1. User performs a gesture in front of the Webcam.
2. OpenCV captures the frame -> MediaPipe extracts 21x (x,y,z) coordinates.
3. Coordinates are buffered; if the hand is active, "tracking" data is streamed.
4. If a gesture completes (hand goes idle), the sequence is passed to the ML Model (currently mocked).
5. FastApi broadcasts: `{"command": "swipe_left", "intensity": 2.5}`.
6. Unity `CommandReceiver` catches the JSON and routes it to `OrbEffects`.
7. `OrbEffects` translates the gesture into localized 3D spatial movement and dynamic VFX.
