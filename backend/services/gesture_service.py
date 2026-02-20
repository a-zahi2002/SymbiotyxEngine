"""
gesture_service.py
------------------
A service to map sequences of gestures to specific application commands.
It handles pattern matching and calculates the 'intensity' of the gesture
based on the movement speed.
"""

import json
import os
import sys

# Add project root to path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import backend.intensity.intensity_analysis as intensity

class GestureService:
    """
    Manages gesture rules and interprets frame sequences into commands.
    """

    def __init__(self, rules_path: str = None) -> None:
        """
        Initializes the GestureService with optional pre-defined rules.

        Args:
            rules_path (str): Path to a JSON file containing gesture-to-command mappings.
                             Format: {"gesture1,gesture2": "command_name"}
        """
        self.rules = {}
        if rules_path and os.path.exists(rules_path):
            self.load_rules(rules_path)

    def load_rules(self, file_path: str) -> None:
        """
        Loads gesture rules from a JSON file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
            print(f"[INFO] Loaded {len(self.rules)} rules from {file_path}")
        except Exception as e:
            print(f"[ERROR] Could not load rules from {file_path}: {e}")

    def add_rule(self, sequence_pattern: str, command_name: str) -> None:
        """
        Adds a new gesture rule to the service at runtime.

        Args:
            sequence_pattern (str): Comma-separated names, e.g., "FIST,OPEN_PALM"
            command_name (str): The command to trigger, e.g., "maximize_window"
        """
        # Normalize: strip whitespace and ensure comma consistency
        normalized_pattern = ",".join([p.strip().upper() for p in sequence_pattern.split(",")])
        self.rules[normalized_pattern] = command_name
        print(f"[INFO] Added rule: {normalized_pattern} -> {command_name}")

    def _extract_gesture_pattern(self, frames: list[dict]) -> str:
        """
        Helper to extract a unique pattern string from a list of frames.
        
        Example: [FIST, FIST, OPEN, OPEN] -> "FIST,OPEN"
        """
        pattern_list = []
        for frame in frames:
            gesture = frame.get("gesture", "UNKNOWN")
            # Only add to pattern if it's different from the last one (detecting transitions)
            if not pattern_list or gesture != pattern_list[-1]:
                pattern_list.append(gesture)
        
        return ",".join(pattern_list)

    def parse_sequence(self, sequence: list[dict]) -> dict | None:
        """
        Analyzes a sequence of frames and returns a matching command and its intensity.

        Args:
            sequence (list): A list of frame dictionaries (as stored in SequenceBuffer).

        Returns:
            dict: { "command": str, "intensity": float } or None if no match is found.
        """
        if not sequence:
            return None

        # 1. Identify the pattern of gesture transitions
        pattern = self._extract_gesture_pattern(sequence)
        
        # 2. Look up the command in the rules
        command = self.rules.get(pattern)
        
        if not command:
            return None

        # 3. Compute intensity based on average velocity
        avg_velocity = intensity.compute_average_velocity(sequence)

        return {
            "command": command,
            "intensity": round(avg_velocity, 4)
        }

if __name__ == "__main__":
    print("=== GestureService Test ===\n")

    # 1. Initialize Service
    service = GestureService()

    # 2. Add Rules
    service.add_rule("FIST,OPEN_PALM", "unlock_door")
    service.add_rule("OPEN_PALM,POINTING", "next_slide")

    # 3. Create mock sequence (FIST slowly transitioning to OPEN_PALM)
    mock_sequence = [
        {"timestamp": 0.0, "gesture": "FIST", "landmarks": [{"id": 0, "x": 0.1, "y": 0.1, "z": 0}]},
        {"timestamp": 0.1, "gesture": "FIST", "landmarks": [{"id": 0, "x": 0.11, "y": 0.1, "z": 0}]},
        {"timestamp": 0.2, "gesture": "OPEN_PALM", "landmarks": [{"id": 0, "x": 0.2, "y": 0.1, "z": 0}]},
        {"timestamp": 0.3, "gesture": "OPEN_PALM", "landmarks": [{"id": 0, "x": 0.3, "y": 0.1, "z": 0}]}
    ]

    # 4. Parse the sequence
    result = service.parse_sequence(mock_sequence)

    if result:
        print(f"\nMatch Found!")
        print(f"  Command:   {result['command']}")
        print(f"  Intensity: {result['intensity']}")
    else:
        print("\nNo matching gesture sequence found.")
