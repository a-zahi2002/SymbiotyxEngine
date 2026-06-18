using UnityEngine;

/// <summary>
/// Visual effects for the GestureOrb. Reacts to intensity from the backend.
/// Smoothly interpolates scale (zoom) and color, drives trail/particle effects.
/// </summary>
public class OrbEffects : MonoBehaviour
{
    [Header("Zoom Settings")]
    public float zoomSpeed = 8f;
    public float baseScale = 1f;
    public float scaleMultiplier = 0.5f;

    [Header("Color Options")]
    public Color lowIntensityColor = new Color(0.2f, 0.4f, 1f, 1f); // Cool Blue
    public Color highIntensityColor = new Color(1f, 0.2f, 0.4f, 1f); // Hot Pink/Red
    public float maxIntensityForColor = 3f;

    [Header("Hand Tracking Mapping")]
    public float trackingSpeed = 12f;
    public float horizontalRange = 12f;
    public float verticalRange = 8f;
    public float depthRange = -6f;

    private SpellEffectsManager spellEffectsManager;
    private OrbRotator orbRotator;

    [Header("VFX Components (Auto-created if missing)")]
    private Renderer[] orbRenderers;
    private MaterialPropertyBlock propertyBlock;
    private TrailRenderer trail;
    private ParticleSystem particles;

    private float targetIntensity = 0f;
    private float currentIntensity = 0f;
    
    private Vector3 startPosition;
    private Vector3 targetPosition;
    private Quaternion targetRotation;
    private string currentSpell = "NONE";

    void Awake()
    {
        startPosition = transform.position;
        targetPosition = startPosition;
        targetRotation = transform.rotation;
        
        orbRenderers = GetComponentsInChildren<Renderer>();
        propertyBlock = new MaterialPropertyBlock();

        // Setup Spell Effects Manager
        spellEffectsManager = FindObjectOfType<SpellEffectsManager>();
        if (spellEffectsManager == null)
        {
            spellEffectsManager = gameObject.AddComponent<SpellEffectsManager>();
        }

        // Get OrbRotator (on same GameObject) to suppress idle spin during gestures
        orbRotator = GetComponent<OrbRotator>();

        // 1) Setup Trail Renderer
        trail = GetComponent<TrailRenderer>();
        if (trail == null)
        {
            trail = gameObject.AddComponent<TrailRenderer>();
            trail.startWidth = 0.5f;
            trail.endWidth = 0f;
            trail.time = 0.5f;
            trail.material = new Material(Shader.Find("Sprites/Default")); // Basic visible material
        }

        // 2) Setup Particle System
        particles = GetComponent<ParticleSystem>();
        if (particles == null)
        {
            GameObject psObj = new GameObject("OrbParticles");
            psObj.transform.SetParent(this.transform, false);
            particles = psObj.AddComponent<ParticleSystem>();
            
            // Basic Burst Config
            var main = particles.main;
            main.playOnAwake = false;
            main.loop = false;
            main.startSpeed = 5f;
            main.startSize = 0.3f;
            main.startLifetime = 1f;
            
            var emission = particles.emission;
            emission.rateOverTime = 0; // Only burst manually
        }
    }

    void Update()
    {
        // Crisp smooth lerp for real-time tracking
        currentIntensity = Mathf.Lerp(currentIntensity, targetIntensity, Time.deltaTime * zoomSpeed);
        
        // Spatial Lerp for dynamic movement (use snappier trackingSpeed when tracking coordinates)
        float currentSpeed = (currentSpell != "NONE" && currentSpell != "idle") ? zoomSpeed : trackingSpeed;
        transform.position = Vector3.Lerp(transform.position, targetPosition, Time.deltaTime * currentSpeed);
        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * zoomSpeed);

        // --- 1. Zoom (Scale) ---
        float targetScale = baseScale + (currentIntensity * scaleMultiplier);
        transform.localScale = Vector3.one * targetScale;

        // --- 2. Colors & Glow ---
        Color targetColor = GetSpellColor(currentSpell, currentIntensity);

        if (orbRenderers != null)
        {
            foreach (Renderer rnd in orbRenderers)
            {
                if (rnd == null || rnd == trail) continue;
                rnd.GetPropertyBlock(propertyBlock);
                propertyBlock.SetColor("_BaseColor", targetColor);
                propertyBlock.SetColor("_Color", targetColor);
                propertyBlock.SetColor("_EmissionColor", targetColor * (1f + currentIntensity)); 
                rnd.SetPropertyBlock(propertyBlock);
            }
        }

        // --- 3. Trail Renderer ---
        if (trail != null)
        {
            trail.startColor = targetColor;
            trail.endColor = new Color(targetColor.r, targetColor.g, targetColor.b, 0f);
            trail.startWidth = 0.5f + (currentIntensity * 0.2f);
        }
    }

    /// <summary>
    /// Overload for backwards compatibility or manual trigger.
    /// </summary>
    public void HandleGesture(string command, float intensity)
    {
        GestureCommand cmd = new GestureCommand { command = command, intensity = intensity, spell = "NONE" };
        HandleGesture(cmd);
    }

    /// <summary>
    /// Parses specific gestures mapped from the Backend into 3D movements.
    /// </summary>
    public void HandleGesture(GestureCommand cmd)
    {
        if (cmd == null) return;
        string command = cmd.command;
        float intensity = cmd.intensity;
        currentSpell = cmd.spell;

        // Tell OrbRotator to pause idle spin (gesture is active)
        if (orbRotator != null && command != "idle")
        {
            orbRotator.NotifyCommandReceived();
        }
        
        // Ensure idle resets all transforms
        if (command == "idle")
        {
            targetPosition = startPosition;
            targetIntensity = 0f;
            currentSpell = "NONE";
            return;
        }
        
        targetIntensity = intensity;
        
        if (cmd.has_hand)
        {
            // Move orb directly to user's hand coordinates (MediaPipe X/Y/Z)
            float tx = (cmd.hand_x - 0.5f) * horizontalRange;
            float ty = (0.5f - cmd.hand_y) * verticalRange;
            float tz = cmd.hand_z * depthRange;
            
            targetPosition = startPosition + new Vector3(tx, ty, tz);
            
            // Allow rotation events to affect orientation during tracking
            if (command.ToLower() == "rotate_cw")
            {
                targetRotation *= Quaternion.Euler(0, intensity * 45f, 0);
            }
            else if (command.ToLower() == "rotate_ccw")
            {
                targetRotation *= Quaternion.Euler(0, -intensity * 45f, 0);
            }
        }
        else
        {
            // React physically to the specific command type (Rule-based Fallback)
            switch (command.ToLower())
            {
                case "swipe_left":
                    targetPosition = startPosition + (Vector3.left * intensity * 2f);
                    break;
                case "swipe_right":
                    targetPosition = startPosition + (Vector3.right * intensity * 2f);
                    break;
                case "rotate_cw":
                    targetRotation *= Quaternion.Euler(0, intensity * 45f, 0);
                    break;
                case "rotate_ccw":
                    targetRotation *= Quaternion.Euler(0, -intensity * 45f, 0);
                    break;
                case "zoom_in":
                    targetIntensity = intensity * 1.5f;
                    targetPosition = startPosition + (Vector3.back * intensity * 1f); // push towards camera
                    break;
                case "zoom_out":
                    targetIntensity = intensity * 0.5f;
                    targetPosition = startPosition + (Vector3.forward * intensity * 1f); // push away
                    break;
                case "tracking":
                    // Scale in place
                    break;
                case "barrier":
                    targetIntensity = intensity * 2.0f;
                    targetPosition = startPosition; // hold center
                    break;
                case "swipe_up":
                    targetPosition = startPosition + (Vector3.up * intensity * 2f);
                    break;
                case "swipe_down":
                    targetPosition = startPosition + (Vector3.down * intensity * 2f);
                    break;
            }
        }
        
        // Trigger procedural cultivation spell effects in Unity via SpellEffectsManager
        if (spellEffectsManager != null && !string.IsNullOrEmpty(cmd.spell) && cmd.spell != "NONE")
        {
            spellEffectsManager.CastSpell(cmd.spell, transform.position, intensity);
        }
        
        // Particle burst on distinct final commands (secondary visual layer)
        if (command != "tracking" && intensity > 1.5f && particles != null)
        {
            var main = particles.main;
            Color burstColor = GetSpellColor(currentSpell, intensity);
            main.startColor = burstColor;
            particles.Emit((int)(intensity * 10)); 
        }
    }

    /// <summary>
    /// Gets a color specific to each spell type for premium visual effects.
    /// </summary>
    private Color GetSpellColor(string spell, float intensity)
    {
        if (string.IsNullOrEmpty(spell) || spell == "NONE")
        {
            float t = Mathf.Clamp01(intensity / maxIntensityForColor);
            return Color.Lerp(lowIntensityColor, highIntensityColor, t);
        }

        switch (spell.ToUpper())
        {
            case "FIREBALL":
                return new Color(1f, 0.3f, 0f, 1f); // Blazing Orange
            case "SHIELD":
            case "BARRIER":
                return new Color(0.2f, 0.8f, 1f, 1f); // Cyan Shield
            case "ENERGY_SLASH":
                return new Color(0.7f, 0f, 1f, 1f); // Purple Slash
            case "HEAL":
                return new Color(0.2f, 1f, 0.4f, 1f); // Green Heal
            case "LIGHTNING":
                return new Color(1f, 0.9f, 0f, 1f); // Yellow Lightning
            case "AURA":
                return new Color(1f, 0.84f, 0f, 1f); // Golden Aura
            case "DRAGON_SUMMON":
                return new Color(1f, 0.2f, 0.6f, 1f); // Prismatic Magenta/Pink
            case "MAGIC_FORMATION":
                return new Color(0.5f, 0f, 0.5f, 1f); // Deep Purple
            case "EARTHQUAKE":
                return new Color(0.6f, 0.4f, 0.2f, 1f); // Earthy Brown
            default:
                float tDef = Mathf.Clamp01(intensity / maxIntensityForColor);
                return Color.Lerp(lowIntensityColor, highIntensityColor, tDef);
        }
    }
}