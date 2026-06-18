"""
dynamic_gesture_engine.py
-------------------------
Hybrid Dynamic Gesture Engine fusing rule-based motion analysis with LSTM classification.
"""

import math
import numpy as np
import torch
import traceback
import os

from backend.models.gesture_classifier import load_model
from backend.models.train_gesture_model import process_sequence

class HybridDynamicGestureEngine:
    """
    Fuses deterministic trajectory-based rules with LSTM classification for dynamic gestures.
    """

    def __init__(self, model_path: str = None) -> None:
        self.model = None
        self.class_map = {}
        
        # Try to load LSTM model
        try:
            self.model, self.class_map = load_model(model_path)
            self.model.eval()
            print(f"[DynamicEngine] Successfully loaded LSTM model with classes: {self.class_map}")
        except Exception as e:
            print(f"[DynamicEngine] LSTM Model not loaded ({e}). Using rule-based fallback.")

    def _get_abs_landmark(self, frame: dict, lm_id: int) -> dict | None:
        """
        Reconstruct absolute landmark coordinates from frame data.
        """
        landmarks = {lm["id"]: lm for lm in frame.get("landmarks", [])}
        if lm_id not in landmarks:
            return None
            
        lm = landmarks[lm_id]
        if "wrist_absolute" in frame:
            w = frame["wrist_absolute"]
            return {
                "x": lm["x"] + w["x"],
                "y": lm["y"] + w["y"],
                "z": lm["z"] + w["z"]
            }
        return lm

    def _analyze_trajectory(self, sequence: list[dict]) -> dict:
        """
        Rule-based trajectory analysis for swipes, slashes, zooms, rotations, circles, and spirals.
        """
        if len(sequence) < 5:
            return {"motion": "unknown", "confidence": 0.0}

        # 1. Extract timestamps and positions
        times = [f.get("timestamp", 0) for f in sequence]
        dt = times[-1] - times[0]
        if dt <= 0:
            dt = 0.03 * len(sequence)

        # Retrieve index tip (8) and wrist (0) trajectories
        wrist_pts = []
        index_pts = []
        scales = []
        angles = []

        for f in sequence:
            w = self._get_abs_landmark(f, 0)
            idx = self._get_abs_landmark(f, 8)
            mcp = self._get_abs_landmark(f, 9)

            if w and idx:
                wrist_pts.append(w)
                index_pts.append(idx)
                
                # Hand scale (distance from wrist to index tip, or wrist to middle MCP)
                if mcp:
                    scales.append(math.sqrt((mcp["x"] - w["x"])**2 + (mcp["y"] - w["y"])**2))
                else:
                    scales.append(math.sqrt((idx["x"] - w["x"])**2 + (idx["y"] - w["y"])**2))

                # Angle of the hand relative to vertical axis
                dx_hand = idx["x"] - w["x"]
                dy_hand = idx["y"] - w["y"]
                angles.append(math.atan2(dy_hand, dx_hand))

        if len(wrist_pts) < 5:
            return {"motion": "unknown", "confidence": 0.0}

        # Calculate translation vectors
        x_start, y_start = wrist_pts[0]["x"], wrist_pts[0]["y"]
        x_end, y_end = wrist_pts[-1]["x"], wrist_pts[-1]["y"]

        dx = x_end - x_start
        dy = y_end - y_start

        vx = dx / dt
        vy = dy / dt
        speed = math.sqrt(vx**2 + vy**2)

        # Scale changes (zooms)
        scale_ratio = scales[-1] / scales[0] if scales[0] > 0 else 1.0

        # Angle changes (rotations)
        # Unwrap angles to avoid wrapping discontinuities
        unwrapped_angles = np.unwrap(angles)
        d_angle = unwrapped_angles[-1] - unwrapped_angles[0]

        # Analyze index finger path for circles/spirals
        # Center of index tip trajectory
        idx_xs = [p["x"] for p in index_pts]
        idx_ys = [p["y"] for p in index_pts]
        cx, cy = np.mean(idx_xs), np.mean(idx_ys)

        radii = [math.sqrt((p["x"] - cx)**2 + (p["y"] - cy)**2) for p in index_pts]
        avg_radius = np.mean(radii) if radii else 0.0
        
        # Calculate angle of index tip relative to center
        center_angles = [math.atan2(p["y"] - cy, p["x"] - cx) for p in index_pts]
        unwrapped_center_angles = np.unwrap(center_angles)
        total_rotation = abs(unwrapped_center_angles[-1] - unwrapped_center_angles[0])

        # Rule evaluation:
        
        # 1. Slashes (Very high velocity)
        if speed > 2.0:
            if abs(dy) > abs(dx) * 1.2:
                if dy < 0:
                    return {"motion": "slash_up", "confidence": 0.90}
                else:
                    return {"motion": "slash_down", "confidence": 0.90}

        # 2. Circle / Spiral
        if total_rotation > 4.5:  # Close to 3/4 circle or more
            # If radius changes significantly, it is a spiral
            radius_change = radii[-1] / radii[0] if radii[0] > 0 else 1.0
            if radius_change < 0.65 or radius_change > 1.5:
                return {"motion": "spiral_motion", "confidence": 0.85}
            return {"motion": "circle_motion", "confidence": 0.85}

        # 3. Rotations
        if abs(d_angle) > 0.45:
            if d_angle > 0:
                return {"motion": "rotate_cw", "confidence": 0.85}
            else:
                return {"motion": "rotate_ccw", "confidence": 0.85}

        # 4. Zooms
        if scale_ratio > 1.25:
            return {"motion": "zoom_in", "confidence": 0.80}
        elif scale_ratio < 0.75:
            return {"motion": "zoom_out", "confidence": 0.80}

        # 5. Swipes (Linear motion at normal speed)
        if abs(dx) > 0.12 or abs(dy) > 0.12:
            if abs(dx) > abs(dy) * 1.3:
                if dx < 0:
                    return {"motion": "swipe_left", "confidence": 0.85}
                else:
                    return {"motion": "swipe_right", "confidence": 0.85}
            elif abs(dy) > abs(dx) * 1.3:
                if dy < 0:
                    return {"motion": "swipe_up", "confidence": 0.85}
                else:
                    return {"motion": "swipe_down", "confidence": 0.85}

        return {"motion": "unknown", "confidence": 0.0}

    def recognize(self, sequence: list[dict]) -> dict:
        """
        Fuses predictions from trajectory-based rules and the LSTM neural network.
        """
        # 1. Run rule-based recognition first
        rule_res = self._analyze_trajectory(sequence)
        
        # 2. If rules are confident, or if LSTM is not loaded, return rule result
        if rule_res["confidence"] >= 0.80 or self.model is None:
            return rule_res

        # 3. Run LSTM model
        try:
            features = process_sequence(sequence)
            input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                preds = self.model(input_tensor)
                confidence = torch.max(torch.nn.functional.softmax(preds, dim=1)).item()
                pred_class = torch.argmax(preds, dim=1).item()
                lstm_gesture = self.class_map.get(pred_class, "unknown")

            # 4. Fusion logic: if LSTM is confident, return it
            if confidence > 0.75 and lstm_gesture != "unknown":
                return {"motion": lstm_gesture, "confidence": confidence}
                
        except Exception as e:
            print(f"[DynamicEngine] LSTM inference failed: {e}")

        # Fallback to rule result
        return rule_res
