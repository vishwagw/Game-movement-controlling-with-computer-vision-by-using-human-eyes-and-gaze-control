"""shooter_demo.py

Simple eye-aim shooter demo.

Controls:
- Aim with eyes (Mediapipe if available) or mouse (fallback).
- Left-click to shoot.
- ESC to quit.

Dependencies: pygame, opencv-python, mediapipe (optional)
"""

import random
import math
import time
import pygame
import cv2
from pygame.locals import *

WINDOW_SIZE = (1024, 720)

# Try to import the repository's EyeTracker (mediapipe based)
USE_MEDIAPIPE = False
EyeTrackerClass = None
try:
    from gaze_camera_embedded import EyeTracker
    EyeTrackerClass = EyeTracker
    USE_MEDIAPIPE = True
except Exception:
    try:
        from gaze_camera_control import EyeTracker
        EyeTrackerClass = EyeTracker
        USE_MEDIAPIPE = True
    except Exception:
        USE_MEDIAPIPE = False


class AimSource:
    def __init__(self):
        self.mode = 'mouse'
        self.tracker = None
        self.cap = None
        self.last_frame = None

        if USE_MEDIAPIPE and EyeTrackerClass is not None:
            try:
                self.tracker = EyeTrackerClass()
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    raise RuntimeError('webcam not available')
                self.mode = 'mediapipe'
                print('Using Mediapipe EyeTracker for aim')
            except Exception as e:
                print('Mediapipe unavailable:', e)
                self.tracker = None
                if self.cap:
                    try:
                        self.cap.release()
                    except Exception:
                        pass

    def stop(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass

    def get_aim(self):
        """Return aim position in screen coordinates (x,y)."""
        if self.mode == 'mediapipe' and self.tracker and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                return None
            self.last_frame = frame.copy()
            try:
                gx, gy = self.tracker.get_gaze_coordinates(frame)
                if gx is None or gy is None:
                    return None
                sx = int(gx * WINDOW_SIZE[0])
                sy = int(gy * WINDOW_SIZE[1])
                return (sx, sy)
            except Exception:
                return None

        # Mouse fallback
        mx, my = pygame.mouse.get_pos()
        return (mx, my)


def draw_webcam_preview(surface, frame, gaze, size=(240, 180), margin=12):
    try:
        w, h = size
        small = cv2.resize(frame, (w, h))
        gx, gy = gaze
        if gx is not None and gy is not None:
            px = int(gx * w)
            py = int(gy * h)
            cv2.circle(small, (px, py), 6, (0, 255, 0), 2)
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(small_rgb.tobytes(), (w, h), 'RGB')
        x = WINDOW_SIZE[0] - w - margin
        y = margin
        pygame.draw.rect(surface, (10, 10, 10), (x-3, y-3, w+6, h+6))
        surface.blit(surf, (x, y))
    except Exception:
        pass


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


class Target:
    def __init__(self, screen_w, screen_h):
        self.w = screen_w
        self.h = screen_h
        self.radius = random.randint(18, 36)
        self.pos = (random.randint(self.radius, screen_w - self.radius), random.randint(self.radius + 80, screen_h - self.radius))
        self.color = (random.randint(80,255), random.randint(80,255), random.randint(80,255))

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, self.pos, self.radius)
        pygame.draw.circle(surf, (0,0,0), self.pos, self.radius, 2)

    def hit(self, point):
        return distance(self.pos, point) <= self.radius


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('Eye-Aim Shooter Demo')
    clock = pygame.time.Clock()

    aim = AimSource()
    targets = [Target(*WINDOW_SIZE) for _ in range(4)]
    score = 0
    shots = 0
    last_hit_time = 0

    font = pygame.font.Font(None, 32)
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == QUIT:
                running = False
            elif ev.type == KEYDOWN:
                if ev.key == K_ESCAPE:
                    running = False
            elif ev.type == MOUSEBUTTONDOWN:
                if ev.button == 1:  # left click => shoot
                    shots += 1
                    aim_pos = aim.get_aim()
                    if aim_pos is not None:
                        # check hits
                        for t in targets:
                            if t.hit(aim_pos):
                                score += 1
                                last_hit_time = time.time()
                                # respawn target
                                targets.remove(t)
                                targets.append(Target(*WINDOW_SIZE))
                                break

        aim_pos = aim.get_aim()

        # Drawing
        screen.fill((30, 34, 40))

        # draw HUD
        hud = font.render(f'Score: {score}   Shots: {shots}   Mode: {aim.mode}', True, (220,220,220))
        screen.blit(hud, (10, 10))

        # draw targets
        for t in targets:
            t.draw(screen)

        # draw aim reticle
        if aim_pos:
            pygame.draw.circle(screen, (255, 255, 0), aim_pos, 10, 3)
            # small inner dot
            pygame.draw.circle(screen, (255, 160, 0), aim_pos, 4)

        # if using mediapipe, show webcam preview with gaze marker
        if aim.mode == 'mediapipe' and aim.last_frame is not None:
            # compute gaze normalized for preview marker
            try:
                # retrieve last gaze normalized from tracker
                gx, gy = aim.tracker.get_gaze_coordinates(aim.last_frame)
            except Exception:
                gx, gy = (None, None)
            draw_webcam_preview(screen, aim.last_frame, (gx, gy))

        pygame.display.flip()
        clock.tick(60)

    aim.stop()
    pygame.quit()


if __name__ == '__main__':
    main()
