"""
dual_hand_engine.py
-------------------
Analyzes left and right hand gestures simultaneously.
"""

class DualHandEngine:
    """
    Combines left and right hand gestures to form dual-hand spells.
    """
    def __init__(self) -> None:
        pass

    def analyze(self, left_gesture: str, right_gesture: str) -> str | None:
        """
        Analyze combinations of left and right hand static gestures.
        """
        if not left_gesture or not right_gesture:
            return None

        g1 = left_gesture.upper()
        g2 = right_gesture.upper()

        if g1 == "UNKNOWN" or g2 == "UNKNOWN":
            return None

        # 1. Dual Palm -> BARRIER
        if g1 == "OPEN_PALM" and g2 == "OPEN_PALM":
            return "BARRIER"

        # 2. Dual Fist -> EARTHQUAKE
        elif g1 == "FIST" and g2 == "FIST":
            return "EARTHQUAKE"

        # 3. Sword + Palm -> ENERGY_SLASH
        elif (g1 == "SWORD_SIGN" and g2 == "OPEN_PALM") or (g1 == "OPEN_PALM" and g2 == "SWORD_SIGN"):
            return "ENERGY_SLASH"

        # 4. Circle / Pinch + Palm -> MAGIC_FORMATION
        elif (g1 == "OPEN_PALM" and g2 == "PINCH") or (g1 == "PINCH" and g2 == "OPEN_PALM"):
            return "MAGIC_FORMATION"

        return None
