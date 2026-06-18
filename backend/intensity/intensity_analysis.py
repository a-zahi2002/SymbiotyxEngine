import math

def compute_distance(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> float:
    """
    Compute the Euclidean distance between two 3D points.

    Args:
        p1 (tuple): (x, y, z) coordinates of the first point.
        p2 (tuple): (x, y, z) coordinates of the second point.

    Returns:
        float: The straight-line distance between the points.
    """
    return math.sqrt(
        (p2[0] - p1[0])**2 +
        (p2[1] - p1[1])**2 +
        (p2[2] - p1[2])**2
    )

def compute_frame_velocity(prev_frame: dict, current_frame: dict) -> float:
    """
    Compute the velocity of the wrist landmark between two frames.

    Velocity = Distance / Time Difference.

    Args:
        prev_frame (dict): The previous frame dictionary.
        current_frame (dict): The current frame dictionary.

    Returns:
        float: Calculated velocity. Returns 0.0 if time difference is zero or data is missing.
    """
    # Extract timestamps
    t_prev = prev_frame.get("timestamp", 0)
    t_curr = current_frame.get("timestamp", 0)
    
    dt = t_curr - t_prev
    if dt <= 0:
        return 0.0

    # Helper to find the wrist (landmark 0)
    def get_wrist_coords(frame: dict) -> tuple[float, float, float] | None:
        landmarks = frame.get("landmarks", [])
        for lm in landmarks:
            if lm.get("id") == 0:
                return (lm["x"], lm["y"], lm["z"])
        return None

    p1 = get_wrist_coords(prev_frame)
    p2 = get_wrist_coords(current_frame)

    if p1 is None or p2 is None:
        return 0.0

    distance = compute_distance(p1, p2)
    return distance / dt

def compute_average_velocity(sequence: list[dict]) -> float:
    """
    Compute the average velocity across an entire sequence of frames.

    Args:
        sequence (list): A list of frame dictionaries.

    Returns:
        float: The mean velocity. Returns 0.0 if the sequence has fewer than 2 frames.
    """
    if len(sequence) < 2:
        return 0.0

    total_velocity = 0.0
    count = 0

    # Iterate through pairs of consecutive frames
    for i in range(len(sequence) - 1):
        v = compute_frame_velocity(sequence[i], sequence[i+1])
        total_velocity += v
        count += 1

    return total_velocity / count if count > 0 else 0.0

if __name__ == "__main__":
    print("=== Intensity Analysis Test ===\n")

    # Mock data: A simple movement along the X-axis
    # Frame 1: at t=0.0, wrist at (0, 0, 0)
    frame1 = {
        "timestamp": 0.0,
        "hand": "right",
        "landmarks": [{"id": 0, "x": 0.0, "y": 0.0, "z": 0.0}]
    }
    
    # Frame 2: at t=0.1, wrist at (0.1, 0, 0) -> Velocity = 0.1 / 0.1 = 1.0
    frame2 = {
        "timestamp": 0.1,
        "hand": "right",
        "landmarks": [{"id": 0, "x": 0.1, "y": 0.0, "z": 0.0}]
    }

    # Frame 3: at t=0.2, wrist at (0.3, 0, 0) -> Velocity = 0.2 / 0.1 = 2.0
    frame3 = {
        "timestamp": 0.2,
        "hand": "right",
        "landmarks": [{"id": 0, "x": 0.3, "y": 0.0, "z": 0.0}]
    }

    test_sequence = [frame1, frame2, frame3]
    
    avg_v = compute_average_velocity(test_sequence)
    print(f"Sequence Length: {len(test_sequence)} frames")
    print(f"Average Velocity: {avg_v:.4f} units/sec")
    
    # Expected: (1.0 + 2.0) / 2 = 1.5
    print("\nTest finished.")

def map_intensity_to_effects(intensity: float, spell_type: str) -> dict:
    """
    Maps a raw intensity float to spell-specific parameters (power, particle count,
    animation speed, and explosion radius).

    Args:
        intensity (float): Raw movement intensity/velocity multiplier.
        spell_type (str): The name of the spell.

    Returns:
        dict: Spell effect parameters.
    """
    # Clamp intensity for safety
    clamped = max(0.5, min(intensity, 5.0))
    
    # Base mapping
    power = clamped * 1.5
    particles = int(clamped * 30)
    anim_speed = 0.5 + (clamped * 0.5)
    radius = 1.0 + (clamped * 0.8)

    # Spell-specific customizations
    if spell_type == "FIREBALL":
        particles = int(clamped * 50)  # Fireballs have lots of sparks
    elif spell_type == "SHIELD":
        radius = 1.5 + (clamped * 0.5)  # Shields grow wider
        particles = int(clamped * 20)
    elif spell_type == "LIGHTNING":
        anim_speed = 1.0 + (clamped * 1.0)  # Lightning is extremely fast
    elif spell_type == "DRAGON_SUMMON":
        power = clamped * 2.5
        radius = 2.0 + (clamped * 1.0)  # Giant dragons

    return {
        "spell_power": round(power, 2),
        "particle_count": particles,
        "animation_speed": round(anim_speed, 2),
        "explosion_radius": round(radius, 2)
    }

