"""
camera.py
---------
A clean wrapper for OpenCV's VideoCapture to manage camera access.
This module is strictly for hardware interaction and does not include
any processing or gesture logic.
"""

import cv2
import numpy as np

class CameraManager:
    """
    Manages the initialization, frame reading, and release of the webcam.
    """

    def __init__(self, camera_index: int = 0) -> None:
        """
        Initialize the camera Capture object.

        Args:
            camera_index (int): The system index of the camera (default is 0).
        """
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            print(f"[ERROR] Camera index {self.camera_index} could not be opened.")

    def read(self) -> tuple[bool, np.ndarray | None]:
        """
        Capture a single frame from the camera.

        Returns:
            tuple: (success, frame) 
                   - success (bool): True if the frame was read correctly.
                   - frame (np.ndarray): The captured image frame (BGR format).
        """
        if not self.cap.isOpened():
            return False, None
            
        success, frame = self.cap.read()
        return success, frame

    def release(self) -> None:
        """
        Release the camera hardware so other applications can use it.
        """
        if self.cap.isOpened():
            self.cap.release()
            print(f"[INFO] Camera {self.camera_index} released.")

# ---------------------------------------------------------------------------
# Simple Test Block
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== CameraManager Test ===")
    print("Press 'q' to quit the preview window.\n")

    # Create a CameraManager instance
    cam = CameraManager(camera_index=0)

    try:
        while True:
            # Read a frame
            success, frame = cam.read()

            if not success:
                print("[ERROR] Failed to read frame.")
                break

            # Show the frame in a window
            cv2.imshow("CameraManager Test Preview", frame)

            # Exit loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] 'q' pressed. Quitting...")
                break
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
    finally:
        cam.release()
        cv2.destroyAllWindows()
