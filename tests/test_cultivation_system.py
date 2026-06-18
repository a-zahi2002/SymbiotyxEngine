"""
test_cultivation_system.py
--------------------------
Automated test suite to verify the target architecture modules.
"""

import sys
import os
import time
import math

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.filters.one_euro_filter import OneEuroFilter, HandLandmarksFilter
from backend.core.gesture_engine import GestureEngine
from backend.runes.dollar_one_recognizer import DollarOneRecognizer
from backend.dual_hand.dual_hand_engine import DualHandEngine
from backend.combos.combo_engine import ComboEngine
from backend.spells.spell_engine import SpellEngine
from backend.events.event_bus import event_bus

def generate_mock_landmarks(gesture_type: str) -> list[dict]:
    """
    Generates relative mock landmarks for testing.
    """
    # Base wrist at 0
    lms = [{"id": i, "x": 0.0, "y": 0.0, "z": 0.0} for i in range(21)]
    
    # helper to set coordinates
    def set_joint(lm_id, x, y, z):
        lms[lm_id] = {"id": lm_id, "x": x, "y": y, "z": z}
        
    if gesture_type == "OPEN_PALM":
        # All extended (tip far from PIP and MCP)
        # Index
        set_joint(5, 0.0, -0.1, 0.0)
        set_joint(6, 0.0, -0.15, 0.0)
        set_joint(8, 0.0, -0.28, 0.0)
        # Middle
        set_joint(9, 0.02, -0.1, 0.0)
        set_joint(10, 0.02, -0.16, 0.0)
        set_joint(12, 0.02, -0.29, 0.0)
        # Ring
        set_joint(13, 0.04, -0.1, 0.0)
        set_joint(14, 0.04, -0.15, 0.0)
        set_joint(16, 0.04, -0.28, 0.0)
        # Pinky
        set_joint(17, 0.06, -0.1, 0.0)
        set_joint(18, 0.06, -0.14, 0.0)
        set_joint(20, 0.06, -0.25, 0.0)
        # Thumb
        set_joint(2, -0.04, -0.05, 0.0)
        set_joint(3, -0.07, -0.08, 0.0)
        set_joint(4, -0.11, -0.11, 0.0)
        
    elif gesture_type == "FIST":
        # All folded (tip close to MCP/PIP)
        # Index
        set_joint(5, 0.0, -0.1, 0.0)
        set_joint(6, 0.0, -0.15, 0.0)
        set_joint(8, 0.0, -0.09, 0.0)
        # Middle
        set_joint(9, 0.02, -0.1, 0.0)
        set_joint(10, 0.02, -0.15, 0.0)
        set_joint(12, 0.02, -0.09, 0.0)
        # Ring
        set_joint(13, 0.04, -0.1, 0.0)
        set_joint(14, 0.04, -0.15, 0.0)
        set_joint(16, 0.04, -0.09, 0.0)
        # Pinky
        set_joint(17, 0.06, -0.1, 0.0)
        set_joint(18, 0.06, -0.14, 0.0)
        set_joint(20, 0.06, -0.08, 0.0)
        # Thumb
        set_joint(2, -0.03, -0.05, 0.0)
        set_joint(3, -0.04, -0.06, 0.0)
        set_joint(4, -0.04, -0.07, 0.0)

    elif gesture_type == "POINTING":
        # Only index extended
        # Index
        set_joint(5, 0.0, -0.1, 0.0)
        set_joint(6, 0.0, -0.15, 0.0)
        set_joint(8, 0.0, -0.28, 0.0)
        # Others folded (same as FIST)
        set_joint(9, 0.02, -0.1, 0.0)
        set_joint(10, 0.02, -0.15, 0.0)
        set_joint(12, 0.02, -0.09, 0.0)
        set_joint(13, 0.04, -0.1, 0.0)
        set_joint(14, 0.04, -0.15, 0.0)
        set_joint(16, 0.04, -0.09, 0.0)
        set_joint(17, 0.06, -0.1, 0.0)
        set_joint(18, 0.06, -0.14, 0.0)
        set_joint(20, 0.06, -0.08, 0.0)
        # Thumb folded
        set_joint(2, -0.03, -0.05, 0.0)
        set_joint(3, -0.04, -0.06, 0.0)
        set_joint(4, -0.04, -0.07, 0.0)

    elif gesture_type == "SWORD_SIGN":
        # Index and middle extended & close
        set_joint(5, 0.0, -0.1, 0.0)
        set_joint(6, 0.0, -0.15, 0.0)
        set_joint(8, 0.0, -0.28, 0.0)
        set_joint(9, 0.015, -0.1, 0.0)
        set_joint(10, 0.015, -0.15, 0.0)
        set_joint(12, 0.015, -0.29, 0.0) # Index & middle very close
        # Others folded
        set_joint(13, 0.04, -0.1, 0.0)
        set_joint(14, 0.04, -0.15, 0.0)
        set_joint(16, 0.04, -0.09, 0.0)
        set_joint(17, 0.06, -0.1, 0.0)
        set_joint(18, 0.06, -0.14, 0.0)
        set_joint(20, 0.06, -0.08, 0.0)
        set_joint(2, -0.03, -0.05, 0.0)
        set_joint(3, -0.04, -0.06, 0.0)
        set_joint(4, -0.04, -0.07, 0.0)
        
    return lms

def test_one_euro_filter():
    print("[TEST] Running One Euro Filter test...")
    f = OneEuroFilter(t0=0.0, x0=10.0, mincutoff=1.0, beta=0.05, dcutoff=1.0)
    
    # Constant input should stabilize at constant value
    val = 10.0
    for i in range(10):
        val = f(t=i*0.03, x=10.0)
    assert abs(val - 10.0) < 1e-4, f"Stable value failed: {val}"
    
    # Sudden jump should be smoothed
    jump = f(t=0.3, x=20.0)
    assert jump < 20.0, f"Smoothing failed: {jump}"
    print("[TEST] One Euro Filter test PASSED.")

def test_static_gesture_engine():
    print("[TEST] Running Static Gesture Engine test...")
    engine = GestureEngine()
    
    # 1. Test OPEN_PALM
    palm_lms = generate_mock_landmarks("OPEN_PALM")
    res = engine.analyze(palm_lms)
    assert res["gesture"] == "OPEN_PALM", f"Expected OPEN_PALM, got {res['gesture']}"
    
    # 2. Test FIST
    fist_lms = generate_mock_landmarks("FIST")
    res = engine.analyze(fist_lms)
    assert res["gesture"] == "FIST", f"Expected FIST, got {res['gesture']}"
    
    # 3. Test POINTING
    pointing_lms = generate_mock_landmarks("POINTING")
    res = engine.analyze(pointing_lms)
    assert res["gesture"] == "POINTING", f"Expected POINTING, got {res['gesture']}"

    # 4. Test SWORD_SIGN
    sword_lms = generate_mock_landmarks("SWORD_SIGN")
    res = engine.analyze(sword_lms)
    assert res["gesture"] == "SWORD_SIGN", f"Expected SWORD_SIGN, got {res['gesture']}"

    print("[TEST] Static Gesture Engine test PASSED.")

def test_dollar_one_recognizer():
    print("[TEST] Running Dollar One Recognizer test...")
    rec = DollarOneRecognizer()
    
    # Generate a circular path
    circle_pts = []
    for i in range(40):
        angle = 2.0 * math.pi * i / 39
        circle_pts.append((math.cos(angle) * 100 + 200, math.sin(angle) * 100 + 200))
        
    res = rec.recognize(circle_pts)
    assert res["rune"] == "FIRE_CIRCLE", f"Expected FIRE_CIRCLE, got {res['rune']}"
    assert res["confidence"] > 0.8, f"Confidence too low: {res['confidence']}"
    print("[TEST] Dollar One Recognizer test PASSED.")

def test_dual_hand_engine():
    print("[TEST] Running Dual-Hand Engine test...")
    engine = DualHandEngine()
    
    res = engine.analyze("OPEN_PALM", "OPEN_PALM")
    assert res == "BARRIER", f"Expected BARRIER, got {res}"
    
    res = engine.analyze("FIST", "FIST")
    assert res == "EARTHQUAKE", f"Expected EARTHQUAKE, got {res}"

    res = engine.analyze("SWORD_SIGN", "OPEN_PALM")
    assert res == "ENERGY_SLASH", f"Expected ENERGY_SLASH, got {res}"
    print("[TEST] Dual-Hand Engine test PASSED.")

def test_combo_engine():
    print("[TEST] Running Combo Engine test...")
    engine = ComboEngine()
    
    # Feed FIST -> OPEN_PALM -> PINCH
    # We must feed stable gestures
    now = time.time()
    
    # 1. Feed FIST stable
    engine.update("FIST")
    time.sleep(0.15)
    res = engine.update("FIST")
    assert res is None
    
    # 2. Feed OPEN_PALM stable
    engine.update("OPEN_PALM")
    time.sleep(0.15)
    res = engine.update("OPEN_PALM")
    assert res is None

    # 3. Feed PINCH stable
    engine.update("PINCH")
    time.sleep(0.15)
    res = engine.update("PINCH")
    
    # Should trigger FIREBALL combo
    assert res == "FIREBALL", f"Expected FIREBALL combo, got {res}"
    print("[TEST] Combo Engine test PASSED.")

def test_spell_engine_qi_states():
    print("[TEST] Running Spell Engine Qi state machine test...")
    engine = SpellEngine()
    
    # Event tracker
    cast_events = []
    def on_cast(payload):
        cast_events.append(payload)
    event_bus.subscribe("spell_cast", on_cast)

    # Transition IDLE -> PREPARING (FIST gesture detected)
    event_bus.publish("gesture_detected", hand="right", gesture="FIST", confidence=0.95)
    assert engine.state == "PREPARING"
    assert engine.active_spell == "FIREBALL"

    # GATHER_QI by moving hand (intensity changes)
    # Feed some intensity velocity to grow Qi
    for i in range(10):
        event_bus.publish("intensity_changed", velocity=0.8, intensity_val=1.5)
        engine.update()
    assert engine.state == "GATHERING_QI"
    
    # Draw rune to CHARGE the spell
    event_bus.publish("rune_detected", rune="FIRE_CIRCLE", confidence=0.92)
    assert engine.state == "CHARGING"
    assert engine.active_rune == "FIRE_CIRCLE"

    # Release to OPEN_PALM to CAST
    event_bus.publish("gesture_detected", hand="right", gesture="OPEN_PALM", confidence=0.95)
    assert engine.state == "COOLDOWN"
    assert len(cast_events) == 1
    assert cast_events[0]["spell"] == "FIREBALL"
    assert cast_events[0]["rune"] == "FIRE_CIRCLE"
    print("[TEST] Spell Engine Qi state machine test PASSED.")

def run_all_tests():
    print("="*40)
    print("  SymbiotixEngine Cultivation Tests")
    print("="*40)
    try:
        test_one_euro_filter()
        test_static_gesture_engine()
        test_dollar_one_recognizer()
        test_dual_hand_engine()
        test_combo_engine()
        test_spell_engine_qi_states()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
