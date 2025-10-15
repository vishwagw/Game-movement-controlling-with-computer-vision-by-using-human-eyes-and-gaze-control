# Gaze Camera Control — Demo

This workspace contains a gaze-based camera control prototype and a small Pygame demo harness.

Files:
- `gaze_camera_embedded.py` — Full prototype that uses Mediapipe + OpenGL to render a 3D scene and control a camera with gaze.
- `gaze_camera_control.py` — Alternate copy of the prototype.
- `demo_pygame_gaze.py` — Lightweight Pygame demo that uses the EyeTracker/Camera classes when available; otherwise falls back to a mouse-driven simulation.
- `requirements.txt` — Suggested Python packages.

Quick start (Windows PowerShell):

```powershell
python -m pip install -r requirements.txt
python demo_pygame_gaze.py
```

Notes:
- If you have a webcam and Mediapipe installed, the demo will attempt to use real gaze data. If the webcam or Mediapipe isn't available, the demo will map the mouse position to simulated gaze.
- The full prototypes (`gaze_camera_embedded.py` / `gaze_camera_control.py`) require PyOpenGL and will open an OpenGL window; the demo uses a simplified 2D view so you can test interactions without OpenGL.
- Controls:
  - Move mouse to simulate gaze (when webcam not available)
  - W toggles webcam usage (if webcam was successfully opened)
  - ESC to quit
