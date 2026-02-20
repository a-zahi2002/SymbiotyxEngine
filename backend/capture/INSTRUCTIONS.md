# Webcam Capture Setup Instructions

## Prerequisites

This project requires specific robust Python versions due to dependency constraints in machine learning libraries (MediaPipe, NumPy).

**Supported Python Versions:** 3.10, 3.11, 3.12 (Recommended: 3.11)
**Unsupported:** Python 3.13, 3.14 (No pre-compiled wheels available yet)

## Critical System Requirement (Windows)

If you see `ImportError: DLL load failed` or `AttributeError: module 'mediapipe' has no attribute 'solutions'`, you are missing the **Visual C++ Redistributable for Visual Studio 2015-2022**.

**Current Status:** Your Python is **64-bit**. You MUST install the **x64** version of the redistributable.

**Download x64 Installer (v14.42+):** [https://aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)
*(Do NOT install x86 unless running 32-bit Python!)*

Restart your computer after installing.

## Setup Steps

1. **Install Python 3.11** from [python.org](https://www.python.org/downloads/windows/).
   - Ensure "Add Python to PATH" is checked during installation.

2. **Install Dependencies (Clean):**
   Open a new terminal and run:
   ```powershell
   # Remove old venv if needed
   if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
   
   # Create new venv with Python 3.11
   py -3.11 -m venv .venv
   
   # Activate and install (uses pinned versions in requirements.txt)
   .venv\Scripts\pip install -r requirements.txt
   ```

3. **Verify Environment:**
   Run the test script to confirm everything loaded correctly.
   ```powershell
   .venv\Scripts\python backend/capture/test_environment.py
   ```
   Expected output: `MediaPipe imported successfully (version 0.10.9)`

4. **Run the Capture Script:**
   ```powershell
   .venv\Scripts\python backend/capture/webcam_capture.py
   ```
