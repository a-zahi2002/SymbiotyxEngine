using UnityEngine;

/// <summary>
/// Adds a slow ambient rotation to the GestureOrb when idle.
/// Stops rotating when the backend sends active gesture commands,
/// so the orb does NOT spin "on its own" during gesture control.
/// </summary>
public class OrbRotator : MonoBehaviour
{
    [Tooltip("Base rotation speed (degrees/second) when idle.")]
    public float rotationSpeed = 30f;

    [Tooltip("How many seconds after the last command before idle spin resumes.")]
    public float idleResumeDelay = 1.5f;

    [Tooltip("How fast to interpolate between active (0) and idle rotation speed.")]
    public float blendSpeed = 3f;

    // Time of last received gesture command
    private float lastCommandTime = -999f;
    private float currentRotationSpeed = 0f;

    /// <summary>
    /// Call this from CommandReceiver / OrbEffects whenever a non-idle
    /// gesture command is received, to suppress the idle spin.
    /// </summary>
    public void NotifyCommandReceived()
    {
        lastCommandTime = Time.time;
    }

    void Update()
    {
        // Determine whether we are "idle" (no recent command from backend)
        bool isIdle = (Time.time - lastCommandTime) > idleResumeDelay;

        // Smoothly blend toward target speed
        float targetSpeed = isIdle ? rotationSpeed : 0f;
        currentRotationSpeed = Mathf.Lerp(currentRotationSpeed, targetSpeed, Time.deltaTime * blendSpeed);

        // Apply rotation only if meaningfully spinning
        if (Mathf.Abs(currentRotationSpeed) > 0.1f)
        {
            transform.Rotate(Vector3.up * currentRotationSpeed * Time.deltaTime);
        }
    }
}