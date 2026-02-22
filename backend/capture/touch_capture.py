import tkinter as tk
import json
import os
import time
import sys

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.capture.sequence_buffer import SequenceBuffer

DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
VALID_SPEEDS = ["slow", "medium", "fast"]

class TouchCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SymbiotixEngine - Touch Gesture Capture")
        self.root.geometry("800x600")

        # UI Setup
        self.header = tk.Label(root, text="Draw Gesture. Middle-click to Save. Right-click to Clear.", font=("Helvetica", 12))
        self.header.pack(pady=5)

        self.canvas_width = 800
        self.canvas_height = 500
        self.canvas = tk.Canvas(root, bg="white", width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack()

        # Input fields
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=5)

        tk.Label(self.control_frame, text="User:").grid(row=0, column=0, padx=5)
        self.username_var = tk.StringVar(value="touch_user")
        tk.Entry(self.control_frame, textvariable=self.username_var, width=15).grid(row=0, column=1, padx=5)

        tk.Label(self.control_frame, text="Gesture:").grid(row=0, column=2, padx=5)
        self.gesture_var = tk.StringVar(value="swipe")
        tk.Entry(self.control_frame, textvariable=self.gesture_var, width=15).grid(row=0, column=3, padx=5)

        tk.Label(self.control_frame, text="Speed:").grid(row=0, column=4, padx=5)
        self.speed_var = tk.StringVar(value="medium")
        tk.OptionMenu(self.control_frame, self.speed_var, *VALID_SPEEDS).grid(row=0, column=5, padx=5)

        # Buffer
        self.buffer = SequenceBuffer()
        self.is_recording = False
        self.last_point = None

        # Bindings
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)
        self.canvas.bind("<Button-2>", self.save_recording)  # Middle click to save
        self.canvas.bind("<Button-3>", self.clear_canvas)    # Right click to clear

    def start_draw(self, event):
        self.is_recording = True
        self.buffer.clear()
        self.canvas.delete("all")
        self.last_point = (event.x, event.y)
        self.add_point(event.x, event.y)

    def draw(self, event):
        if self.is_recording:
            # Draw line
            if self.last_point:
                self.canvas.create_line(self.last_point[0], self.last_point[1], event.x, event.y, fill="black", width=3)
            self.last_point = (event.x, event.y)
            self.add_point(event.x, event.y)

    def end_draw(self, event):
        self.is_recording = False
        self.last_point = None

    def add_point(self, x, y):
        # Normalize relative to canvas size
        norm_x = round(x / self.canvas_width, 6)
        norm_y = round(y / self.canvas_height, 6)
        
        frame_record = {
            "timestamp": round(time.time(), 4),
            "hand": "touch",
            "landmarks": [
                {"id": 0, "x": norm_x, "y": norm_y, "z": 0.0} # Representing the single touch point
            ]
        }
        self.buffer.add_frame(frame_record)

    def clear_canvas(self, event=None):
        self.canvas.delete("all")
        self.buffer.clear()

    def save_recording(self, event=None):
        if len(self.buffer) == 0:
            print("[WARN] No points to save.")
            return

        username = self.username_var.get().strip() or "unknown"
        gesture_name = self.gesture_var.get().strip() or "unknown"
        speed_label = self.speed_var.get()

        output_dir = os.path.join(DATA_RAW_DIR, username, gesture_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp_str = str(int(time.time()))
        filename = f"touch_{speed_label}_{timestamp_str}.json"
        filepath = os.path.join(output_dir, filename)

        output_payload = {
            "metadata": {
                "username": username,
                "gesture_name": gesture_name,
                "hand_used": "touch",
                "speed_label": speed_label,
                "total_frames": len(self.buffer),
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "input_type": "touchscreen"
            },
            "frames": self.buffer.get_sequence(),
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_payload, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Saved touch recording to: {filepath}")
            self.clear_canvas()
        except OSError as e:
            print(f"[ERROR] Failed to save touch recording: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TouchCaptureApp(root)
    root.mainloop()
