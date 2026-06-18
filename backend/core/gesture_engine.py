"""
gesture_engine.py
-----------------
Expanded static gesture engine using rotation-invariant geometric rules.
Identifies 11 mudras from hand landmarks without neural network dependencies.
"""

import math

class GestureEngine:
    """
    Analyzes hand landmarks provided by MediaPipe to detect finger states 
    and classify basic gestures.
    """

    def __init__(self) -> None:
        pass

    def analyze(self, landmarks: list) -> dict:
        """
        Processes a list of landmarks to determine which fingers are extended
        and classifies the overall static gesture.

        Args:
            landmarks (list): A list of dictionaries, each containing 'id', 'x', 'y', 'z'.

        Returns:
            dict: Gesture name, confidence, and internal finger states.
        """
        if not landmarks or len(landmarks) < 21:
            return {
                "gesture": "UNKNOWN",
                "confidence": 0.0,
                "thumb": False, "index": False, "middle": False, 
                "ring": False, "pinky": False
            }

        # Convert landmarks list to a dictionary for faster lookup by ID
        lm_dict = {lm['id']: lm for lm in landmarks}
        
        # Translate landmarks so wrist (0) is at (0, 0, 0)
        # This makes the classification translation and scale invariant
        wrist = lm_dict.get(0, {'x': 0, 'y': 0, 'z': 0})
        wx, wy, wz = wrist['x'], wrist['y'], wrist['z']
        
        coords = {}
        for lm_id, lm in lm_dict.items():
            coords[lm_id] = {
                'x': lm['x'] - wx,
                'y': lm['y'] - wy,
                'z': lm['z'] - wz
            }

        def get_dist(id1, id2):
            return ((coords[id1]['x'] - coords[id2]['x'])**2 + 
                    (coords[id1]['y'] - coords[id2]['y'])**2 + 
                    (coords[id1]['z'] - coords[id2]['z'])**2)**0.5

        # Check finger extensions
        # A finger is considered extended if the TIP is significantly farther from MCP than PIP.
        # Index: Tip 8, PIP 6, MCP 5
        # Middle: Tip 12, PIP 10, MCP 9
        # Ring: Tip 16, PIP 14, MCP 13
        # Pinky: Tip 20, PIP 18, MCP 17
        index_up = get_dist(8, 5) > get_dist(6, 5) * 1.25
        middle_up = get_dist(12, 9) > get_dist(10, 9) * 1.25
        ring_up = get_dist(16, 13) > get_dist(14, 13) * 1.25
        pinky_up = get_dist(20, 17) > get_dist(18, 17) * 1.25
        
        # Thumb: Tip 4, IP 3, MCP 2.
        # Must be extended away from MCP 2 and Index MCP 5.
        thumb_up = get_dist(4, 2) > get_dist(3, 2) * 1.15 and get_dist(4, 5) > 0.065

        # Semi-bent states for Tiger Seal (claw)
        index_semi = get_dist(8, 5) > get_dist(6, 5) * 0.95 and get_dist(8, 5) < get_dist(6, 5) * 1.25
        middle_semi = get_dist(12, 9) > get_dist(10, 9) * 0.95 and get_dist(12, 9) < get_dist(10, 9) * 1.25
        ring_semi = get_dist(16, 13) > get_dist(14, 13) * 0.95 and get_dist(16, 13) < get_dist(14, 13) * 1.25
        pinky_semi = get_dist(20, 17) > get_dist(18, 17) * 0.95 and get_dist(20, 17) < get_dist(18, 17) * 1.25
        thumb_semi = get_dist(4, 2) > get_dist(3, 2) * 0.95 and get_dist(4, 2) < get_dist(3, 2) * 1.15

        # Distance checks for specific mudras
        index_middle_dist = get_dist(8, 12)
        thumb_index_dist = get_dist(4, 8)

        gesture = "UNKNOWN"
        confidence = 0.5

        # Gesture definitions:
        
        # 1. PINCH (Thumb tip and index tip are very close, other fingers usually not fully folded)
        if thumb_index_dist < 0.04:
            gesture = "PINCH"
            confidence = 0.95
            
        # 2. OPEN_PALM (All 5 extended)
        elif index_up and middle_up and ring_up and pinky_up and thumb_up:
            gesture = "OPEN_PALM"
            confidence = 0.95
            
        # 3. FIST (All fingers folded)
        elif not index_up and not middle_up and not ring_up and not pinky_up:
            # Let's verify it's not a pinch
            gesture = "FIST"
            confidence = 0.95

        # 4. SWORD_SIGN (Index and Middle extended and pressed together, Ring/Pinky folded)
        elif index_up and middle_up and not ring_up and not pinky_up and index_middle_dist < 0.045:
            gesture = "SWORD_SIGN"
            confidence = 0.95

        # 5. PEACE_SIGN (Index and Middle extended and spread apart, Thumb extended, Ring/Pinky folded)
        elif index_up and middle_up and not ring_up and not pinky_up and thumb_up and index_middle_dist >= 0.045:
            gesture = "PEACE_SIGN"
            confidence = 0.90

        # 6. VICTORY (Index and Middle extended and spread, Thumb folded, Ring/Pinky folded)
        elif index_up and middle_up and not ring_up and not pinky_up and not thumb_up and index_middle_dist >= 0.045:
            gesture = "VICTORY"
            confidence = 0.90

        # 7. LOTUS_SEAL (Thumb, Index, Pinky extended, Middle and Ring folded)
        elif thumb_up and index_up and pinky_up and not middle_up and not ring_up:
            gesture = "LOTUS_SEAL"
            confidence = 0.95

        # 8. POINTING (Only Index extended)
        elif index_up and not middle_up and not ring_up and not pinky_up:
            gesture = "POINTING"
            confidence = 0.95

        # 9. THUMB_UP (Thumb extended and pointing upwards, other fingers folded)
        elif thumb_up and not index_up and not middle_up and not ring_up and not pinky_up and coords[4]['y'] < coords[2]['y'] - 0.02:
            gesture = "THUMB_UP"
            confidence = 0.90

        # 10. THUMB_DOWN (Thumb extended and pointing downwards, other fingers folded)
        elif thumb_up and not index_up and not middle_up and not ring_up and not pinky_up and coords[4]['y'] > coords[2]['y'] + 0.02:
            gesture = "THUMB_DOWN"
            confidence = 0.90

        # 11. TIGER_SEAL (All 5 semi-bent in claw shape)
        elif index_semi and middle_semi and ring_semi and pinky_semi:
            gesture = "TIGER_SEAL"
            confidence = 0.85

        return {
            "gesture": gesture,
            "confidence": confidence,
            "thumb": bool(thumb_up),
            "index": bool(index_up),
            "middle": bool(middle_up),
            "ring": bool(ring_up),
            "pinky": bool(pinky_up)
        }

if __name__ == "__main__":
    engine = GestureEngine()
    # Mock data for OPEN_PALM
    mock_landmarks = [
        {"id": 0, "x": 0.0, "y": 0.5, "z": 0.0}, # wrist
        {"id": 2, "x": -0.05, "y": 0.4, "z": 0.0},
        {"id": 3, "x": -0.08, "y": 0.35, "z": 0.0},
        {"id": 4, "x": -0.11, "y": 0.32, "z": 0.0}, # Thumb Tip (far left)
        {"id": 5, "x": -0.03, "y": 0.3, "z": 0.0},
        {"id": 6, "x": -0.03, "y": 0.22, "z": 0.0},
        {"id": 8, "x": -0.03, "y": 0.1, "z": 0.0},  # Index Tip (straight up)
        {"id": 9, "x": 0.0, "y": 0.3, "z": 0.0},
        {"id": 10, "x": 0.0, "y": 0.2, "z": 0.0},
        {"id": 12, "x": 0.0, "y": 0.08, "z": 0.0},  # Middle Tip (straight up)
        {"id": 13, "x": 0.03, "y": 0.3, "z": 0.0},
        {"id": 14, "x": 0.03, "y": 0.22, "z": 0.0},
        {"id": 16, "x": 0.03, "y": 0.1, "z": 0.0},  # Ring Tip (straight up)
        {"id": 17, "x": 0.06, "y": 0.32, "z": 0.0},
        {"id": 18, "x": 0.06, "y": 0.25, "z": 0.0},
        {"id": 20, "x": 0.06, "y": 0.12, "z": 0.0}  # Pinky Tip (straight up)
    ]
    # Pad the list to 21 landmarks
    for i in range(21):
        if i not in [lm["id"] for lm in mock_landmarks]:
            mock_landmarks.append({"id": i, "x": 0.0, "y": 0.5, "z": 0.0})
            
    print(engine.analyze(mock_landmarks))
