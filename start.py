"""
start.py
--------
SymbiotixEngine — One-Shot Launcher

Starts the FastAPI WebSocket server on the MAIN THREAD so uvicorn is happy.
The camera + inference loop is launched as a separate console window subprocess
when Unity connects to ws://localhost:8000/ws.

Usage (from project root):
    python start.py

Or to run inference separately without waiting for Unity:
    python backend/server/inference_runner.py
"""

import subprocess
import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 60)
    print("  SymbiotixEngine — Starting Backend Server")
    print("=" * 60)
    print()
    print("  WebSocket endpoint : ws://localhost:8000/ws")
    print("  Status endpoint    : http://localhost:8000/status")
    print()
    print("  1. Start Unity and open MainScene")
    print("  2. Press Play in Unity")
    print("  3. A camera window will open automatically")
    print("  4. Use hand gestures to control the orb!")
    print()
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60)
    print()

    python_exe = sys.executable

    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn",
         "backend.server.websocket_server:app",
         "--host", "0.0.0.0",
         "--port", "8000",
         "--log-level", "info"],
        cwd=PROJECT_ROOT
    )

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[START] Shutting down...")
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[START] Done.")


if __name__ == "__main__":
    main()
