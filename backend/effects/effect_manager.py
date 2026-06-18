"""
effect_manager.py
-----------------
Manages 2D spell visual effects using Python Arcade.
Subscribes to spell events and renders cultivation circles, runes, and particle bursts.
"""

import time
import threading
import random
import math
from backend.events.event_bus import event_bus

# Try importing Pygame for a thread-safe window option on Windows
PYGAME_AVAILABLE = False
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    pass

# Try importing Arcade, handle missing package or display errors
ARCADE_AVAILABLE = False
try:
    import arcade
    ARCADE_AVAILABLE = True
except ImportError:
    pass

# HSL-based Color Palettes for Spells
PALETTES = {
    "FIREBALL": [(255, 69, 0), (255, 140, 0), (255, 215, 0)],      # Fire (Orange, Red-Orange, Gold)
    "SHIELD": [(0, 206, 209), (30, 144, 255), (135, 206, 250)],    # Shield (Cyan, Dodger Blue, Sky Blue)
    "ENERGY_SLASH": [(138, 43, 226), (186, 85, 211), (255, 0, 255)], # Slash (Purple, Violet, Magenta)
    "HEAL": [(50, 205, 50), (144, 238, 144), (0, 250, 154)],       # Wood/Heal (Lime, Light Green, Medium Spring Green)
    "LIGHTNING": [(255, 255, 0), (224, 255, 255), (0, 255, 255)],  # Lightning (Yellow, Azure, Cyan)
    "AURA": [(255, 223, 0), (255, 215, 0), (244, 196, 48)],        # Cultivation Aura (Gold, Saffron)
    "DRAGON_SUMMON": [(255, 69, 0), (148, 0, 211), (0, 255, 255)],  # Dragon (Prismatic Mix)
    "MAGIC_FORMATION": [(255, 105, 180), (138, 43, 226), (0, 0, 255)], # Array (Deep Purple/Pink/Blue)
    "EARTHQUAKE": [(139, 69, 19), (210, 180, 140), (160, 82, 45)],  # Earth (Brown, Tan, Sienna)
    "BARRIER": [(0, 206, 209), (30, 144, 255), (255, 255, 255)]     # Barrier (Cyan, Dodger Blue, White)
}

class Particle:
    """
    Represent a single visual spell particle.
    """
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: float, lifetime: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_lifetime = lifetime
        self.lifetime = lifetime

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        # Fade out size
        self.size = max(1.0, self.size * (self.lifetime / self.max_lifetime))

    def draw(self):
        if self.lifetime > 0 and ARCADE_AVAILABLE:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            color_with_alpha = (self.color[0], self.color[1], self.color[2], alpha)
            arcade.draw_circle_filled(self.x, self.y, self.size, color_with_alpha)

if ARCADE_AVAILABLE:
    class CultivationWindow(arcade.Window):
        """
        Arcade Window showing real-time cultivation spell visual effects.
        """
        def __init__(self, width: int = 800, height: int = 600) -> None:
            super().__init__(width, height, "Cultivation Magic Array Visualizer")
            arcade.set_background_color((15, 15, 25)) # Sleek dark mode space
            self.particles: list[Particle] = []
            
            # Cultivation visual states
            self.active_spell = None
            self.spell_state = "IDLE"
            self.qi_level = 0.0
            self.active_rune = None
            
            self.circle_angle = 0.0
            self.formation_rotation = 0.0

            # Register event subscriptions
            event_bus.subscribe("spell_preparing", self.on_spell_state)
            event_bus.subscribe("spell_gathering_qi", self.on_spell_state)
            event_bus.subscribe("spell_charging", self.on_spell_state)
            event_bus.subscribe("spell_cast", self.on_spell_cast)
            event_bus.subscribe("spell_cooldown", self.on_spell_state)
            event_bus.subscribe("spell_idle", self.on_spell_state)

        def on_spell_state(self, spell: str, state: str, qi: float) -> None:
            self.active_spell = spell
            self.spell_state = state
            self.qi_level = qi

        def on_spell_cast(self, payload: dict) -> None:
            self.active_spell = payload.get("spell")
            self.spell_state = payload.get("state")
            self.active_rune = payload.get("rune")
            power = payload.get("intensity", 1.0)
            
            # Spawn a massive particle burst from center (400, 300)
            colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
            num_particles = int(power * 60)
            
            for _ in range(num_particles):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 400) * power
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle)
                color = random.choice(colors)
                size = random.uniform(4, 12) * power
                lifetime = random.uniform(0.5, 1.5)
                
                self.particles.append(Particle(400, 300, vx, vy, color, size, lifetime))

        def on_update(self, delta_time: float) -> None:
            # Rotate visual elements
            self.circle_angle += 1.5 * delta_time
            self.formation_rotation -= 0.8 * delta_time

            # Update particles
            for p in self.particles:
                p.update(delta_time)
            # Filter dead particles
            self.particles = [p for p in self.particles if p.lifetime > 0]

            # Generate gathering particles swirling in
            if self.spell_state in ("PREPARING", "GATHERING_QI", "CHARGING") and self.active_spell:
                colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
                if random.random() < 0.3:
                    # Spawn particle at radius
                    angle = random.uniform(0, 2*math.pi)
                    r = 200.0
                    px = 400 + r * math.cos(angle)
                    py = 300 + r * math.sin(angle)
                    # Swirl velocity vector (pointing inward and slightly tangent)
                    vx = -120 * math.cos(angle) - 60 * math.sin(angle)
                    vy = -120 * math.sin(angle) + 60 * math.cos(angle)
                    self.particles.append(Particle(px, py, vx, vy, random.choice(colors), random.uniform(2, 5), 1.2))

        def on_draw(self) -> None:
            self.clear()
            
            # Draw particle systems
            for p in self.particles:
                p.draw()

            # Render Cultivation Array HUD
            arcade.draw_text("CULTIVATION REALM", 20, 560, arcade.color.GOLD, 18, font_name="Century Gothic")
            arcade.draw_text(f"State: {self.spell_state}", 20, 530, arcade.color.WHITE, 14)
            if self.active_spell:
                arcade.draw_text(f"Spell Focus: {self.active_spell}", 20, 505, arcade.color.AQUA, 14)
                arcade.draw_text(f"Qi Level: {self.qi_level:.1f}", 20, 480, arcade.color.GREEN, 14)

            # Draw the main magical circle if active
            if self.spell_state in ("PREPARING", "GATHERING_QI", "CHARGING") and self.active_spell:
                colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
                color = colors[0]
                
                # Outer circle
                arcade.draw_circle_outline(400, 300, 120, color, 3)
                # Inner rotating formation
                arcade.draw_circle_outline(400, 300, 90, color, 1)
                
                # Draw mudra/spell name text inside
                arcade.draw_text(
                    self.active_spell, 400, 292, color, 16, 
                    anchor_x="center", anchor_y="center", bold=True
                )
                
                # Draw drawing path (runes) if charging
                if self.spell_state == "CHARGING" and self.active_rune:
                    arcade.draw_text(
                        f"Rune: {self.active_rune}", 400, 250, arcade.color.GOLD, 12,
                        anchor_x="center", anchor_y="center"
                    )

            # Draw a cooling down overlay
            if self.spell_state == "COOLDOWN":
                arcade.draw_text(
                    "QI COOLDOWN...", 400, 300, arcade.color.RED, 22,
                    anchor_x="center", anchor_y="center", bold=True
                )

if PYGAME_AVAILABLE:
    class PygameCultivationWindow:
        """
        Pygame Window showing real-time cultivation spell visual effects.
        Thread-safe alternative to Arcade.
        """
        def __init__(self, width: int = 800, height: int = 600) -> None:
            self.width = width
            self.height = height
            self.running = False
            self.particles: list[Particle] = []
            
            # Cultivation visual states
            self.active_spell = None
            self.spell_state = "IDLE"
            self.qi_level = 0.0
            self.active_rune = None
            
            self.circle_angle = 0.0
            self.formation_rotation = 0.0

            # Register event subscriptions
            event_bus.subscribe("spell_preparing", self.on_spell_state)
            event_bus.subscribe("spell_gathering_qi", self.on_spell_state)
            event_bus.subscribe("spell_charging", self.on_spell_state)
            event_bus.subscribe("spell_cast", self.on_spell_cast)
            event_bus.subscribe("spell_cooldown", self.on_spell_state)
            event_bus.subscribe("spell_idle", self.on_spell_state)
            event_bus.subscribe("rune_detected", self.on_rune_detected)

        def on_spell_state(self, spell: str, state: str, qi: float) -> None:
            self.active_spell = spell
            self.spell_state = state
            self.qi_level = qi

        def on_rune_detected(self, rune: str, confidence: float) -> None:
            self.active_rune = rune

        def on_spell_cast(self, payload: dict) -> None:
            self.active_spell = payload.get("spell")
            self.spell_state = payload.get("state")
            self.active_rune = payload.get("rune")
            power = payload.get("intensity", 1.0)
            
            colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
            num_particles = int(power * 60)
            
            for _ in range(num_particles):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 400) * power
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle)
                color = random.choice(colors)
                size = random.uniform(4, 12) * power
                lifetime = random.uniform(0.5, 1.5)
                
                self.particles.append(Particle(400, 300, vx, vy, color, size, lifetime))

        def run(self) -> None:
            pygame.init()
            pygame.display.set_caption("Cultivation Magic Array Visualizer")
            screen = pygame.display.set_mode((self.width, self.height))
            clock = pygame.time.Clock()
            self.running = True
            
            try:
                font_title = pygame.font.SysFont("centurygothic", 20, bold=True)
                font_hud = pygame.font.SysFont("centurygothic", 14)
                font_spell = pygame.font.SysFont("centurygothic", 16, bold=True)
                font_cooldown = pygame.font.SysFont("centurygothic", 22, bold=True)
            except Exception:
                font_title = pygame.font.Font(None, 24)
                font_hud = pygame.font.Font(None, 18)
                font_spell = pygame.font.Font(None, 20)
                font_cooldown = pygame.font.Font(None, 28)

            while self.running:
                dt = clock.tick(60) / 1000.0 # Cap at 60 FPS
                
                # Event handling
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                
                # Update angles
                self.circle_angle += 1.5 * dt
                self.formation_rotation -= 0.8 * dt

                # Update particles
                for p in self.particles:
                    p.update(dt)
                self.particles = [p for p in self.particles if p.lifetime > 0]

                # Generate gathering particles swirling in
                if self.spell_state in ("PREPARING", "GATHERING_QI", "CHARGING") and self.active_spell:
                    colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
                    if random.random() < 0.3:
                        angle = random.uniform(0, 2 * math.pi)
                        r = 200.0
                        px = 400 + r * math.cos(angle)
                        py = 300 + r * math.sin(angle)
                        vx = -120 * math.cos(angle) - 60 * math.sin(angle)
                        vy = -120 * math.sin(angle) + 60 * math.cos(angle)
                        self.particles.append(Particle(px, py, vx, vy, random.choice(colors), random.uniform(2, 5), 1.2))

                # Draw everything
                screen.fill((15, 15, 25))

                # Draw particles
                for p in self.particles:
                    if p.lifetime > 0:
                        alpha = int(255 * (p.lifetime / p.max_lifetime))
                        p_size = int(max(1.0, p.size))
                        # Render alpha circle using a temporary surface
                        surf = pygame.Surface((p_size * 2, p_size * 2), pygame.SRCALPHA)
                        pygame.draw.circle(surf, (p.color[0], p.color[1], p.color[2], alpha), (p_size, p_size), p_size)
                        screen.blit(surf, (int(p.x - p_size), int(p.y - p_size)))

                # Draw HUD
                txt_realm = font_title.render("CULTIVATION REALM", True, (255, 215, 0)) # Gold
                screen.blit(txt_realm, (20, 20))

                txt_state = font_hud.render(f"State: {self.spell_state}", True, (255, 255, 255))
                screen.blit(txt_state, (20, 50))

                if self.active_spell:
                    txt_focus = font_hud.render(f"Spell Focus: {self.active_spell}", True, (0, 255, 255)) # Aqua
                    screen.blit(txt_focus, (20, 75))
                    txt_qi = font_hud.render(f"Qi Level: {self.qi_level:.1f}", True, (0, 255, 0)) # Green
                    screen.blit(txt_qi, (20, 100))

                    # Draw the main magical circle if active
                    if self.spell_state in ("PREPARING", "GATHERING_QI", "CHARGING"):
                        colors = PALETTES.get(self.active_spell, [(255, 255, 255)])
                        color = colors[0]

                        # Outer circle
                        pygame.draw.circle(screen, color, (400, 300), 120, 3)
                        # Inner rotating formation
                        pygame.draw.circle(screen, color, (400, 300), 90, 1)

                        # Draw spell name text inside
                        txt_name = font_spell.render(self.active_spell, True, color)
                        name_rect = txt_name.get_rect(center=(400, 292))
                        screen.blit(txt_name, name_rect)

                        # Draw active rune
                        if self.spell_state == "CHARGING" and self.active_rune:
                            txt_rune = font_hud.render(f"Rune: {self.active_rune}", True, (255, 215, 0))
                            rune_rect = txt_rune.get_rect(center=(400, 340))
                            screen.blit(txt_rune, rune_rect)

                if self.spell_state == "COOLDOWN":
                    txt_cd = font_cooldown.render("QI COOLDOWN...", True, (255, 0, 0))
                    cd_rect = txt_cd.get_rect(center=(400, 300))
                    screen.blit(txt_cd, cd_rect)

                pygame.display.flip()
            
            pygame.quit()

class EffectManager:
    """
    Wraps the visualizer window. Handles asynchronous execution.
    """
    def __init__(self) -> None:
        self.win = None
        
        # Simple logging subscriptions if Arcade is not available or window fails
        event_bus.subscribe("spell_cast", self.log_cast)

    def log_cast(self, payload: dict) -> None:
        spell = payload.get("spell")
        power = payload.get("intensity")
        print(f"[VFX] Visual burst for {spell} (Power: {power:.2f}, Details: {payload.get('effect_details')})")

    def run_window(self) -> None:
        """
        Runs the visualization window (prefers Pygame for Windows thread-safety).
        """
        if PYGAME_AVAILABLE:
            print("[VFX] Starting Pygame VFX visualizer...")
            def target():
                try:
                    self.win = PygameCultivationWindow()
                    self.win.run()
                except Exception as e:
                    print(f"[VFX] FAILED to start Pygame window: {e}. Running headless mode.")
            threading.Thread(target=target, daemon=True).start()
        elif ARCADE_AVAILABLE:
            print("[VFX] Starting Arcade VFX visualizer...")
            def target():
                try:
                    self.win = CultivationWindow()
                    arcade.run()
                except Exception as e:
                    print(f"[VFX] FAILED to start Arcade window: {e}. Running headless mode.")
            threading.Thread(target=target, daemon=True).start()
        else:
            print("[VFX] Neither Pygame nor Arcade is installed. Running headless mode.")

# Global effect manager instance
effect_manager = EffectManager()

if __name__ == "__main__":
    import time
    # Running directly will launch the visualizer window and mock some spell events
    if ARCADE_AVAILABLE:
        print("Starting standalone VFX Visualizer. Press Q to exit.")
        # Start effect manager
        effect_manager.run_window()
        
        # Emit mock events to show visual array
        def mock_events():
            time.sleep(2.0)
            event_bus.publish("spell_preparing", spell="FIREBALL", state="PREPARING", qi=10.0)
            time.sleep(1.5)
            event_bus.publish("spell_gathering_qi", spell="FIREBALL", state="GATHERING_QI", qi=30.0)
            time.sleep(1.5)
            event_bus.publish("spell_charging", spell="FIREBALL", state="CHARGING", qi=50.0)
            event_bus.publish("rune_detected", rune="FIRE_CIRCLE", confidence=0.95)
            time.sleep(1.5)
            # Cast
            event_bus.publish("spell_cast", {"spell": "FIREBALL", "state": "CASTING", "intensity": 2.8, "rune": "FIRE_CIRCLE"})
            time.sleep(3.0)
            
        threading.Thread(target=mock_events, daemon=True).start()
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exit Standalone VFX.")
