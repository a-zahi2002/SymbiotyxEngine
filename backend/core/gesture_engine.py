"""
gesture_engine.py
-----------------
Core logic for analyzing hand landmarks and identifying simple gestures.
This module uses geometric rules based on relative landmark positions.
"""

class GestureEngine:
    """
    Analyzes hand landmarks provided by MediaPipe to detect finger states 
    and classify basic gestures.
    """

    def __init__(self) -> None:
        """
        Initializes the GestureEngine.
        """
        # Mapping finger names to their tip and PIP (Proximal Interphalangeal joint) landmark IDs
        # MediaPipe Landmark IDs:
        # Thumb: Tip 4, IP 3
        # Index: Tip 8, PIP 6
        # Middle: Tip 12, PIP 10
        # Ring: Tip 16, PIP 14
        # Pinky: Tip 20, PIP 18
        self.finger_map = {
            "thumb": (4, 3),
            "index": (8, 6),
            "middle": (12, 10),
            "ring": (16, 14),
            "pinky": (20, 18)
        }

    def analyze(self, landmarks: list) -> dict:
        """
        Processes a list of landmarks to determine which fingers are extended.

        Rule: A finger is considered 'up' if the Y-coordinate of its tip 
        is less than the Y-coordinate of its PIP joint (since Y=0 is the top).

        Args:
            landmarks (list): A list of dictionaries, each containing 'id', 'x', 'y', 'z'.

        Returns:
            dict: Finger states and the identified gesture name.
        """
        if not landmarks:
            return {
                "thumb": False, "index": False, "middle": False, 
                "ring": False, "pinky": False, "gesture": "UNKNOWN"
            }

        # Convert landmarks list to a dictionary for faster lookup by ID
        lm_dict = {lm['id']: lm for lm in landmarks}
        
        results = {}
        fingers_up_count = 0
        
        # Check each finger state
        for finger, (tip_id, pip_id) in self.finger_map.items():
            if tip_id in lm_dict and pip_id in lm_dict:
                # In MediaPipe, Y decreases as you go up the screen
                is_up = lm_dict[tip_id]['y'] < lm_dict[pip_id]['y']
                results[finger] = is_up
                if is_up:
                    fingers_up_count += 1
            else:
                results[finger] = False

        # Gesture Classification Logic
        gesture = "UNKNOWN"
        
        # All 5 fingers up
        if fingers_up_count == 5:
            gesture = "OPEN_PALM"
            
        # No fingers up
        elif fingers_up_count == 0:
            gesture = "FIST"
            
        # Only index finger up
        elif fingers_up_count == 1 and results["index"]:
            gesture = "POINTING"

        results["gesture"] = gesture
        return results

if __name__ == "__main__":
    # Small test block to verify logic
    engine = GestureEngine()
    
    # Mock landmarks for an OPEN_PALM (all tips have smaller Y than PIPs)
    mock_landmarks = [
        {"id": 4, "x": 0.1, "y": 0.1, "z": 0}, {"id": 3, "x": 0.1, "y": 0.2, "z": 0},   # Thumb
        {"id": 8, "x": 0.2, "y": 0.1, "z": 0}, {"id": 6, "x": 0.2, "y": 0.2, "z": 0},   # Index
        {"id": 12, "x": 0.3, "y": 0.1, "z": 0}, {"id": 10, "x": 0.3, "y": 0.2, "z": 0}, # Middle
        {"id": 16, "x": 0.4, "y": 0.1, "z": 0}, {"id": 14, "x": 0.4, "y": 0.2, "z": 0}, # Ring
        {"id": 20, "x": 0.5, "y": 0.1, "z": 0}, {"id": 18, "x": 0.5, "y": 0.2, "z": 0}  # Pinky
    ]
    
    print("Testing OPEN_PALM mock data...")
    print(engine.analyze(mock_landmarks))
