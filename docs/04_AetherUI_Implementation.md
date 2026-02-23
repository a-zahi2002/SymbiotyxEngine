# AetherUI: Visual Feedback Implementation

## Overview
AetherUI is the frontend component of the Symbiotix Engine, built in Unity. It serves to instantly visually validate to the user that their physical gestures have been accurately perceived and mapped by the system.

## The GestureOrb
The primary feedback mechanism currently implemented is the **GestureOrb**. It is a dynamic 3D object that heavily reacts to the raw intensity data streamed from the backend.

### `OrbEffects.cs`
This script translates abstract JSON data into rich visual effects (VFX) and physical transformations.

#### 1. Spatial Transformation
Gestures are not merely logged; they are mapped to physical 3D movements corresponding to their semantic meaning.
- **Swipes (`swipe_left`, `swipe_right`):** The orb translates along the X-axis (`Vector3.left` / `right`).
- **Rotations (`rotate_cw`, `rotate_ccw`):** The orb multiplies its `Quaternion` by 45 degrees over the Y-axis.
- **Zooms (`zoom_in`, `zoom_out`):** The orb pushes forward or pulls backward along the Z-axis, simulating depth interaction.
- **Tracking:** While the hand is merely present, the baseline scale of the orb gently pulses based on proximal distance from the camera.
- **Idle:** When the hand leaves the frame, the orb snaps back to its origin coordinates.
All physical changes are smoothed via crisp `Mathf.Lerp` functions to eliminate jitter from raw tracking data.

#### 2. Visual Effects (VFX)
To make the interface feel organic, several automated Unity component systems are hooked into the tracking intensity:
- **HDR Emission:** As the tracking intensity rises (hand gets closer), the Orb's material color dynamically interpolates from a cool blue into a hot pink/red. Furthermore, the property block adjusts the `_EmissionColor` to cause the material to literally "glow" brighter in the scene using Unity's post-processing stack.
- **Trail Renderer:** A `TrailRenderer` traces the path of the orb as it undergoes spatial transformation. Its width naturally tapers based on the current tracking intensity.
- **Particle System:** To emphasize the discrete completion of a gesture, a `ParticleSystem` is utilized. When a final "Gesture Complete" command is received with a high intensity spike (e.g., `intensity > 1.5`), an immediate burst emission of localized particles is triggered, matching the orb's interpolating color.

### Component Automation
`OrbEffects.cs` uses defensive programming paradigms. If it is attached to a GameObject that lacks a `TrailRenderer` or `ParticleSystem`, it will automatically spawn, parent, and fully configure these components at Runtime. This creates a purely drag-and-drop developer experience.
