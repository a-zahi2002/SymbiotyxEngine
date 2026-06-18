"""
one_euro_filter.py
------------------
One Euro Filter implementation for smoothing 3D hand tracking landmarks.
This reduces jitter and enhances spell stability.
"""

import math
import time

class LowPassFilter:
    """
    Simple first-order low-pass filter.
    """
    def __init__(self, alpha: float):
        self.alpha = alpha
        self.y = None

    def __call__(self, x: float, alpha: float = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.y is None:
            self.y = x
        else:
            self.y = self.alpha * x + (1.0 - self.alpha) * self.y
        return self.y

class OneEuroFilter:
    """
    One Euro Filter with adaptive cutoff frequency.
    """
    def __init__(self, t0: float, x0: float, mincutoff: float = 1.0, beta: float = 0.005, dcutoff: float = 1.0):
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)
        self.x_filt = LowPassFilter(self._alpha(mincutoff, 1.0))
        self.dx_filt = LowPassFilter(self._alpha(dcutoff, 1.0))
        self.t_prev = float(t0)
        self.x_prev = float(x0)

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, t: float, x: float) -> float:
        t = float(t)
        dt = t - self.t_prev
        if dt <= 0:
            return self.x_prev
        
        # Estimate derivative
        dx = (x - self.x_prev) / dt
        dx_smoothed = self.dx_filt(dx, self._alpha(self.dcutoff, dt))
        
        # Adapt cutoff frequency
        cutoff = self.mincutoff + self.beta * abs(dx_smoothed)
        alpha = self._alpha(cutoff, dt)
        
        # Smooth signal
        x_smoothed = self.x_filt(x, alpha)
        self.t_prev = t
        self.x_prev = x_smoothed
        return x_smoothed

class HandLandmarksFilter:
    """
    Manages OneEuroFilters for 21 landmarks * 3 coordinates (x, y, z).
    """
    def __init__(self, mincutoff: float = 1.0, beta: float = 0.05, dcutoff: float = 1.0):
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.filters = {}  # maps (landmark_id, coord) -> OneEuroFilter

    def filter(self, landmarks: list[dict], timestamp: float) -> list[dict]:
        """
        Smooth a list of 21 landmark dictionaries.
        """
        if not landmarks:
            return []
            
        filtered_landmarks = []
        for lm in landmarks:
            lm_id = lm["id"]
            x, y, z = lm["x"], lm["y"], lm["z"]
            
            key_x = (lm_id, "x")
            key_y = (lm_id, "y")
            key_z = (lm_id, "z")
            
            if key_x not in self.filters:
                self.filters[key_x] = OneEuroFilter(timestamp, x, self.mincutoff, self.beta, self.dcutoff)
                self.filters[key_y] = OneEuroFilter(timestamp, y, self.mincutoff, self.beta, self.dcutoff)
                self.filters[key_z] = OneEuroFilter(timestamp, z, self.mincutoff, self.beta, self.dcutoff)
            
            fx = self.filters[key_x](timestamp, x)
            fy = self.filters[key_y](timestamp, y)
            fz = self.filters[key_z](timestamp, z)
            
            filtered_landmarks.append({
                "id": lm_id,
                "x": round(fx, 6),
                "y": round(fy, 6),
                "z": round(fz, 6)
            })
        return filtered_landmarks
