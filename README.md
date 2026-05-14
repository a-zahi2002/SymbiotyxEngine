# SymbiotixEngine 🌌

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.9-007ACC?logo=google&logoColor=white)](https://developers.google.com/mediapipe)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Unity](https://img.shields.io/badge/Unity-2022.3+-000000?logo=unity&logoColor=white)](https://unity.com/)

**SymbiotixEngine** is a high-performance, multimodal Human-Computer Interaction (HCI) engine designed to bridge the gap between physical gestures and immersive digital environments. By combining real-time computer vision, LSTM-based sequence classification, and low-latency WebSocket communication, it enables a "symbiotic" experience where digital interfaces react fluidly to human movement.

---

## ✨ Key Features

- 🖐️ **High-Fidelity Hand Tracking**: Powered by MediaPipe for robust 21-landmark 3D hand detection.
- 🧠 **Hybrid Gesture Engine**:
    - **Rule-Based**: Instant geometric analysis for static gestures (Fist, Open Palm, Pointing).
    - **LSTM Neural Network**: Sequence-aware classification for dynamic gestures (Zoom, Swipe, Rotate).
- ⚡ **Intensity Analysis**: Real-time velocity and magnitude computation, allowing for "pressure-sensitive" digital interactions.
- 🌐 **Low-Latency Bridge**: FastAPI-powered WebSocket server for sub-millisecond data broadcast to Unity.
- 🎨 **AetherUI**: A responsive Unity-based visualization layer that reacts to commands and intensity.
- 📊 **Data Collection Pipeline**: Built-in recording tools for capturing, labeling, and augmenting gesture datasets in JSON format.

---

## 🏗️ Architecture

The system follows a decoupled, three-tier architecture:

### 1. The Capture & Perception Layer (`backend/core`)
- **Camera Manager**: Optimized OpenCV-based frame capture with configurable resolution.
- **Hand Tracker**: MediaPipe integration for extracting 3D landmarks.
- **Sequence Buffer**: A temporal sliding window that stores landmark history for dynamic analysis.

### 2. The Intelligence Layer (`backend/models` & `backend/intensity`)
- **Geometric Engine**: Direct mathematical analysis of finger angles and relative positions.
- **LSTM Classifier**: A 2-layer Long Short-Term Memory network trained on normalized gesture sequences (50-frame windows).
- **Intensity Processor**: Computes hand velocity and spatial displacement to map physical "effort" to digital "scale".

### 3. The Communication & Visualization Layer (`backend/server` & `unity/`)
- **FastAPI WebSocket Server**: Manages multi-client connections and broadcasts JSON payloads:
  ```json
  {
    "command": "zoom_in",
    "intensity": 2.45
  }
  ```
- **AetherUI (Unity)**: Consumes commands to drive 3D shaders, physics-based UI elements, and navigation.

---

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.10 - 3.12 |
| **Tracking** | Google MediaPipe |
| **Deep Learning** | PyTorch (LSTM Architecture) |
| **Networking** | FastAPI, Uvicorn, WebSockets |
| **Visualization** | Unity 3D, C#, HLSL Shaders |
| **Data Processing** | NumPy, OpenCV |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Unity 2022.3+
- A webcam

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/a-zahi2002/SymbiotyxEngine.git
cd SymbiotyxEngine

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Engine
To start the real-time inference server and WebSocket bridge:
```bash
python backend/server/websocket_server.py
```

### 3. Unity Integration
1. Open the `unity/AetherUI` project in Unity Hub.
2. Open the `Main` scene.
3. Ensure the `WebSocketClient` component is pointing to `ws://localhost:8000/ws`.
4. Hit **Play**.

---

## 📂 Project Structure

```text
SymbiotixEngine/
├── backend/
│   ├── capture/       # Raw data acquisition and sequence buffering
│   ├── core/          # Hand tracking and geometric gesture logic
│   ├── intensity/     # Velocity and magnitude analysis
│   ├── models/        # PyTorch LSTM architecture and training scripts
│   └── server/        # FastAPI WebSocket implementation
├── data/
│   ├── raw/           # Collected JSON gesture sequences
│   └── processed/     # Normalized datasets for training
├── unity/
│   └── AetherUI/      # Unity project for 3D visualization
├── scripts/           # Automation and utility scripts
└── tests/             # Unit and integration tests
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
