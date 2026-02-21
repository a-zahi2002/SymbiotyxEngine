using UnityEngine;

/// <summary>
/// Visual effects for the GestureOrb. Reacts to intensity from the backend.
/// Smoothly interpolates scale (zoom) and color based on received intensity.
/// </summary>
[RequireComponent(typeof(Renderer))]
public class OrbEffects : MonoBehaviour
{
    [Header("Zoom Settings")]
    [Tooltip("How fast the orb scales toward the target size.")]
    public float zoomSpeed = 5f;

    [Tooltip("Base scale of the orb (at intensity 0).")]
    public float baseScale = 1f;

    [Tooltip("How much each unit of intensity adds to the scale.")]
    public float scaleMultiplier = 0.5f;

    [Header("Color Settings")]
    [Tooltip("Color at low intensity.")]
    public Color lowIntensityColor = Color.blue;

    [Tooltip("Color at high intensity.")]
    public Color highIntensityColor = Color.red;

    [Tooltip("Intensity value at which color is fully 'high'.")]
    public float maxIntensityForColor = 3f;

    // Internal state
    private float targetIntensity = 0f;
    private float currentIntensity = 0f;
    private Renderer orbRenderer;
    private MaterialPropertyBlock propertyBlock;

    void Awake()
    {
        orbRenderer = GetComponent<Renderer>();
        propertyBlock = new MaterialPropertyBlock();

        if (orbRenderer == null)
        {
            Debug.LogError("[OrbEffects] No Renderer found on " + gameObject.name);
        }
        else
        {
            Debug.Log("[OrbEffects] Initialized on " + gameObject.name);
        }
    }

    void Update()
    {
        // Smoothly interpolate current intensity toward the target
        currentIntensity = Mathf.Lerp(currentIntensity, targetIntensity, Time.deltaTime * zoomSpeed);

        // --- Zoom (Scale) ---
        float targetScale = baseScale + (currentIntensity * scaleMultiplier);
        transform.localScale = Vector3.one * targetScale;

        // --- Color ---
        if (orbRenderer != null)
        {
            float t = Mathf.Clamp01(currentIntensity / maxIntensityForColor);
            Color lerpedColor = Color.Lerp(lowIntensityColor, highIntensityColor, t);

            // Use MaterialPropertyBlock to avoid creating material instances
            orbRenderer.GetPropertyBlock(propertyBlock);
            propertyBlock.SetColor("_BaseColor", lerpedColor);  // URP
            propertyBlock.SetColor("_Color", lerpedColor);      // Built-in
            orbRenderer.SetPropertyBlock(propertyBlock);
        }
    }

    /// <summary>
    /// Called by CommandReceiver when a new intensity value is received.
    /// </summary>
    public void SetIntensity(float intensity)
    {
        targetIntensity = intensity;
        Debug.Log($"[OrbEffects] Intensity set to {intensity:F2} → target scale: {baseScale + intensity * scaleMultiplier:F2}");
    }
}