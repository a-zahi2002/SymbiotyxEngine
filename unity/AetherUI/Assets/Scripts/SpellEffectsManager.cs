using UnityEngine;
using System.Collections;
using System.Collections.Generic;

/// <summary>
/// Procedural Spell Effects Manager for SymbiotixEngine.
/// Spawns premium Donghua-style cultivation magic effects without external assets.
/// </summary>
public class SpellEffectsManager : MonoBehaviour
{
    public static SpellEffectsManager Instance { get; private set; }

    [Header("Default Colors")]
    public Color fireColor = new Color(1f, 0.25f, 0f, 1f);      // Blazing Orange
    public Color shieldColor = new Color(0.2f, 0.8f, 1f, 0.6f);  // Cyan Barrier
    public Color slashColor = new Color(0.6f, 0f, 1f, 0.8f);     // Purple Sword Beam
    public Color healColor = new Color(0.2f, 1f, 0.4f, 0.8f);    // Wood Green
    public Color lightningColor = new Color(1f, 0.9f, 0f, 1f);   // Heavenly Gold/Yellow
    public Color auraColor = new Color(1f, 0.75f, 0f, 0.8f);     // Golden Emperor Aura
    public Color dragonColor = new Color(1f, 0.1f, 0.6f, 0.8f);   // Magenta Dragon Qi

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
        }
    }

    /// <summary>
    /// Entry point to cast a spell in Unity.
    /// </summary>
    public void CastSpell(string spellName, Vector3 origin, float intensity)
    {
        Debug.Log($"✨ [SpellEffectsManager] Casting Spell: {spellName} | Intensity: {intensity:F2}");
        
        switch (spellName.ToUpper())
        {
            case "FIREBALL":
                SpawnFireball(origin, intensity);
                break;
            case "SHIELD":
            case "BARRIER":
                SpawnShield(origin, intensity);
                break;
            case "ENERGY_SLASH":
                SpawnEnergySlash(origin, intensity);
                break;
            case "HEAL":
                SpawnHeal(origin, intensity);
                break;
            case "LIGHTNING":
                SpawnLightning(origin, intensity);
                break;
            case "AURA":
                SpawnAura(origin, intensity);
                break;
            case "DRAGON_SUMMON":
                SpawnDragonSummon(origin, intensity);
                break;
            case "MAGIC_FORMATION":
                SpawnMagicFormation(origin, intensity);
                break;
            case "EARTHQUAKE":
                SpawnEarthquake(origin, intensity);
                break;
            default:
                Debug.LogWarning($"Unknown spell: {spellName}");
                break;
        }
    }

    #region Shader & Material Helpers

    private Material CreateSpellMaterial(Color color, bool transparent = true, bool additive = false)
    {
        // Use URP shader if available, fallback to Standard
        Shader targetShader = Shader.Find("Universal Render Pipeline/Lit");
        if (targetShader == null)
        {
            targetShader = Shader.Find("Standard");
        }

        Material mat = new Material(targetShader);

        if (transparent)
        {
            // Set up transparent URP properties
            mat.SetFloat("_Surface", 1); // Transparent
            mat.SetFloat("_Blend", additive ? 1 : 0); // Additive = 1, Alpha = 0
            mat.SetOverrideTag("RenderType", "Transparent");
            
            // Standard Shader compatibility fallback settings
            mat.SetInt("_SrcBlend", (int)(additive ? UnityEngine.Rendering.BlendMode.One : UnityEngine.Rendering.BlendMode.SrcAlpha));
            mat.SetInt("_DstBlend", (int)(additive ? UnityEngine.Rendering.BlendMode.One : UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha));
            mat.SetInt("_ZWrite", 0);
            mat.DisableKeyword("_ALPHATEST_ON");
            mat.EnableKeyword("_ALPHABLEND_ON");
            if (additive) mat.EnableKeyword("_ALPHAPREMULTIPLY_ON");
            mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        }

        mat.SetColor("_BaseColor", color);
        mat.SetColor("_Color", color);

        // Turn on Emission for extreme Donghua glow
        mat.EnableKeyword("_EMISSION");
        mat.SetColor("_EmissionColor", color * 2.5f);

        return mat;
    }

    #endregion

    #region Fireball

    private void SpawnFireball(Vector3 origin, float intensity)
    {
        GameObject fireball = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        fireball.name = "FireballSpell";
        fireball.transform.position = origin;
        fireball.transform.localScale = Vector3.one * 0.8f * intensity;

        // Prevent collision physics bumping
        if (fireball.TryGetComponent<Collider>(out Collider col))
        {
            col.isTrigger = true;
        }

        // Apply orange glowing material
        Renderer ren = fireball.GetComponent<Renderer>();
        ren.material = CreateSpellMaterial(fireColor, true, true);

        // Add Light component inside
        Light light = fireball.AddComponent<Light>();
        light.color = fireColor;
        light.range = 8f * intensity;
        light.intensity = 3f * intensity;

        // Add Trail
        TrailRenderer trail = fireball.AddComponent<TrailRenderer>();
        trail.startWidth = 0.5f * intensity;
        trail.endWidth = 0f;
        trail.time = 0.4s;
        trail.material = CreateSpellMaterial(fireColor, true, true);
        
        // Gradient color for trail
        Gradient gradient = new Gradient();
        gradient.SetKeys(
            new GradientColorKey[] { new GradientColorKey(fireColor, 0f), new GradientColorKey(Color.red, 0.7f), new GradientColorKey(Color.black, 1f) },
            new GradientAlphaKey[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0.5f, 0.8f), new GradientAlphaKey(0f, 1f) }
        );
        trail.colorGradient = gradient;

        // Add movement script to shoot forward
        ProjectileMovement pm = fireball.AddComponent<ProjectileMovement>();
        pm.direction = Vector3.forward;
        pm.speed = 18f;
        pm.lifeTime = 2.5f;
        pm.burstColor = fireColor;
    }

    #endregion

    #region Shield / Barrier

    private void SpawnShield(Vector3 origin, float intensity)
    {
        // Spawns a beautiful glowing shield hemisphere in front of the caster
        GameObject shield = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        shield.name = "SpiritualShield";
        shield.transform.position = origin + Vector3.forward * 1.5f;
        shield.transform.localScale = Vector3.zero; // Animation scales it up

        if (shield.TryGetComponent<Collider>(out Collider col))
        {
            col.isTrigger = true;
        }

        Renderer ren = shield.GetComponent<Renderer>();
        ren.material = CreateSpellMaterial(shieldColor, true, false);

        // Light inside
        Light light = shield.AddComponent<Light>();
        light.color = shieldColor;
        light.range = 6f * intensity;
        light.intensity = 2f;

        // Shield animation script
        ShieldAnimator sa = shield.AddComponent<ShieldAnimator>();
        sa.targetScale = new Vector3(3f, 3f, 0.5f) * intensity; // Flat oval barrier
        sa.duration = 2.0f;
        sa.lightComponent = light;
        sa.shieldColor = shieldColor;
    }

    #endregion

    #region Energy Slash

    private void SpawnEnergySlash(Vector3 origin, float intensity)
    {
        // Spawns a glowing purple crescent blade
        GameObject slash = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        slash.name = "EnergySlash";
        slash.transform.position = origin + Vector3.forward * 0.5f;
        
        // Shape like a crescent: wide, thin, short height
        slash.transform.localScale = new Vector3(4.5f * intensity, 0.05f, 0.4f * intensity);
        // Rotate so flat cylinder side faces forward
        slash.transform.rotation = Quaternion.Euler(90f, 0f, 0f);

        if (slash.TryGetComponent<Collider>(out Collider col))
        {
            col.isTrigger = true;
        }

        Renderer ren = slash.GetComponent<Renderer>();
        ren.material = CreateSpellMaterial(slashColor, true, true);

        // Light
        Light light = slash.AddComponent<Light>();
        light.color = slashColor;
        light.range = 6f;
        light.intensity = 2f;

        // Trail
        TrailRenderer trail = slash.AddComponent<TrailRenderer>();
        trail.startWidth = 2.5f * intensity;
        trail.endWidth = 0f;
        trail.time = 0.3s;
        trail.material = CreateSpellMaterial(slashColor, true, true);

        // Move forward rapidly and rotate around Z axis for a spin effect
        ProjectileMovement pm = slash.AddComponent<ProjectileMovement>();
        pm.direction = Vector3.forward;
        pm.speed = 26f;
        pm.lifeTime = 1.2f;
        pm.spinVector = new Vector3(0f, 0f, 360f); // Spin on forward axis
        pm.burstColor = slashColor;
    }

    #endregion

    #region Heal

    private void SpawnHeal(Vector3 origin, float intensity)
    {
        // Spawns wood-element rising healing circles around the caster
        for (int i = 0; i < 3; i++)
        {
            GameObject ring = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            ring.name = "HealRing";
            ring.transform.position = origin + Vector3.down * 0.5f;
            ring.transform.localScale = new Vector3(1.5f, 0.02f, 1.5f);
            
            // Remove collider
            if (ring.TryGetComponent<Collider>(out Collider col))
            {
                Destroy(col);
            }

            Renderer ren = ring.GetComponent<Renderer>();
            ren.material = CreateSpellMaterial(healColor, true, false);

            RisingRing rr = ring.AddComponent<RisingRing>();
            rr.speed = 2.5f + i * 0.8f;
            rr.scaleSpeed = 2f;
            rr.delay = i * 0.25f;
            rr.maxHeight = 3f;
            rr.baseColor = healColor;
        }

        // Spawn a green light glow
        GameObject healLightObj = new GameObject("HealLight");
        healLightObj.transform.position = origin;
        Light light = healLightObj.AddComponent<Light>();
        light.color = healColor;
        light.range = 8f * intensity;
        light.intensity = 3f * intensity;
        Destroy(healLightObj, 1.5f);
    }

    #endregion

    #region Lightning

    private void SpawnLightning(Vector3 origin, float intensity)
    {
        // Spawns heavenly lightning striking from the sky onto the target
        GameObject bolt = new GameObject("LightningBolt");
        bolt.transform.position = origin;

        LineRenderer lr = bolt.AddComponent<LineRenderer>();
        lr.startWidth = 0.25f * intensity;
        lr.endWidth = 0.05f;
        lr.material = CreateSpellMaterial(lightningColor, true, true);

        // Flash Light
        Light light = bolt.AddComponent<Light>();
        light.color = lightningColor;
        light.range = 15f;
        light.intensity = 5f * intensity;

        LightningAnimator la = bolt.AddComponent<LightningAnimator>();
        la.startPoint = origin + new Vector3(Random.Range(-3f, 3f), 15f, Random.Range(-1f, 1f));
        la.endPoint = origin;
        la.intensity = intensity;
    }

    #endregion

    #region Aura

    private void SpawnAura(Vector3 origin, float intensity)
    {
        // Unleashes a large golden shockwave ring expanding outwards
        GameObject wave = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        wave.name = "EmperorAuraWave";
        wave.transform.position = origin + Vector3.down * 0.3f;
        wave.transform.localScale = new Vector3(0.1f, 0.02f, 0.1f);

        if (wave.TryGetComponent<Collider>(out Collider col))
        {
            Destroy(col);
        }

        Renderer ren = wave.GetComponent<Renderer>();
        ren.material = CreateSpellMaterial(auraColor, true, true);

        Light light = wave.AddComponent<Light>();
        light.color = auraColor;
        light.range = 5f;
        light.intensity = 3f;

        AuraShockwave ash = wave.AddComponent<AuraShockwave>();
        ash.expandSpeed = 16f * intensity;
        ash.duration = 0.8f;
        ash.baseColor = auraColor;
        ash.lightComponent = light;
    }

    #endregion

    #region Dragon Summon

    private void SpawnDragonSummon(Vector3 origin, float intensity)
    {
        // Creates a spiral ascending dragon energy effect by coiling glowing magenta particles
        GameObject dragonRoot = new GameObject("DragonSummonCore");
        dragonRoot.transform.position = origin;

        for (int i = 0; i < 2; i++)
        {
            GameObject coil = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            coil.name = "DragonCoil";
            coil.transform.position = origin;
            coil.transform.localScale = Vector3.one * 0.4f;

            if (coil.TryGetComponent<Collider>(out Collider col))
            {
                Destroy(col);
            }

            Renderer ren = coil.GetComponent<Renderer>();
            ren.material = CreateSpellMaterial(dragonColor, true, true);

            TrailRenderer trail = coil.AddComponent<TrailRenderer>();
            trail.startWidth = 0.6f * intensity;
            trail.endWidth = 0.0f;
            trail.time = 0.6f;
            trail.material = CreateSpellMaterial(dragonColor, true, true);

            DragonCoil dc = coil.AddComponent<DragonCoil>();
            dc.parentCore = dragonRoot.transform;
            dc.spinSpeed = 600f * (i == 0 ? 1f : -1f); // Counter-rotating coils
            dc.verticalSpeed = 6f;
            dc.radius = 1.6f;
            dc.delay = i * 0.15f;
        }

        Destroy(dragonRoot, 3.5f);
    }

    #endregion

    #region Magic Formation

    private void SpawnMagicFormation(Vector3 origin, float intensity)
    {
        // Spawns a concentric rotating cultivation array under the caster's feet
        GameObject formation = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        formation.name = "MagicFormationArray";
        formation.transform.position = origin + Vector3.down * 1.5f;
        formation.transform.localScale = new Vector3(6f * intensity, 0.01f, 6f * intensity);

        if (formation.TryGetComponent<Collider>(out Collider col))
        {
            Destroy(col);
        }

        Renderer ren = formation.GetComponent<Renderer>();
        ren.material = CreateSpellMaterial(new Color(0.5f, 0f, 0.7f, 0.4f), true, false); // Purple magic circle

        // Add a rotating child ring
        GameObject innerRing = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        innerRing.name = "FormationInnerRing";
        innerRing.transform.SetParent(formation.transform, false);
        innerRing.transform.localPosition = new Vector3(0f, 1f, 0f); // slightly offset up
        innerRing.transform.localScale = new Vector3(0.7f, 1.2f, 0.7f); // Concentric smaller ring
        
        if (innerRing.TryGetComponent<Collider>(out Collider colInner))
        {
            Destroy(colInner);
        }

        Renderer renInner = innerRing.GetComponent<Renderer>();
        renInner.material = CreateSpellMaterial(new Color(0.8f, 0.2f, 1f, 0.7f), true, true);

        // Spin scripts
        formation.AddComponent<FormationSpinner>().spinSpeed = 30f;
        innerRing.AddComponent<FormationSpinner>().spinSpeed = -60f; // Counter-spin

        // Pulse and Fade script
        FormationAnimator fa = formation.AddComponent<FormationAnimator>();
        fa.duration = 4.5f;
        fa.baseColor = new Color(0.5f, 0f, 0.7f, 0.4f);
        fa.innerColor = new Color(0.8f, 0.2f, 1f, 0.7f);
        fa.innerRenderer = renInner;
    }

    #endregion

    #region Earthquake

    private void SpawnEarthquake(Vector3 origin, float intensity)
    {
        // 1. Trigger camera shake
        Camera mainCam = Camera.main;
        if (mainCam != null)
        {
            CameraShake shake = mainCam.gameObject.GetComponent<CameraShake>();
            if (shake == null)
            {
                shake = mainCam.gameObject.AddComponent<CameraShake>();
            }
            shake.duration = 1.0f;
            shake.magnitude = 0.25f * intensity;
        }

        // 2. Spawn rising rock chunks
        for (int i = 0; i < 8; i++)
        {
            GameObject rock = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rock.name = "EarthquakeDebris";
            
            // Random offset on horizontal ground plane
            Vector3 rockOffset = new Vector3(Random.Range(-4f, 4f), -1.8f, Random.Range(1f, 6f));
            rock.transform.position = origin + rockOffset;
            rock.transform.localScale = Vector3.one * Random.Range(0.4f, 0.9f) * intensity;
            rock.transform.rotation = Random.rotation;

            Renderer ren = rock.GetComponent<Renderer>();
            // Earthy brownish-gold material
            ren.material = CreateSpellMaterial(new Color(0.45f, 0.25f, 0.08f, 1.0f), false, false);
            ren.material.EnableKeyword("_EMISSION");
            ren.material.SetColor("_EmissionColor", new Color(0.7f, 0.4f, 0.1f) * 0.5f); // faint orange magma cracks

            RockPhysicSim rps = rock.AddComponent<RockPhysicSim>();
            rps.launchForce = Random.Range(4f, 8f);
        }
    }

    #endregion
}

#region Helper Components (Procedural Behaviors)

/// <summary>
/// Controls linear movement, spin, and trail burst for flying projectile spells like Fireballs and Energy Slashes.
/// </summary>
public class ProjectileMovement : MonoBehaviour
{
    public Vector3 direction = Vector3.forward;
    public float speed = 15f;
    public float lifeTime = 2f;
    public Vector3 spinVector = Vector3.zero;
    public Color burstColor = Color.white;

    private void Update()
    {
        transform.Translate(direction * speed * Time.deltaTime, Space.World);
        if (spinVector != Vector3.zero)
        {
            transform.Rotate(spinVector * Time.deltaTime, Space.Self);
        }

        lifeTime -= Time.deltaTime;
        if (lifeTime <= 0)
        {
            Explode();
        }
    }

    private void Explode()
    {
        // Procedurally spawn explosion particles using temporary tiny spheres
        GameObject expContainer = new GameObject("SpellExplosion");
        expContainer.transform.position = transform.position;

        for (int i = 0; i < 15; i++)
        {
            GameObject spark = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            spark.transform.position = transform.position;
            spark.transform.localScale = Vector3.one * Random.Range(0.1f, 0.3f);
            
            if (spark.TryGetComponent<Collider>(out Collider col)) Destroy(col);
            
            Renderer ren = spark.GetComponent<Renderer>();
            Material mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            if (mat.shader == null) mat.shader = Shader.Find("Standard");
            mat.SetColor("_BaseColor", burstColor);
            mat.EnableKeyword("_EMISSION");
            mat.SetColor("_EmissionColor", burstColor * 3f);
            ren.material = mat;

            // Add simple force movement outwards
            spark.AddComponent<SparkBehavior>().velocity = Random.insideUnitSphere * Random.Range(6f, 12f);
            Destroy(spark, 0.6f);
        }

        Destroy(expContainer, 0.8f);
        Destroy(gameObject);
    }
}

/// <summary>
/// Moves spark debris from projectile impact.
/// </summary>
public class SparkBehavior : MonoBehaviour
{
    public Vector3 velocity;
    private void Update()
    {
        transform.position += velocity * Time.deltaTime;
        velocity = Vector3.Lerp(velocity, Vector3.zero, Time.deltaTime * 3f); // friction
        transform.localScale = Vector3.Lerp(transform.localScale, Vector3.zero, Time.deltaTime * 4f); // shrink
    }
}

/// <summary>
/// Animates the scale and fading of defensive barrier shields.
/// </summary>
public class ShieldAnimator : MonoBehaviour
{
    public Vector3 targetScale;
    public float duration;
    public Light lightComponent;
    public Color shieldColor;

    private float elapsed = 0f;
    private Material shieldMat;

    private void Start()
    {
        shieldMat = GetComponent<Renderer>().material;
    }

    private void Update()
    {
        elapsed += Time.deltaTime;
        float percent = elapsed / duration;

        if (percent <= 0.15f) // Quick scale up
        {
            float t = percent / 0.15f;
            transform.localScale = Vector3.Lerp(Vector3.zero, targetScale, t);
        }
        else if (percent >= 0.8f) // Fade out
        {
            float t = (percent - 0.8f) / 0.2f;
            Color c = Color.Lerp(shieldColor, new Color(shieldColor.r, shieldColor.g, shieldColor.b, 0f), t);
            shieldMat.SetColor("_BaseColor", c);
            shieldMat.SetColor("_EmissionColor", c * 2f);
            if (lightComponent != null) lightComponent.intensity = Mathf.Lerp(2f, 0f, t);
        }

        if (percent >= 1f)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Animates wood-Qi healing cylinders rising and scaling out.
/// </summary>
public class RisingRing : MonoBehaviour
{
    public float speed;
    public float scaleSpeed;
    public float delay;
    public float maxHeight;
    public Color baseColor;

    private float elapsed = 0f;
    private Material ringMat;

    private void Start()
    {
        ringMat = GetComponent<Renderer>().material;
        // Make initially invisible
        Color invisible = baseColor;
        invisible.a = 0f;
        ringMat.SetColor("_BaseColor", invisible);
        ringMat.SetColor("_EmissionColor", invisible);
    }

    private void Update()
    {
        if (delay > 0)
        {
            delay -= Time.deltaTime;
            return;
        }

        elapsed += Time.deltaTime;
        transform.Translate(Vector3.up * speed * Time.deltaTime, Space.World);
        transform.localScale += new Vector3(scaleSpeed, 0f, scaleSpeed) * Time.deltaTime;

        // Fade calculation
        float alpha = 1f - (transform.localPosition.y / maxHeight);
        alpha = Mathf.Clamp01(alpha);
        
        Color c = baseColor;
        c.a = alpha * 0.7f;
        ringMat.SetColor("_BaseColor", c);
        ringMat.SetColor("_EmissionColor", c * 3f);

        if (alpha <= 0.05f || elapsed > 1.8f)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Generates and animates jagged lines for heavenly lightning strikes.
/// </summary>
public class LightningAnimator : MonoBehaviour
{
    public Vector3 startPoint;
    public Vector3 endPoint;
    public float intensity;

    private LineRenderer lr;
    private float lifeTime = 0.25f;
    private int segmentCount = 10;
    private List<Vector3> points = new List<Vector3>();

    private void Start()
    {
        lr = GetComponent<LineRenderer>();
        GenerateLightningPath();
    }

    private void GenerateLightningPath()
    {
        points.Clear();
        points.Add(startPoint);

        Vector3 dir = endPoint - startPoint;
        float segmentLength = dir.magnitude / segmentCount;

        for (int i = 1; i < segmentCount; i++)
        {
            float ratio = (float)i / segmentCount;
            Vector3 midPoint = startPoint + dir * ratio;
            // Add jitter perpendicular to trajectory
            Vector3 perp = Vector3.Cross(dir, Random.onUnitSphere).normalized;
            midPoint += perp * Random.Range(-0.8f, 0.8f) * (1.0f - ratio); // Less jitter near ground
            points.Add(midPoint);
        }

        points.Add(endPoint);
        lr.positionCount = points.Count;
        lr.SetPositions(points.ToArray());
    }

    private void Update()
    {
        lifeTime -= Time.deltaTime;
        
        // Rapid flicker effect
        if (Time.frameCount % 2 == 0)
        {
            GenerateLightningPath();
        }

        if (lifeTime <= 0)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Animates gold aura expand wave.
/// </summary>
public class AuraShockwave : MonoBehaviour
{
    public float expandSpeed;
    public float duration;
    public Color baseColor;
    public Light lightComponent;

    private float elapsed = 0f;
    private Material auraMat;

    private void Start()
    {
        auraMat = GetComponent<Renderer>().material;
    }

    private void Update()
    {
        elapsed += Time.deltaTime;
        float percent = elapsed / duration;

        // Expand
        transform.localScale += new Vector3(expandSpeed, 0f, expandSpeed) * Time.deltaTime;

        // Fade
        Color c = baseColor;
        c.a = Mathf.Lerp(baseColor.a, 0f, percent);
        auraMat.SetColor("_BaseColor", c);
        auraMat.SetColor("_EmissionColor", c * 3f);

        if (lightComponent != null)
        {
            lightComponent.intensity = Mathf.Lerp(3f, 0f, percent);
        }

        if (percent >= 1f)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Spirals glowing dragon spheres upwards.
/// </summary>
public class DragonCoil : MonoBehaviour
{
    public Transform parentCore;
    public float spinSpeed;
    public float verticalSpeed;
    public float radius;
    public float delay;

    private float angle = 0f;
    private float height = 0f;

    private void Update()
    {
        if (delay > 0)
        {
            delay -= Time.deltaTime;
            return;
        }

        if (parentCore == null)
        {
            Destroy(gameObject);
            return;
        }

        angle += spinSpeed * Time.deltaTime;
        height += verticalSpeed * Time.deltaTime;

        // Spiral diameter shrinks as it reaches the peak
        float currentRadius = radius * Mathf.Max(0.1f, 1f - (height / 8f));
        
        float x = Mathf.Cos(angle * Mathf.Deg2Rad) * currentRadius;
        float z = Mathf.Sin(angle * Mathf.Deg2Rad) * currentRadius;

        transform.position = parentCore.position + new Vector3(x, height - 1.5f, z);

        if (height > 10f)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Simple rotation script for formation rings.
/// </summary>
public class FormationSpinner : MonoBehaviour
{
    public float spinSpeed;
    private void Update()
    {
        transform.Rotate(0f, spinSpeed * Time.deltaTime, 0f, Space.Self);
    }
}

/// <summary>
/// Fades out the Magic Formation array.
/// </summary>
public class FormationAnimator : MonoBehaviour
{
    public float duration;
    public Color baseColor;
    public Color innerColor;
    public Renderer innerRenderer;

    private float elapsed = 0f;
    private Material mainMat;
    private Material innerMat;

    private void Start()
    {
        mainMat = GetComponent<Renderer>().material;
        if (innerRenderer != null) innerMat = innerRenderer.material;
    }

    private void Update()
    {
        elapsed += Time.deltaTime;
        float percent = elapsed / duration;

        if (percent >= 0.75f) // Fade last 25%
        {
            float t = (percent - 0.75f) / 0.25f;
            Color cMain = Color.Lerp(baseColor, new Color(baseColor.r, baseColor.g, baseColor.b, 0f), t);
            mainMat.SetColor("_BaseColor", cMain);

            if (innerMat != null)
            {
                Color cInner = Color.Lerp(innerColor, new Color(innerColor.r, innerColor.g, innerColor.b, 0f), t);
                innerMat.SetColor("_BaseColor", cInner);
                innerMat.SetColor("_EmissionColor", cInner * 2f);
            }
        }

        if (percent >= 1f)
        {
            Destroy(gameObject);
        }
    }
}

/// <summary>
/// Screenshake script applied temporarily to the Main Camera.
/// </summary>
public class CameraShake : MonoBehaviour
{
    public float duration = 1.0f;
    public float magnitude = 0.2f;

    private Vector3 originalPos;

    private void OnEnable()
    {
        originalPos = transform.localPosition;
        StartCoroutine(Shake());
    }

    private IEnumerator Shake()
    {
        float elapsed = 0.0f;
        while (elapsed < duration)
        {
            float x = Random.Range(-1f, 1f) * magnitude;
            float y = Random.Range(-1f, 1f) * magnitude;
            
            transform.localPosition = originalPos + new Vector3(x, y, 0f);
            elapsed += Time.deltaTime;
            yield return null;
        }

        transform.localPosition = originalPos;
    }
}

/// <summary>
/// Launches debris blocks upward with simple custom gravity simulation.
/// </summary>
public class RockPhysicSim : MonoBehaviour
{
    public float launchForce;
    private float gravity = -9.8f;
    private Vector3 velocity;

    private void Start()
    {
        // Launch up and outward
        velocity = new Vector3(Random.Range(-2f, 2f), launchForce, Random.Range(-2f, 2f));
        // Rotate randomly
        transform.rotation = Random.rotation;
    }

    private void Update()
    {
        velocity.y += gravity * Time.deltaTime;
        transform.position += velocity * Time.deltaTime;
        
        // Spin rock
        transform.Rotate(50f * Time.deltaTime, 30f * Time.deltaTime, 0f);

        // Shrink & Destroy when falling too low
        if (velocity.y < 0)
        {
            transform.localScale = Vector3.Lerp(transform.localScale, Vector3.zero, Time.deltaTime * 3f);
            if (transform.localScale.magnitude < 0.05f)
            {
                Destroy(gameObject);
            }
        }
    }
}

#endregion
