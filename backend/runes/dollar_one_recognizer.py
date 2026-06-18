"""
dollar_one_recognizer.py
------------------------
$1 (Dollar One) gesture recognizer implementation for 2D stroke/rune recognition.
Provides deterministic, fast recognition on CPU.
"""

import math
import numpy as np

class DollarOneRecognizer:
    """
    Implements the $1 gesture recognizer for 2D curves.
    """

    def __init__(self, num_points: int = 64, square_size: float = 250.0) -> None:
        self.num_points = num_points
        self.square_size = square_size
        self.templates = {}
        
        # Load synthetic templates
        self._initialize_templates()

    def _initialize_templates(self):
        """
        Generate synthetic templates for circle, triangle, star, square, spiral, and Z-seal.
        """
        # 1. Circle template
        circle_pts = []
        for i in range(self.num_points):
            angle = 2.0 * math.pi * i / (self.num_points - 1)
            circle_pts.append((math.cos(angle), math.sin(angle)))
        self.add_template("circle", circle_pts)

        # 2. Triangle template
        triangle_pts = []
        # Draw from top (0, 1) -> bottom right (0.86, -0.5) -> bottom left (-0.86, -0.5) -> top (0, 1)
        p1, p2, p3 = (0.0, 1.0), (0.86, -0.5), (-0.86, -0.5)
        # Interpolate points along three sides
        n_side = self.num_points // 3
        for i in range(n_side):
            t = i / n_side
            triangle_pts.append((p1[0]*(1-t) + p2[0]*t, p1[1]*(1-t) + p2[1]*t))
        for i in range(n_side):
            t = i / n_side
            triangle_pts.append((p2[0]*(1-t) + p3[0]*t, p2[1]*(1-t) + p3[1]*t))
        for i in range(self.num_points - len(triangle_pts)):
            t = i / (self.num_points - len(triangle_pts) - 1) if (self.num_points - len(triangle_pts) - 1) > 0 else 0
            triangle_pts.append((p3[0]*(1-t) + p1[0]*t, p3[1]*(1-t) + p1[1]*t))
        self.add_template("triangle", triangle_pts)

        # 3. Square template
        square_pts = []
        p_sq = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        n_side = self.num_points // 4
        for s in range(4):
            sp, ep = p_sq[s], p_sq[s+1]
            for i in range(n_side):
                t = i / n_side
                square_pts.append((sp[0]*(1-t) + ep[0]*t, sp[1]*(1-t) + ep[1]*t))
        while len(square_pts) < self.num_points:
            square_pts.append(p_sq[-1])
        self.add_template("square", square_pts)

        # 4. Star template (5-pointed)
        star_pts = []
        # Star vertices in drawing order
        vertices = []
        for i in range(5):
            angle = -math.pi/2.0 + i * 2.0 * math.pi * 2.0 / 5.0
            vertices.append((math.cos(angle), math.sin(angle)))
        vertices.append(vertices[0]) # close star
        
        n_segment = self.num_points // 5
        for s in range(5):
            sp, ep = vertices[s], vertices[s+1]
            for i in range(n_segment):
                t = i / n_segment
                star_pts.append((sp[0]*(1-t) + ep[0]*t, sp[1]*(1-t) + ep[1]*t))
        while len(star_pts) < self.num_points:
            star_pts.append(vertices[-1])
        self.add_template("star", star_pts)

        # 5. Spiral template
        spiral_pts = []
        for i in range(self.num_points):
            theta = 3.0 * math.pi * i / (self.num_points - 1)
            r = 1.0 - 0.7 * (i / (self.num_points - 1))
            spiral_pts.append((r * math.cos(theta), r * math.sin(theta)))
        self.add_template("spiral", spiral_pts)

        # 6. Z-seal (Z-shape mudra)
        z_pts = []
        pz = [(-1.0, 1.0), (1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]
        n_seg = self.num_points // 3
        for s in range(3):
            sp, ep = pz[s], pz[s+1]
            for i in range(n_seg):
                t = i / n_seg
                z_pts.append((sp[0]*(1-t) + ep[0]*t, sp[1]*(1-t) + ep[1]*t))
        while len(z_pts) < self.num_points:
            z_pts.append(pz[-1])
        self.add_template("z_seal", z_pts)

    def add_template(self, name: str, points: list[tuple[float, float]]):
        """
        Processes and adds a template.
        """
        processed = self._prepare_path(points)
        self.templates[name] = processed

    def _path_length(self, points: list[tuple[float, float]]) -> float:
        """
        Total length of the path.
        """
        d = 0.0
        for i in range(1, len(points)):
            d += math.hypot(points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
        return d

    def _resample(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """
        Resamples path to have exactly N equidistant points.
        """
        if not points:
            return [(0.0, 0.0)] * self.num_points
        if len(points) == 1:
            return [points[0]] * self.num_points

        I = self._path_length(points) / (self.num_points - 1)
        if I <= 0:
            return [points[0]] * self.num_points

        new_points = [points[0]]
        D = 0.0
        i = 1
        
        # Clone points to avoid modification issues
        pts = list(points)
        
        while i < len(pts):
            d = math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1])
            if (D + d) >= I:
                # Interpolate
                qx = pts[i-1][0] + ((I - D) / d) * (pts[i][0] - pts[i-1][0])
                qy = pts[i-1][1] + ((I - D) / d) * (pts[i][1] - pts[i-1][1])
                new_points.append((qx, qy))
                pts.insert(i, (qx, qy)) # insert the interpolated point
                D = 0.0
            else:
                D += d
            i += 1

        # Handle rounding errors
        while len(new_points) < self.num_points:
            new_points.append(pts[-1])
        return new_points[:self.num_points]

    def _centroid(self, points: list[tuple[float, float]]) -> tuple[float, float]:
        """
        Calculates centroid of the path.
        """
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return float(np.mean(xs)), float(np.mean(ys))

    def _rotate_by(self, points: list[tuple[float, float]], angle: float) -> list[tuple[float, float]]:
        """
        Rotates points by a given angle around centroid.
        """
        c = self._centroid(points)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_pts = []
        for p in points:
            dx = p[0] - c[0]
            dy = p[1] - c[1]
            rx = dx * cos_a - dy * sin_a + c[0]
            ry = dx * sin_a + dy * cos_a + c[1]
            new_pts.append((rx, ry))
        return new_pts

    def _scale_to(self, points: list[tuple[float, float]], size: float) -> list[tuple[float, float]]:
        """
        Scales path non-uniformly to a square bounding box of given size.
        """
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x
        h = max_y - min_y
        
        # Avoid division by zero
        if w == 0: w = 1e-5
        if h == 0: h = 1e-5

        new_pts = []
        for p in points:
            sx = (p[0] - min_x) * (size / w)
            sy = (p[1] - min_y) * (size / h)
            new_pts.append((sx, sy))
        return new_pts

    def _translate_to(self, points: list[tuple[float, float]], target: tuple[float, float]) -> list[tuple[float, float]]:
        """
        Translates path so its centroid is at target.
        """
        c = self._centroid(points)
        new_pts = []
        for p in points:
            new_pts.append((p[0] - c[0] + target[0], p[1] - c[1] + target[1]))
        return new_pts

    def _prepare_path(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """
        Resamples, rotates to zero, scales, and translates to origin.
        """
        # Step 1: Resample
        resampled = self._resample(points)
        # Step 2: Rotate to 0
        c = self._centroid(resampled)
        angle = math.atan2(resampled[0][1] - c[1], resampled[0][0] - c[0])
        rotated = self._rotate_by(resampled, -angle)
        # Step 3: Scale
        scaled = self._scale_to(rotated, self.square_size)
        # Step 4: Translate
        translated = self._translate_to(scaled, (0, 0))
        return translated

    def _distance_at_best_angle(self, points: list[tuple[float, float]], template: list[tuple[float, float]]) -> float:
        """
        Calculates minimum matching distance at best rotated angle.
        """
        # To simplify, we calculate the distance at 0 rotation, as prepare_path
        # already rotated both candidate and template to their 0 angles.
        d = 0.0
        for p_cand, p_temp in zip(points, template):
            d += math.hypot(p_cand[0] - p_temp[0], p_cand[1] - p_temp[1])
        return d / self.num_points

    def recognize(self, points: list[tuple[float, float]]) -> dict:
        """
        Matches a gesture path against loaded templates.

        Args:
            points: List of 2D coordinates representing the stroke.

        Returns:
            dict: {"rune": str, "confidence": float}
        """
        if len(points) < 8:
            return {"rune": "unknown", "confidence": 0.0}

        try:
            cand = self._prepare_path(points)
            best_name = "unknown"
            min_dist = float("inf")

            for name, temp in self.templates.items():
                d = self._distance_at_best_angle(cand, temp)
                if d < min_dist:
                    min_dist = d
                    best_name = name

            # Calculate confidence score based on square size bounding box
            # Max possible distance is the diagonal of the square: square_size * sqrt(2)
            half_diag = 0.5 * self.square_size * math.sqrt(2.0)
            confidence = 1.0 - (min_dist / half_diag)
            confidence = max(0.0, min(confidence, 1.0))

            # Map templates to canonical spells
            rune_map = {
                "circle": "FIRE_CIRCLE",
                "triangle": "TRIANGLE",
                "star": "STAR",
                "square": "SQUARE",
                "spiral": "SPIRAL",
                "z_seal": "Z_SEAL"
            }
            rune_name = rune_map.get(best_name, "unknown")

            return {"rune": rune_name, "confidence": round(confidence, 4)}
        except Exception as e:
            print(f"[DollarOne] Recognition error: {e}")
            return {"rune": "unknown", "confidence": 0.0}

if __name__ == "__main__":
    rec = DollarOneRecognizer()
    # Mock circular stroke
    mock_stroke = []
    for i in range(40):
        angle = 2.0 * math.pi * i / 39
        mock_stroke.append((math.cos(angle) * 100 + 300, math.sin(angle) * 100 + 300))
        
    print(rec.recognize(mock_stroke))
