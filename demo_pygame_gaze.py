"""demo_pygame_gaze.py

Simple Pygame demo that exercises gaze-based camera control.

Behavior:
- Tries to import and use `EyeTracker` and `Camera` from `gaze_camera_embedded.py` (or `gaze_camera_control.py`).
- If webcam / mediapipe / PyOpenGL aren't available or webcam can't be opened, falls back to a mouse-driven simulation.

Run: python demo_pygame_gaze.py
"""
import sys
import time
import math
import pygame
from pygame.locals import *

# Try to import the project's gaze classes. If that fails, we'll simulate gaze with the mouse.
USE_REAL_GAZE = False
try:
    # Prefer embedded version if present
    from gaze_camera_embedded import EyeTracker, Camera
    USE_REAL_GAZE = True
except Exception:
    try:
        from gaze_camera_control import EyeTracker, Camera
        USE_REAL_GAZE = True
    except Exception:
        EyeTracker = None
        Camera = None

import cv2

WINDOW_SIZE = (800, 600)

class DemoApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Gaze Demo — Webcam or Mouse Simulation")
        self.clock = pygame.time.Clock()
        self.running = True

        # Camera-like state (visualised)
        self.camera = Camera() if Camera else None

        # Gaze source
        self.use_webcam = False
        self.cap = None
        self.tracker = None

        if USE_REAL_GAZE and EyeTracker is not None:
            try:
                self.tracker = EyeTracker()
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if self.cap is None or not self.cap.isOpened():
                    raise RuntimeError("Webcam not available")
                self.use_webcam = True
                print("Using real webcam + Mediapipe gaze (if installed)")
            except Exception as e:
                print("Falling back to mouse simulation (webcam unavailable or import failed):", e)
                self.cleanup_cam()

        else:
            print("Mediapipe/OpenGL imports not available — using mouse simulation")

        # store last webcam frame and gaze for rendering
        self.last_frame = None
        self.last_gaze = (None, None)

    def cleanup_cam(self):
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        self.cap = None
        self.tracker = None
        self.use_webcam = False
        self.last_frame = None
        self.last_gaze = (None, None)

    def get_gaze(self):
        """Return (gaze_x, gaze_y) in normalized 0..1 coordinates, or (None, None) if unavailable."""
        if self.use_webcam and self.tracker and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                # webcam failed — fallback
                self.cleanup_cam()
                return None, None
            try:
                gx, gy = self.tracker.get_gaze_coordinates(frame)
                # store for rendering
                self.last_frame = frame.copy()
                self.last_gaze = (gx, gy)
                return gx, gy
            except Exception:
                return None, None

        # Mouse simulation: map mouse position inside window to 0..1
        mx, my = pygame.mouse.get_pos()
        gx = mx / WINDOW_SIZE[0]
        gy = my / WINDOW_SIZE[1]
        # clear any webcam preview when using mouse sim
        self.last_frame = None
        self.last_gaze = (None, None)
        return gx, gy

    def draw_scene(self):
        # Background
        self.screen.fill((30, 30, 40))

        # Draw some reference boxes that appear to move when camera rotates
        if self.camera:
            yaw = self.camera.yaw
            pitch = self.camera.pitch
        else:
            yaw = 0
            pitch = 0

        cx, cy = WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2

        # Parallax boxes
        positions = [(-200, 0, (200, 100)), (-80, -60, (120, 80)), (120, 40, (140, 110)), (260, -20, (160, 140))]
        for base_x, base_y, size in positions:
            # Shift based on yaw/pitch to simulate camera rotation
            shift_x = int((yaw / 60.0) * 200)
            shift_y = int((pitch / 60.0) * 150)
            rect_x = cx + base_x - shift_x
            rect_y = cy + base_y - shift_y
            pygame.draw.rect(self.screen, (70, 130, 180), (rect_x, rect_y, size[0], size[1]), border_radius=8)

        # Draw center crosshair
        pygame.draw.line(self.screen, (0, 255, 0), (cx - 12, cy), (cx + 12, cy), 2)
        pygame.draw.line(self.screen, (0, 255, 0), (cx, cy - 12), (cx, cy + 12), 2)

        # HUD text
        font = pygame.font.Font(None, 28)
        if self.camera:
            txt = f"Yaw: {self.camera.yaw:.1f}°  Pitch: {self.camera.pitch:.1f}°"
        else:
            txt = "Simulation: Mouse controls gaze (move mouse)"
        surf = font.render(txt, True, (220, 220, 220))
        self.screen.blit(surf, (10, 10))

        # Draw webcam preview in top-right if we have a recent frame
        if self.last_frame is not None:
            try:
                display_w, display_h = 240, 180
                frame = cv2.resize(self.last_frame, (display_w, display_h))

                # draw gaze marker onto frame if available
                gx, gy = self.last_gaze
                if gx is not None and gy is not None:
                    px = int(gx * display_w)
                    py = int(gy * display_h)
                    # draw marker (BGR)
                    cv2.circle(frame, (px, py), 6, (0, 255, 0), 2)

                # convert BGR->RGB for pygame
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_surface = pygame.image.frombuffer(frame_rgb.tobytes(), (display_w, display_h), 'RGB')

                margin = 12
                x_pos = WINDOW_SIZE[0] - display_w - margin
                y_pos = margin
                # draw a background rect
                pygame.draw.rect(self.screen, (10, 10, 10), (x_pos-3, y_pos-3, display_w+6, display_h+6))
                self.screen.blit(frame_surface, (x_pos, y_pos))
            except Exception:
                # ignore preview rendering errors
                pass

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.running = False
                    elif event.key == K_w and self.use_webcam:
                        # toggle webcam
                        self.use_webcam = not self.use_webcam

            # Acquire gaze and update camera
            gx, gy = self.get_gaze()
            if gx is not None and gy is not None:
                if self.camera:
                    self.camera.update_from_gaze(gx, gy)
                else:
                    # When no Camera class available, we still show raw positions via pseudo values
                    pass

            # Draw
            self.draw_scene()
            pygame.display.flip()
            self.clock.tick(60)

        # cleanup
        self.cleanup_cam()
        pygame.quit()


if __name__ == '__main__':
    app = DemoApp()
    app.run()
