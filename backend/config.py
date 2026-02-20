"""
config.py
---------
Centralized configuration file for the SymbiotixEngine backend.
Contains constants used across the camera, tracking, and processing modules.
"""

# The system index for the webcam (usually 0 for built-in, 1+ for external)
CAMERA_INDEX = 0

# Desired frame resolution for the camera capture
# Note: The actual resolution depends on hardware support
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# The maximum number of hands to detect and track concurrently
MAX_HANDS = 2

# Minimum confidence value ([0.0, 1.0]) for hand detection to be considered successful
MIN_DETECTION_CONFIDENCE = 0.5

# Minimum confidence value ([0.0, 1.0]) for hand tracking to be considered successful
MIN_TRACKING_CONFIDENCE = 0.5
