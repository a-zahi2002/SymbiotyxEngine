"""
spell_engine.py
---------------
Cultivation Qi State Machine and Spell Engine.
Listens to event bus signals and resolves active spells and states.
"""

import time
from backend.events.event_bus import event_bus
from backend.spells.spell_registry import (
    SPELLS,
    STATE_IDLE,
    STATE_PREPARING,
    STATE_GATHERING_QI,
    STATE_CHARGING,
    STATE_CASTING,
    STATE_COOLDOWN
)
import backend.intensity.intensity_analysis as intensity_analysis

class SpellEngine:
    """
    State machine that resolves gestures, runes, combos, and dual-hand inputs into spells.
    """
    def __init__(self) -> None:
        self.state = STATE_IDLE
        self.active_spell = None
        self.qi_level = 0.0
        self.active_rune = None
        self.cooldown_ends = {}  # maps spell_name -> end_time
        
        self.current_intensity = 1.0
        self.current_velocity = 0.0
        self.last_update_time = time.time()
        self.state_entered_time = time.time()
        self.last_gesture = "UNKNOWN"
        self.last_dynamic_gesture = "none"

        # Subscribe to event bus signals
        event_bus.subscribe("gesture_detected", self.on_gesture_detected)
        event_bus.subscribe("dynamic_gesture_detected", self.on_dynamic_gesture_detected)
        event_bus.subscribe("rune_detected", self.on_rune_detected)
        event_bus.subscribe("combo_detected", self.on_combo_detected)
        event_bus.subscribe("dual_hand_detected", self.on_dual_hand_detected)
        event_bus.subscribe("intensity_changed", self.on_intensity_changed)

    def change_state(self, new_state: str) -> None:
        """
        Transition to a new state and publish the transition.
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.state_entered_time = time.time()
            # print(f"[SpellEngine] State Transition: {old_state} -> {new_state} (Spell: {self.active_spell}, Qi: {self.qi_level:.1f})")
            
            # Publish event
            event_bus.publish(
                f"spell_{new_state.lower()}",
                spell=self.active_spell,
                state=new_state,
                qi=self.qi_level
            )

    def update(self) -> None:
        """
        Periodic tick to handle cooldown timers and state updates.
        """
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # 1. Handle Cooldown state
        if self.state == STATE_COOLDOWN:
            if self.active_spell and self.active_spell in SPELLS:
                cooldown_dur = SPELLS[self.active_spell]["cooldown"]
                elapsed = now - self.state_entered_time
                if elapsed >= cooldown_dur:
                    # Cooldown complete
                    self.cooldown_ends[self.active_spell] = now
                    self.active_spell = None
                    self.active_rune = None
                    self.qi_level = 0.0
                    self.change_state(STATE_IDLE)
            else:
                self.active_spell = None
                self.active_rune = None
                self.qi_level = 0.0
                self.change_state(STATE_IDLE)

        # 2. Decay Qi level slowly if idle or in preparing
        elif self.state == STATE_PREPARING:
            # If preparing takes too long without movement, reset to IDLE
            if now - self.state_entered_time > 4.0:
                self.active_spell = None
                self.qi_level = 0.0
                self.change_state(STATE_IDLE)
                
        elif self.state == STATE_GATHERING_QI:
            # Decay Qi if there's no movement
            if self.current_velocity < 0.2:
                self.qi_level = max(0.0, self.qi_level - 10.0 * dt)
                if self.qi_level == 0.0 and now - self.state_entered_time > 5.0:
                    self.active_spell = None
                    self.change_state(STATE_IDLE)

    def trigger_cast(self) -> None:
        """
        Execute the active spell cast and enter cooldown.
        """
        if not self.active_spell:
            return

        spell_info = SPELLS[self.active_spell]
        req_qi = spell_info["qi_requirement"]

        # Ensure we have gathered enough Qi or we scale down the spell
        cast_power = self.qi_level / req_qi if req_qi > 0 else 1.0
        cast_power = max(0.5, min(cast_power * self.current_intensity, 5.0))

        # Get visual scaling details
        effect_data = intensity_analysis.map_intensity_to_effects(cast_power, self.active_spell)

        # Publish CAST event
        payload = {
            "spell": self.active_spell,
            "command": spell_info["unity_command"],
            "intensity": round(cast_power, 4),
            "rune": self.active_rune or "NONE",
            "state": STATE_CASTING,
            "effect_details": effect_data,
            "gesture": getattr(self, "last_gesture", "UNKNOWN"),
            "dynamic_gesture": getattr(self, "last_dynamic_gesture", "none"),
            "velocity": round(self.current_velocity, 4),
            "confidence": 0.95
        }
        
        print(f"\n⚡ [SpellEngine] CASTING {self.active_spell}! Power: {cast_power:.2f} | Rune: {payload['rune']}")
        
        event_bus.publish("spell_cast", payload)
        self.change_state(STATE_CASTING)
        
        # Immediately enter Cooldown
        self.change_state(STATE_COOLDOWN)

    # ─────────────────────────── Event Handlers ───────────────────────────

    def on_gesture_detected(self, hand: str, gesture: str, confidence: float) -> None:
        """
        Handle static gesture detection signals.
        """
        if self.state == STATE_COOLDOWN:
            return

        self.last_gesture = gesture

        # 1. Idle -> Preparing transitions based on static mudras
        if self.state == STATE_IDLE:
            if gesture == "FIST":
                self.active_spell = "FIREBALL"
                self.qi_level = 5.0
                self.change_state(STATE_PREPARING)
            elif gesture == "LOTUS_SEAL":
                self.active_spell = "HEAL"
                self.qi_level = 10.0
                self.change_state(STATE_PREPARING)
            elif gesture == "SWORD_SIGN":
                self.active_spell = "ENERGY_SLASH"
                self.qi_level = 5.0
                self.change_state(STATE_PREPARING)
                
        # 2. Release gestures to trigger CAST
        elif self.state in (STATE_GATHERING_QI, STATE_CHARGING):
            if gesture == "OPEN_PALM":
                # Cast the spell on open palm release
                self.trigger_cast()

    def on_dynamic_gesture_detected(self, motion: str, confidence: float) -> None:
        """
        Handle dynamic gesture signals (swipes/slashes).
        """
        if self.state == STATE_COOLDOWN:
            return

        self.last_dynamic_gesture = motion

        # Map dynamic gestures directly to spells if idle
        if self.state == STATE_IDLE:
            motion_map = {
                "swipe_left": "SHIELD",
                "swipe_right": "ENERGY_SLASH",
                "swipe_up": "EARTHQUAKE",
                "swipe_down": "LIGHTNING",
                "zoom_in": "HEAL",
                "zoom_out": "DRAGON_SUMMON",
                "rotate_cw": "AURA",
                "rotate_ccw": "MAGIC_FORMATION"
            }
            if motion in motion_map:
                self.active_spell = motion_map[motion]
                self.qi_level = SPELLS[self.active_spell]["qi_requirement"]
                self.trigger_cast()
        
        # If preparing or gathering, a fast slash can release the spell
        elif self.state in (STATE_PREPARING, STATE_GATHERING_QI, STATE_CHARGING):
            if motion in ("slash_up", "slash_down", "swipe_left", "swipe_right", "swipe_up", "swipe_down"):
                self.trigger_cast()

    def on_rune_detected(self, rune: str, confidence: float) -> None:
        """
        Handle 2D template-drawn runes.
        """
        if self.state == STATE_COOLDOWN:
            return

        # If we are preparing or gathering, drawing a rune boosts Qi and enters CHARGING
        if self.state in (STATE_PREPARING, STATE_GATHERING_QI, STATE_IDLE):
            if self.state == STATE_IDLE:
                # Direct rune cast mapping
                rune_spell_map = {
                    "FIRE_CIRCLE": "FIREBALL",
                    "TRIANGLE": "SHIELD",
                    "STAR": "LIGHTNING",
                    "SQUARE": "MAGIC_FORMATION",
                    "SPIRAL": "DRAGON_SUMMON",
                    "Z_SEAL": "ENERGY_SLASH"
                }
                if rune in rune_spell_map:
                    self.active_spell = rune_spell_map[rune]
                    self.active_rune = rune
                    self.qi_level = SPELLS[self.active_spell]["qi_requirement"] * 0.8
                    self.change_state(STATE_GATHERING_QI)
                    self.change_state(STATE_CHARGING)
            else:
                self.active_rune = rune
                # Boost Qi level
                spell_info = SPELLS[self.active_spell]
                self.qi_level = min(spell_info["qi_requirement"], self.qi_level + 15.0)
                self.change_state(STATE_CHARGING)

    def on_combo_detected(self, spell_name: str) -> None:
        """
        Handle sequence-based combo triggers.
        """
        if self.state == STATE_COOLDOWN:
            return

        # A combo instantly completes preparation and charges the spell fully
        if spell_name in SPELLS:
            self.active_spell = spell_name
            self.qi_level = SPELLS[spell_name]["qi_requirement"]
            print(f"[SpellEngine] Combo Detected: {spell_name}! Instantly fully charged.")
            self.change_state(STATE_PREPARING)
            self.change_state(STATE_GATHERING_QI)
            self.change_state(STATE_CHARGING)
            
            # Auto-cast combo spells on completion
            self.trigger_cast()

    def on_dual_hand_detected(self, spell_name: str) -> None:
        """
        Handle dual-hand Mudra combinations.
        """
        if self.state == STATE_COOLDOWN:
            return

        if spell_name in SPELLS:
            self.active_spell = spell_name
            self.qi_level = SPELLS[spell_name]["qi_requirement"]
            print(f"[SpellEngine] Dual-Hand mudra detected: {spell_name}!")
            self.change_state(STATE_PREPARING)
            self.change_state(STATE_GATHERING_QI)
            self.change_state(STATE_CHARGING)
            
            # Auto-cast dual-hand spells
            self.trigger_cast()

    def on_intensity_changed(self, velocity: float, intensity_val: float) -> None:
        """
        Handle live movement velocity updates to drive cultivation Qi build-up.
        """
        self.current_velocity = velocity
        self.current_intensity = intensity_val

        if not self.active_spell or self.active_spell not in SPELLS:
            return

        # If preparing, hand motion gathers Qi
        if self.state == STATE_PREPARING:
            if velocity > 0.2:
                self.qi_level = min(SPELLS[self.active_spell]["qi_requirement"], self.qi_level + velocity * 8.0)
                if self.qi_level >= SPELLS[self.active_spell]["qi_requirement"] * 0.5:
                    self.change_state(STATE_GATHERING_QI)
                    
        # If gathering Qi, movement adds energy
        elif self.state == STATE_GATHERING_QI:
            if velocity > 0.2:
                self.qi_level = min(SPELLS[self.active_spell]["qi_requirement"], self.qi_level + velocity * 12.0)
                if self.qi_level >= SPELLS[self.active_spell]["qi_requirement"]:
                    self.change_state(STATE_CHARGING)
