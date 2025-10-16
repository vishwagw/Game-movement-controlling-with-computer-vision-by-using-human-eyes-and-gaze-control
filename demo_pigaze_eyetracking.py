"""demo_pigaze_eyetracking.py

Demo that prefers a hardware eye tracker via PyGaze when available. If PyGaze is not present,
falls back to the Mediapipe-based EyeTracker (from this repo) and finally to mouse simulation.

The demo draws a simple 2D scene in Pygame. When using Mediapipe it will attempt to show the
webcam preview in the top-right corner with a gaze marker. When using PyGaze with a real
eye-tracker device, it maps the eye-tracker gaze to the window coordinates.

Run:
  python demo_pigaze_eyetracking.py

Note: PyGaze is not available via pip in a single package for all platforms; installation varies
by OS and hardware. This demo tries to import the standard `pygaze` package if available.
"""

import sys
import time
import pygame
import cv2
from pygame.locals import *

WINDOW_SIZE = (1024, 720)

# Try PyGaze first
USE_PYGAZE = False
try:
    import pygaze
    # Attempt to import common PyGaze classes (names differ across versions/hardware)
    from pygaze import libinput
    USE_PYGAZE = True
    print("PyGaze import succeeded — will attempt to use eye-tracker device")
except Exception:
    USE_PYGAZE = False

# If PyGaze not available, try repo's Mediapipe tracker
USE_MEDIAPIPE = False
try:
    from gaze_camera_embedded import EyeTracker
    USE_MEDIAPIPE = True
    print("Using Mediapipe EyeTracker from repository")
except Exception:
    try:
        from gaze_camera_control import EyeTracker
        USE_MEDIAPIPE = True
        print("Using Mediapipe EyeTracker from repository (alt)")
    except Exception:
        USE_MEDIAPIPE = False


class EyeSource:
    """Unified interface: start(), stop(), get_gaze() -> (gx, gy) normalized 0..1, or (None,None)."""
    def __init__(self):
        self.mode = 'mouse'
        self.pytracker = None
        self.mp_tracker = None
        self.cap = None
        self.last_frame = None

        if USE_PYGAZE:
            try:
                # Minimal attempt — different PyGaze setups require different code.
                # We'll try to use libinput.EyeTracker if present (not guaranteed).
                self.pytracker = libinput.EyeTracker()
                self.mode = 'pygaze'
            except Exception:
                self.pytracker = None

        if not self.pytracker and USE_MEDIAPIPE:
            try:
                self.mp_tracker = EyeTracker()
                # open webcam
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    raise RuntimeError('Webcam unavailable')
                self.mode = 'mediapipe'
            except Exception:
                # fallback to mouse
                self.mp_tracker = None
                if self.cap:
                    try:
                        self.cap.release()
                    except Exception:
                        pass

        print(f"EyeSource mode: {self.mode}")

    def start(self):
        # For PyGaze hardware you might need to call open() on the device — left as a TODO
        return

    def stop(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass

    def get_gaze(self):
        if self.mode == 'pygaze' and self.pytracker:
            try:
                # PyGaze API varies — we attempt common pattern where tracker.sample() returns x,y in pixels
                sample = self.pytracker.sample()
                if sample is None:
                    return None, None
                x, y = sample[0], sample[1]
                return x / WINDOW_SIZE[0], y / WINDOW_SIZE[1]
            except Exception:
                return None, None

        if self.mode == 'mediapipe' and self.mp_tracker and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                return None, None
            self.last_frame = frame.copy()
            try:
                gx, gy = self.mp_tracker.get_gaze_coordinates(frame)
                return gx, gy
            except Exception:
                return None, None

        # Mouse fallback
        mx, my = pygame.mouse.get_pos()
        return mx / WINDOW_SIZE[0], my / WINDOW_SIZE[1]


def draw_preview(surface, frame, gaze, size=(240, 180), margin=12):
    try:
        w, h = size
        frame_r = cv2.resize(frame, (w, h))
        gx, gy = gaze
        if gx is not None and gy is not None:
            px = int(gx * w)
            py = int(gy * h)
            cv2.circle(frame_r, (px, py), 6, (0, 255, 0), 2)
        frame_rgb = cv2.cvtColor(frame_r, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(frame_rgb.tobytes(), (w, h), 'RGB')
        x = WINDOW_SIZE[0] - w - margin
        y = margin
        pygame.draw.rect(surface, (10, 10, 10), (x-2, y-2, w+4, h+4))
        surface.blit(surf, (x, y))
    except Exception:
        pass


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('PyGaze / Mediapipe Eye-Tracking Demo')
    clock = pygame.time.Clock()

    eyes = EyeSource()
    running = True
    font = pygame.font.Font(None, 28)

    while running:
        for e in pygame.event.get():
            if e.type == QUIT:
                running = False
            elif e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    running = False

        gx, gy = eyes.get_gaze()

        # Draw scene
        screen.fill((28, 28, 38))
        cx, cy = WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2

        # Show a cursor where gaze maps
        if gx is not None and gy is not None:
            px = int(gx * WINDOW_SIZE[0])
            py = int(gy * WINDOW_SIZE[1])
            pygame.draw.circle(screen, (255, 200, 0), (px, py), 8)
            txt = f"Gaze: {gx:.3f}, {gy:.3f}  Mode: {eyes.mode}"
        else:
            txt = f"Gaze: None  Mode: {eyes.mode}"

        # Draw some reference elements to interact with gaze
        pygame.draw.rect(screen, (70, 120, 180), (cx-220, cy-80, 160, 120), border_radius=8)
        pygame.draw.rect(screen, (120, 160, 100), (cx+80, cy-60, 220, 100), border_radius=8)

        surf = font.render(txt, True, (220, 220, 220))
        screen.blit(surf, (10, 10))

        # If mediapipe mode, draw webcam preview
        if eyes.mode == 'mediapipe' and eyes.last_frame is not None:
            draw_preview(screen, eyes.last_frame, (gx, gy))

        pygame.display.flip()
        clock.tick(60)

    eyes.stop()
    pygame.quit()


if __name__ == '__main__':
    main()
