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

    void Awake()
    {
        startPosition = transform.position;
        targetPosition = startPosition;
        targetRotation = transform.rotation;
        
        orbRenderers = GetComponentsInChildren<Renderer>();
        propertyBlock = new MaterialPropertyBlock();

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
        
        // Spatial Lerp for dynamic movement
        transform.position = Vector3.Lerp(transform.position, targetPosition, Time.deltaTime * zoomSpeed);
        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * zoomSpeed);

        // --- 1. Zoom (Scale) ---
        float targetScale = baseScale + (currentIntensity * scaleMultiplier);
        transform.localScale = Vector3.one * targetScale;

        // --- 2. Colors & Glow ---
        float t = Mathf.Clamp01(currentIntensity / maxIntensityForColor);
        Color lerpedColor = Color.Lerp(lowIntensityColor, highIntensityColor, t);

        if (orbRenderers != null)
        {
            foreach (Renderer rnd in orbRenderers)
            {
                if (rnd == null || rnd == trail) continue;
                rnd.GetPropertyBlock(propertyBlock);
                propertyBlock.SetColor("_BaseColor", lerpedColor);
                propertyBlock.SetColor("_Color", lerpedColor);
                propertyBlock.SetColor("_EmissionColor", lerpedColor * (1f + currentIntensity)); 
                rnd.SetPropertyBlock(propertyBlock);
            }
        }

        // --- 3. Trail Renderer ---
        if (trail != null)
        {
            trail.startColor = lerpedColor;
            trail.endColor = new Color(lerpedColor.r, lerpedColor.g, lerpedColor.b, 0f);
            trail.startWidth = 0.5f + (currentIntensity * 0.2f);
        }
    }

    /// <summary>
    /// Parses specific gestures mapped from the Backend into 3D movements.
    /// </summary>
    public void HandleGesture(string command, float intensity)
    {
        // Ensure idle resets all transforms
        if (command == "idle")
        {
            targetPosition = startPosition;
            targetIntensity = 0f;
            return;
        }
        
        targetIntensity = intensity;
        
        // React physically to the specific command type
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
                // Just scales in place based on raw hand distance
                break;
        }
        
        // Particle burst on distinct final commands
        if (command != "tracking" && intensity > 1.5f && particles != null)
        {
            var main = particles.main;
            main.startColor = Color.Lerp(lowIntensityColor, highIntensityColor, intensity / maxIntensityForColor);
            particles.Emit((int)(intensity * 10)); 
        }
    }
}