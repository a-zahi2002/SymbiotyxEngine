# WebSocket & Networking Integration

## Overview
Low-latency communication is vital for an HCI system. The Symbiotix Engine utilizes WebSockets to achieve full-duplex, real-time communication between the Python AI backend and the Unity 3D frontend.

## Python Backend (FastAPI + Uvicorn)
The server architecture is built on `FastAPI` and served via `Uvicorn`, providing native asynchronous support. 

### Connection Manager
The `ConnectionManager` class tracks all active connections. This allows the system to theoretically support multiple simultaneous Unity clients or supplementary dashboards connecting to the same AI backend.
- `connect(websocket)`: Registers a new client on handshake.
- `broadcast(data)`: Iterates through active clients to send a JSON payload. Silently purges dead connections.

### Thread Synchronization
The FastAPI event loop (`asyncio`) cannot be halted. However, the OpenCV camera loop is synchronous and blocking.
- To bridge this, the inference worker runs in a separate thread.
- When an inference is made, the thread safely passes the broadcast back into the main async loop using `asyncio.run_coroutine_threadsafe(send_gesture_command(...), loop)`.

### Payload Structure
All communication is standardized into a simple JSON schema for fast serialization/deserialization:
```json
{
  "command": "swipe_right",
  "intensity": 3.0
}
```

## Unity Frontend (NativeWebSocket)
The C# client uses the `NativeWebSocket` package to connect to the backend.

### CommandReceiver.cs
This script acts as the "ears" of the 3D application.
- **Connection Resiliency:** If the Python server shuts down or takes too long to boot, the `CommandReceiver` catches the `OnError` and `OnClose` events, waiting a specified `reconnectDelay` before automatically trying again.
- **Asynchronous Safety:** Unity's API is not thread-safe and heavily restricts what can happen outside the main thread. C# Tasks and Coroutines safely dispatch incoming network messages back onto Unity's main thread via `DispatchMessageQueue()` in `.Update()`.
- **Background Execution:** By default, Unity freezes its networking when the window loses focus. The system enforces `Application.runInBackground = true` on Awake, ensuring continuous data polling even while the user is interacting with the Python webcam terminal.
