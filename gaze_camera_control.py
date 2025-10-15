import cv2
import mediapipe as mp
import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math

class EyeTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    def get_gaze_coordinates(self, frame):
        """Extract gaze coordinates from webcam frame"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return None, None
        
        face_landmarks = results.multi_face_landmarks[0]
        h, w = frame.shape[:2]
        
        # Get eye landmarks (iris centers)
        # Left iris: 468-473, Right iris: 473-478
        left_iris = face_landmarks.landmark[468]
        right_iris = face_landmarks.landmark[473]
        
        # Average both eyes for gaze direction
        gaze_x = (left_iris.x + right_iris.x) / 2
        gaze_y = (left_iris.y + right_iris.y) / 2
        
        return gaze_x, gaze_y

class Camera:
    def __init__(self):
        self.yaw = 0.0  # Horizontal rotation
        self.pitch = 0.0  # Vertical rotation
        self.smoothing = 0.15  # Lower = smoother but slower response
        self.sensitivity = 60.0  # Degrees of rotation at screen edge
        self.dead_zone = 0.2  # Center region with no movement
        
        # Smoothing buffers
        self.gaze_history_x = []
        self.gaze_history_y = []
        self.history_size = 5
        
    def update_from_gaze(self, gaze_x, gaze_y):
        """Update camera rotation based on gaze coordinates"""
        if gaze_x is None or gaze_y is None:
            return
        
        # Normalize to -1 to 1 range (center is 0)
        norm_x = (gaze_x - 0.5) * 2
        norm_y = (gaze_y - 0.5) * 2
        
        # Apply smoothing using moving average
        self.gaze_history_x.append(norm_x)
        self.gaze_history_y.append(norm_y)
        
        if len(self.gaze_history_x) > self.history_size:
            self.gaze_history_x.pop(0)
            self.gaze_history_y.pop(0)
        
        smooth_x = sum(self.gaze_history_x) / len(self.gaze_history_x)
        smooth_y = sum(self.gaze_history_y) / len(self.gaze_history_y)
        
        # Apply dead zone
        if abs(smooth_x) < self.dead_zone:
            smooth_x = 0
        else:
            # Scale after dead zone
            smooth_x = (smooth_x - np.sign(smooth_x) * self.dead_zone) / (1 - self.dead_zone)
            
        if abs(smooth_y) < self.dead_zone:
            smooth_y = 0
        else:
            smooth_y = (smooth_y - np.sign(smooth_y) * self.dead_zone) / (1 - self.dead_zone)
        
        # Calculate target rotation
        target_yaw = smooth_x * self.sensitivity
        target_pitch = -smooth_y * self.sensitivity  # Invert Y for natural feel
        
        # Clamp pitch to avoid gimbal lock
        target_pitch = max(-80, min(80, target_pitch))
        
        # Smooth interpolation to target
        self.yaw += (target_yaw - self.yaw) * self.smoothing
        self.pitch += (target_pitch - self.pitch) * self.smoothing
        
    def apply(self):
        """Apply camera transformations to OpenGL"""
        glRotatef(self.pitch, 1, 0, 0)
        glRotatef(self.yaw, 0, 1, 0)

class Game3D:
    def __init__(self):
        self.eye_tracker = EyeTracker()
        self.camera = Camera()
        self.cap = cv2.VideoCapture(0)
        
        # Initialize Pygame and OpenGL
        pygame.init()
        self.display = (1280, 720)
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Gaze-Based Camera Control - Look around with your eyes!")
        
        # OpenGL setup
        glEnable(GL_DEPTH_TEST)
        gluPerspective(45, (self.display[0] / self.display[1]), 0.1, 50.0)
        glTranslatef(0.0, 0.0, -10)
        
        self.running = True
        self.show_webcam = True
        
    def draw_grid_floor(self):
        """Draw a grid floor for reference"""
        glBegin(GL_LINES)
        glColor3f(0.3, 0.3, 0.3)
        
        for i in range(-10, 11):
            glVertex3f(i, -2, -10)
            glVertex3f(i, -2, 10)
            glVertex3f(-10, -2, i)
            glVertex3f(10, -2, i)
        glEnd()
        
    def draw_cube(self, x, y, z, size=1, color=(1, 0, 0)):
        """Draw a colored cube"""
        glPushMatrix()
        glTranslatef(x, y, z)
        
        vertices = [
            [1, 1, -1], [1, -1, -1], [-1, -1, -1], [-1, 1, -1],
            [1, 1, 1], [1, -1, 1], [-1, -1, 1], [-1, 1, 1]
        ]
        vertices = [[v[0]*size, v[1]*size, v[2]*size] for v in vertices]
        
        edges = [
            (0,1), (1,2), (2,3), (3,0),
            (4,5), (5,6), (6,7), (7,4),
            (0,4), (1,5), (2,6), (3,7)
        ]
        
        glColor3f(*color)
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        
        glPopMatrix()
        
    def draw_scene(self):
        """Draw the 3D scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glPushMatrix()
        self.camera.apply()
        
        # Draw floor grid
        self.draw_grid_floor()
        
        # Draw multiple cubes in different positions
        self.draw_cube(0, 0, 0, 1, (1, 0, 0))  # Red center
        self.draw_cube(-3, 0, 0, 0.7, (0, 1, 0))  # Green left
        self.draw_cube(3, 0, 0, 0.7, (0, 0, 1))  # Blue right
        self.draw_cube(0, 0, -3, 0.7, (1, 1, 0))  # Yellow back
        self.draw_cube(0, 0, 3, 0.7, (1, 0, 1))  # Magenta front
        self.draw_cube(0, 2, 0, 0.5, (0, 1, 1))  # Cyan top
        
        glPopMatrix()
        
    def draw_hud(self):
        """Draw 2D HUD overlay with info"""
        # Switch to 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.display[0], self.display[1], 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        
        # Draw crosshair in center
        glColor3f(0, 1, 0)
        glBegin(GL_LINES)
        cx, cy = self.display[0]//2, self.display[1]//2
        glVertex2f(cx - 10, cy)
        glVertex2f(cx + 10, cy)
        glVertex2f(cx, cy - 10)
        glVertex2f(cx, cy + 10)
        glEnd()
        
        glEnable(GL_DEPTH_TEST)
        
        # Restore 3D rendering
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, 36)
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_w:
                        self.show_webcam = not self.show_webcam
                    elif event.key == pygame.K_UP:
                        self.camera.sensitivity += 5
                    elif event.key == pygame.K_DOWN:
                        self.camera.sensitivity = max(5, self.camera.sensitivity - 5)
                    elif event.key == pygame.K_EQUALS:
                        self.camera.smoothing = min(0.5, self.camera.smoothing + 0.05)
                    elif event.key == pygame.K_MINUS:
                        self.camera.smoothing = max(0.05, self.camera.smoothing - 0.05)
            
            # Get webcam frame and track gaze
            ret, frame = self.cap.read()
            if ret:
                gaze_x, gaze_y = self.eye_tracker.get_gaze_coordinates(frame)
                self.camera.update_from_gaze(gaze_x, gaze_y)
                
                # Show webcam feed
                if self.show_webcam:
                    # Draw gaze indicator on webcam feed
                    if gaze_x is not None and gaze_y is not None:
                        h, w = frame.shape[:2]
                        px, py = int(gaze_x * w), int(gaze_y * h)
                        cv2.circle(frame, (px, py), 10, (0, 255, 0), 2)
                    
                    cv2.imshow('Webcam - Eye Tracking', frame)
            
            # Render 3D scene
            self.draw_scene()
            self.draw_hud()
            
            # Draw text info on Pygame surface
            info_surface = pygame.Surface((400, 150))
            info_surface.set_alpha(200)
            info_surface.fill((0, 0, 0))
            
            texts = [
                f"Yaw: {self.camera.yaw:.1f}°  Pitch: {self.camera.pitch:.1f}°",
                f"Sensitivity: {self.camera.sensitivity:.0f} (↑/↓)",
                f"Smoothing: {self.camera.smoothing:.2f} (+/-)",
                f"Press W: Toggle Webcam | ESC: Quit"
            ]
            
            y_offset = 10
            for text in texts:
                text_surface = font.render(text, True, (255, 255, 255))
                info_surface.blit(text_surface, (10, y_offset))
                y_offset += 30
            
            # Convert pygame surface to OpenGL texture and draw
            text_data = pygame.image.tostring(info_surface, "RGBA", True)
            glWindowPos2d(10, 10)
            glDrawPixels(info_surface.get_width(), info_surface.get_height(), 
                        GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            pygame.display.flip()
            clock.tick(60)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()

if __name__ == "__main__":
    print("=== Gaze-Based Camera Control Prototype ===")
    print("\nInstructions:")
    print("1. Look around with your eyes to rotate the camera")
    print("2. The center area is a 'dead zone' - no movement")
    print("3. Look towards screen edges to rotate camera")
    print("\nControls:")
    print("  W - Toggle webcam window")
    print("  ↑/↓ - Adjust sensitivity")
    print("  +/- - Adjust smoothing")
    print("  ESC - Quit")
    print("\nStarting application...")
    
    try:
        game = Game3D()
        game.run()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have installed:")
        print("  pip install opencv-python mediapipe pygame PyOpenGL")
