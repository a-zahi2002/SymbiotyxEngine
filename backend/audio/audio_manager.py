"""
audio_manager.py
----------------
Audio manager to trigger sound effects based on event bus signals.
Supports Pygame mixer with winsound beeps as Windows-native fallbacks.
"""

import os
import sys
import threading
from backend.events.event_bus import event_bus

class AudioManager:
    """
    Handles sound effects for cultivation spells.
    """
    def __init__(self) -> None:
        self.enabled = False
        
        # Try to initialize Pygame Mixer
        try:
            import pygame
            pygame.mixer.init()
            self.enabled = True
            print("[AudioManager] Pygame mixer initialized successfully.")
        except Exception as e:
            print(f"[AudioManager] Pygame mixer initialization failed ({e}). Falling back to winsound.")
            
        self.sound_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "audio"))
        self.sounds = {}
        
        if self.enabled:
            self._load_sounds()

        # Subscribe to spell state events on the Event Bus
        event_bus.subscribe("spell_preparing", self.on_spell_preparing)
        event_bus.subscribe("spell_gathering_qi", self.on_spell_gathering_qi)
        event_bus.subscribe("spell_charging", self.on_spell_charging)
        event_bus.subscribe("spell_cast", self.on_spell_cast)
        event_bus.subscribe("spell_cooldown", self.on_spell_cooldown)

    def _load_sounds(self) -> None:
        """
        Load sound files if they exist.
        """
        if not os.path.exists(self.sound_dir):
            return
            
        import pygame
        for file in os.listdir(self.sound_dir):
            if file.endswith((".wav", ".mp3")):
                name = os.path.splitext(file)[0].lower()
                path = os.path.join(self.sound_dir, file)
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[AudioManager] Failed to load {file}: {e}")

    def play_sound(self, sound_name: str, fallback_freq: int = 440, fallback_duration: int = 150) -> None:
        """
        Play a sound, or beep if files are missing.
        """
        sound_name = sound_name.lower()
        if self.enabled and sound_name in self.sounds:
            # Play using Pygame in a separate thread to prevent blocking
            threading.Thread(target=self.sounds[sound_name].play, daemon=True).start()
        else:
            # Fallback beep on Windows
            if sys.platform == "win32":
                threading.Thread(target=self._beep, args=(fallback_freq, fallback_duration), daemon=True).start()
            else:
                print(f"[AudioManager] BEEP: {fallback_freq}Hz, {fallback_duration}ms (Sound '{sound_name}' missing)")

    def _beep(self, freq: int, duration: int) -> None:
        try:
            import winsound
            winsound.Beep(freq, duration)
        except Exception:
            pass

    # ─────────────────────────── Event Subscriptions ───────────────────────────

    def on_spell_preparing(self, spell: str, state: str, qi: float) -> None:
        print(f"[Audio] Preparing {spell}... (Qi: {qi})")
        self.play_sound("prepare", fallback_freq=400, fallback_duration=120)

    def on_spell_gathering_qi(self, spell: str, state: str, qi: float) -> None:
        print(f"[Audio] Gathering Qi for {spell}... (Qi: {qi:.1f})")
        self.play_sound("gather", fallback_freq=520, fallback_duration=150)

    def on_spell_charging(self, spell: str, state: str, qi: float) -> None:
        print(f"[Audio] Spell charging: {spell}! (Qi: {qi:.1f})")
        self.play_sound("charge", fallback_freq=650, fallback_duration=200)

    def on_spell_cast(self, payload: dict) -> None:
        spell = payload.get("spell", "spell")
        power = payload.get("intensity", 1.0)
        print(f"[Audio] Casting spell: {spell}! Power: {power:.2f}")
        # Cast sound is longer and higher pitch
        self.play_sound("cast", fallback_freq=880, fallback_duration=400)

    def on_spell_cooldown(self, spell: str, state: str, qi: float) -> None:
        print(f"[Audio] Spell entered cooldown: {spell}")
        self.play_sound("cooldown", fallback_freq=300, fallback_duration=180)

if __name__ == "__main__":
    import time
    print("=== AudioManager Test ===")
    manager = AudioManager()
    
    # Test prepare sound
    event_bus.publish("spell_preparing", spell="FIREBALL", state="PREPARING", qi=10.0)
    time.sleep(0.5)
    # Test cast sound
    event_bus.publish("spell_cast", {"spell": "FIREBALL", "intensity": 2.5})
    time.sleep(1.0)
