#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# SM64 Mini Engine (Ursina-only build) - Fixed Version
# -----------------------------------------------------------------------------
# Clean Ursina version — no Panda3D/OpenGL config required.
#  • 600x400 window
#  • Mario + Lakitu camera logic (yaw sync)
#  • Safe macOS run without PRC tweaks
#  • Fixed: robust yaw-rotated movement; normalize after non-zero check
# -----------------------------------------------------------------------------

from ursina import *
import math, random, os

# macOS GLSL compatibility tweak (optional; noop on most setups)
if hasattr(os, "uname") and os.uname().sysname == 'Darwin':
    os.environ['PANDORA_GLSL_VERSION'] = '120'  # Fallback to GLSL 1.20 for legacy support

# -----------------------------------------------------------------------------
# Window / App Setup
# -----------------------------------------------------------------------------
app = Ursina()
window.title = "SM64 Mini Engine – Ursina Edition"
window.size = (600, 400)
window.color = color.rgb(135, 206, 235)
window.borderless = False
window.fullscreen = False

try:
    window.icon = None
except Exception:
    pass

# -----------------------------------------------------------------------------
# Simple Lakitu-like Camera
# -----------------------------------------------------------------------------
class LakituCamera(Entity):
    def __init__(self, target, distance=6.5, yaw=0.0, pitch=18.0):
        super().__init__()
        self.target = target
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self.min_pitch, self.max_pitch = -60, 60
        self.smooth = 6

    def update(self):
        # Orbit with right mouse drag
        if held_keys['right mouse']:
            self.yaw   -= mouse.velocity[0] * 120
            self.pitch -= mouse.velocity[1] * 120
            self.pitch = clamp(self.pitch, self.min_pitch, self.max_pitch)

        # Compute desired position
        target_pos = self.target.world_position
        cam_offset = Vec3(
            math.sin(math.radians(self.yaw)) * self.distance,
            math.sin(math.radians(self.pitch)) * self.distance * 0.6,
            math.cos(math.radians(self.yaw)) * self.distance
        )
        desired_cam = target_pos + cam_offset

        camera.world_position = lerp(camera.world_position, desired_cam, min(time.dt * self.smooth, 1))
        camera.look_at(target_pos)

        # Expose yaw for player movement (use explicit rotation_y)
        if 'camera_pivot' in globals():
            try:
                camera_pivot.rotation_y = self.yaw
            except Exception:
                pass

# -----------------------------------------------------------------------------
# Mario Entity (simple controller)
# -----------------------------------------------------------------------------
class Mario(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.red,
            scale_y=1.8,
            collider='box',
            **kwargs
        )
        self.grounded = True
        self.vel_y = 0.0

    def input_move_dir(self, cam_yaw: float) -> Vec3:
        # Local WASD intent
        x = (held_keys['d'] - held_keys['a'])
        z = (held_keys['w'] - held_keys['s'])
        if not x and not z:
            return Vec3(0, 0, 0)

        # Rotate around Y by camera yaw (right-handed; yaw in degrees)
        rad = math.radians(cam_yaw)
        world_x = x * math.cos(rad) + z * math.sin(rad)
        world_z = -x * math.sin(rad) + z * math.cos(rad)
        v = Vec3(world_x, 0, world_z)
        return v.normalized()

    def update(self):
        cam_yaw = getattr(globals().get('camera_pivot', object()), 'rotation_y', 0.0)
        wish = self.input_move_dir(cam_yaw)
        self.position += wish * time.dt * 5

        # Simple jump physics
        if self.grounded and held_keys['space']:
            self.vel_y = 7
            self.grounded = False

        self.y += self.vel_y * time.dt
        self.vel_y -= 18 * time.dt

        if self.y < 0:
            self.y = 0
            self.vel_y = 0
            self.grounded = True

# -----------------------------------------------------------------------------
# Scene Setup
# -----------------------------------------------------------------------------
ground = Entity(model='plane', scale=(40, 1, 40), color=color.green, collider='box')
player = Mario(position=(0, 1, 0))

camera_pivot = Entity()
lakitu = LakituCamera(target=player)

# Simple instructions overlay
Text(
    text='WASD move • Space jump • RMB orbit • Esc quit',
    origin=(-.5, .5),
    scale=.8,
    background=True
)

# -----------------------------------------------------------------------------
# Optional Fixed-Function Fallback (placeholder)
# -----------------------------------------------------------------------------
if os.environ.get('SM64_MINI_FORCE_FIXED') == '1':
    print("[WARN] Fixed-function fallback requested (no shader mode).")

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
def input(key):
    if key == 'escape':
        application.quit()

app.run()
