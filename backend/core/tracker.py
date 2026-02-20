"""
tracker.py
----------
Hand tracking logic using MediaPipe.
Processes raw camera frames to detect and identify hand landmarks.
"""

import cv2
import mediapipe as mp
import numpy as np

class HandTracker:
    """
    Wraps MediaPipe Hands to detect and draw landmarks on hand images.
    """

    def __init__(self, max_hands: int = 2, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5) -> None:
        """
        Initialize MediaPipe Hands.

        Args:
            max_hands (int): Max number of hands to track.
            min_detection_confidence (float): Confidence threshold for hand detection.
            min_tracking_confidence (float): Confidence threshold for tracking movement.
        """
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def process(self, frame: np.ndarray) -> list:
        """
        Process a frame to find hand landmarks.

        Args:
            frame (np.ndarray): The BGR image frame from the camera.

        Returns:
            list: A list of landmarks objects for each detected hand.
        """
        # Convert the BGR image to RGB as required by MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame and find landmarks
        results = self.hands.process(rgb_frame)
        
        # Return the list of multi_hand_landmarks (if any)
        if results.multi_hand_landmarks:
            return results.multi_hand_landmarks
        return []

    def draw_landmarks(self, frame: np.ndarray, landmarks_list: list) -> None:
        """
        Draw detected landmarks and connections on the provided frame.

        Args:
            frame (np.ndarray): The image to draw on.
            landmarks_list (list): The list of landmarks detected by process().
        """
        for hand_landmarks in landmarks_list:
            self.mp_drawing.draw_landmarks(
                frame, 
                hand_landmarks, 
                self.mp_hands.HAND_CONNECTIONS
            )

# ---------------------------------------------------------------------------
# Simple Test Block
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import os
    
    # Add project root to path for local imports if needed
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    
    from backend.core.camera import CameraManager
    
    print("=== HandTracker Test ===")
    print("Press 'q' to quit.\n")

    cam = CameraManager(camera_index=0)
    tracker = HandTracker()

    try:
        while True:
            success, frame = cam.read()
            if not success:
                break

            # Process frame for landmarks
            landmarks = tracker.process(frame)
            
            # Draw landmarks on the frame
            tracker.draw_landmarks(frame, landmarks)

            cv2.imshow("HandTracker Test Preview", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()
