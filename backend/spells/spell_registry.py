"""
spell_registry.py
-----------------
Declarative registry for cultivation spells and Qi states.
"""

# Cultivation Qi States
STATE_IDLE = "IDLE"
STATE_PREPARING = "PREPARING"
STATE_GATHERING_QI = "GATHERING_QI"
STATE_CHARGING = "CHARGING"
STATE_CASTING = "CASTING"
STATE_COOLDOWN = "COOLDOWN"

# Canonical Cultivation Spells Definitions
SPELLS = {
    "FIREBALL": {
        "name": "Fireball",
        "description": "Gather fire Qi to unleash a blazing fireball",
        "cooldown": 2.0,
        "qi_requirement": 20.0,
        "unity_command": "fireball"
    },
    "SHIELD": {
        "name": "Shield",
        "description": "Create a defensive spiritual barrier",
        "cooldown": 3.0,
        "qi_requirement": 15.0,
        "unity_command": "swipe_left"  # Maps physical movement in Unity
    },
    "ENERGY_SLASH": {
        "name": "Energy Slash",
        "description": "Focus Qi into a sharp sword beam",
        "cooldown": 1.5,
        "qi_requirement": 10.0,
        "unity_command": "swipe_right"
    },
    "HEAL": {
        "name": "Heal",
        "description": "Circulate wood Qi to mend wounds",
        "cooldown": 5.0,
        "qi_requirement": 30.0,
        "unity_command": "zoom_in"
    },
    "LIGHTNING": {
        "name": "Lightning",
        "description": "Call down heavenly lightning tribulation",
        "cooldown": 4.0,
        "qi_requirement": 40.0,
        "unity_command": "swipe_down"
    },
    "AURA": {
        "name": "Aura",
        "description": "Unleash cultivation aura to pressure opponents",
        "cooldown": 6.0,
        "qi_requirement": 25.0,
        "unity_command": "rotate_cw"
    },
    "DRAGON_SUMMON": {
        "name": "Dragon Summon",
        "description": "Summon a spiritual Qi dragon",
        "cooldown": 10.0,
        "qi_requirement": 80.0,
        "unity_command": "zoom_out"
    },
    "MAGIC_FORMATION": {
        "name": "Magic Formation",
        "description": "Erect a complex runic cultivation array",
        "cooldown": 8.0,
        "qi_requirement": 50.0,
        "unity_command": "rotate_ccw"
    },
    "EARTHQUAKE": {
        "name": "Earthquake",
        "description": "Shatter the ground with earth Qi",
        "cooldown": 4.5,
        "qi_requirement": 35.0,
        "unity_command": "swipe_up"
    },
    "BARRIER": {
        "name": "Barrier",
        "description": "Erect a solid defense barrier using both hands",
        "cooldown": 3.0,
        "qi_requirement": 20.0,
        "unity_command": "barrier"
    }
}

