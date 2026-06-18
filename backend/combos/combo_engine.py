"""
combo_engine.py
---------------
Detects sequences of gestures over time (combos).
"""

import time

class ComboEngine:
    """
    Buffers and parses gesture history to identify spell casting combos.
    """
    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout
        self.history: list[tuple[str, float]] = []  # list of (gesture, timestamp)
        self.last_gesture = "UNKNOWN"
        self.last_change_time = time.time()
        
        # Combo mappings: tuple of gestures -> resulting spell
        self.combos = {
            ("FIST", "OPEN_PALM", "PINCH"): "FIREBALL",
            ("VICTORY", "OPEN_PALM", "VICTORY"): "DRAGON_SUMMON",
            ("POINTING", "FIST", "POINTING"): "LIGHTNING",
            ("LOTUS_SEAL", "TIGER_SEAL"): "HEAL"
        }

    def update(self, current_gesture: str) -> str | None:
        """
        Feeds the current static gesture into the combo state machine.
        Returns the triggered spell name, or None.
        """
        now = time.time()

        # Clean history of old entries
        self.history = [(g, t) for g, t in self.history if now - t <= self.timeout]

        # Check for gesture transition
        if current_gesture != self.last_gesture:
            self.last_gesture = current_gesture
            self.last_change_time = now
            return None

        # Debounce: Gesture must be held stable for at least 0.12 seconds
        if current_gesture != "UNKNOWN":
            if now - self.last_change_time >= 0.12:
                # Add to history if it's different from the last added gesture
                if not self.history or self.history[-1][0] != current_gesture:
                    self.history.append((current_gesture, now))
                    # print(f"[Combo] History updated: {[g for g, t in self.history]}")

        # Match combo suffix
        history_names = [g for g, t in self.history]
        for combo_seq, spell_name in self.combos.items():
            n = len(combo_seq)
            if len(history_names) >= n:
                if tuple(history_names[-n:]) == combo_seq:
                    # Reset history to prevent duplicate triggers
                    self.history.clear()
                    return spell_name

        return None
