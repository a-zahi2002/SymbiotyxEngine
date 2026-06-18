using UnityEngine;
using NativeWebSocket;
using System;

/// <summary>
/// Represents a command sent from the backend to Unity.
/// </summary>
[Serializable]
public class GestureCommand
{
    public string command;
    public float intensity;
    public string gesture;
    public string dynamic_gesture;
    public string rune;
    public string spell;
    public string state;
    public float velocity;
    public float confidence;
    public float hand_x;
    public float hand_y;
    public float hand_z;
    public bool has_hand;
}

/// <summary>
/// Receives commands from backend WebSocket server and forwards intensity to OrbEffects.
/// 
/// SETUP: Attach this script to any GameObject in your scene.
/// It will automatically find the "GestureOrb" by name and add OrbEffects if missing.
/// </summary>
public class CommandReceiver : MonoBehaviour
{
    private WebSocket websocket;

    [Header("Orb Settings")]
    [Tooltip("Drag your GestureOrb here, or leave empty to auto-find by name 'GestureOrb'.")]
    public GameObject gestureOrb;

    private OrbEffects orbEffects;

    [Header("Connection Settings")]
    [Tooltip("Backend WebSocket URL. Default: ws://localhost:8000/ws")]
    public string backendUrl = "ws://localhost:8000/ws";

    [Tooltip("Seconds between reconnection attempts if connection fails.")]
    public float reconnectDelay = 3f;

    private bool isConnecting = false;

    void Awake()
    {
        // Prevent Unity from freezing when the Python webcam window is focused
        Application.runInBackground = true;
        
        FindAndSetupOrb();
    }

    /// <summary>
    /// Finds the GestureOrb and ensures OrbEffects is attached.
    /// </summary>
    private void FindAndSetupOrb()
    {
        // Step 1: Find the GestureOrb if not assigned via Inspector
        if (gestureOrb == null)
        {
            Debug.Log("[CommandReceiver] gestureOrb not assigned in Inspector, searching by name...");
            gestureOrb = GameObject.Find("GestureOrb");

            if (gestureOrb == null)
            {
                Debug.LogError(
                    "[CommandReceiver] ❌ GestureOrb not found in scene!\n" +
                    "  → Make sure you have a GameObject named exactly 'GestureOrb' in your Hierarchy.\n" +
                    "  → Or drag-drop the orb into the 'Gesture Orb' field in the Inspector."
                );
                return;
            }

            Debug.Log("[CommandReceiver] ✅ Found GestureOrb by name: " + gestureOrb.name);
        }
        else
        {
            Debug.Log("[CommandReceiver] ✅ GestureOrb assigned via Inspector: " + gestureOrb.name);
        }

        // Step 2: Get or add the OrbEffects component
        orbEffects = gestureOrb.GetComponent<OrbEffects>();
        if (orbEffects == null)
        {
            Debug.LogWarning(
                "[CommandReceiver] ⚠ OrbEffects component not found on " + gestureOrb.name +
                ". Adding it automatically..."
            );
            orbEffects = gestureOrb.AddComponent<OrbEffects>();
            Debug.Log("[CommandReceiver] ✅ OrbEffects component added to " + gestureOrb.name);
        }
        else
        {
            Debug.Log("[CommandReceiver] ✅ OrbEffects component found on " + gestureOrb.name);
        }
    }

    async void Start()
    {
        if (gestureOrb == null)
        {
            Debug.LogError("[CommandReceiver] Cannot start WebSocket — GestureOrb is missing.");
            return;
        }

        await ConnectWebSocket();
    }

    private async System.Threading.Tasks.Task ConnectWebSocket()
    {
        if (isConnecting) return;
        isConnecting = true;

        Debug.Log("[CommandReceiver] Connecting to " + backendUrl + " ...");
        websocket = new WebSocket(backendUrl);

        websocket.OnOpen += () =>
        {
            if (this == null) return;
            Debug.Log("[CommandReceiver] ✅ Connected to backend at " + backendUrl);
            isConnecting = false;
        };

        websocket.OnError += (e) =>
        {
            if (this == null) return;
            Debug.LogError("[CommandReceiver] ❌ WebSocket Error: " + e);
            isConnecting = false;
        };

        websocket.OnClose += (e) =>
        {
            if (this == null) return;
            Debug.LogWarning("[CommandReceiver] ⚠ Connection closed. Will attempt reconnect in " + reconnectDelay + "s");
            isConnecting = false;
            Invoke(nameof(TryReconnect), reconnectDelay);
        };

        websocket.OnMessage += (bytes) =>
        {
            if (this == null) return;
            var message = System.Text.Encoding.UTF8.GetString(bytes);
            Debug.Log("[CommandReceiver] 📩 Received: " + message);

            try
            {
                GestureCommand cmd = JsonUtility.FromJson<GestureCommand>(message);
                HandleCommand(cmd);
            }
            catch (Exception ex)
            {
                Debug.LogError("[CommandReceiver] Failed to parse command: " + ex.Message);
            }
        };

        try
        {
            await websocket.Connect();
        }
        catch (Exception ex)
        {
            if (this == null) return;
            Debug.LogError("[CommandReceiver] ❌ Failed to connect: " + ex.Message);
            isConnecting = false;
            Invoke(nameof(TryReconnect), reconnectDelay);
        }
    }

    private async void TryReconnect()
    {
        Debug.Log("[CommandReceiver] Attempting reconnect...");
        await ConnectWebSocket();
    }

    void HandleCommand(GestureCommand cmd)
    {
        if (cmd == null)
        {
            Debug.LogWarning("[CommandReceiver] Received null command.");
            return;
        }

        if (gestureOrb == null)
        {
            Debug.LogError("[CommandReceiver] GestureOrb reference lost!");
            return;
        }

        Debug.Log($"[CommandReceiver] Command: '{cmd.command}' | Intensity: {cmd.intensity:F4} | Spell: '{cmd.spell}' | State: '{cmd.state}'");

        if (orbEffects != null)
        {
            orbEffects.HandleGesture(cmd);
        }
        else
        {
            Debug.LogError("[CommandReceiver] OrbEffects is null — cannot apply gesture effects!");
        }
    }

    void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        websocket?.DispatchMessageQueue();
#endif
    }

    private async void OnApplicationQuit()
    {
        if (websocket != null && websocket.State == WebSocketState.Open)
        {
            await websocket.Close();
        }
    }

    /// <summary>
    /// Editor button to test zoom manually (can be called from Inspector context menu).
    /// </summary>
    [ContextMenu("Test Zoom (Intensity 2.0)")]
    private void TestZoom()
    {
        if (orbEffects != null)
        {
            orbEffects.HandleGesture("zoom_in", 2.0f);
            Debug.Log("[CommandReceiver] Test zoom triggered with intensity 2.0");
        }
        else
        {
            Debug.LogError("[CommandReceiver] Cannot test — OrbEffects not found.");
        }
    }
}