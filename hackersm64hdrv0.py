#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# SM64 Peach's Castle – N64 Accurate Tech Demo
# -----------------------------------------------------------------------------
# • Peach's Castle exterior with proper orientation and N64-style design
# • Dynamic HUD that properly scales with a 600×400 window
# • Small, clean text elements (no Ursina adornments)
# • Ursina-only (no Panda3D PRC tweaks), single file, PR-ready
# -----------------------------------------------------------------------------

from ursina import *
import math, random, os

# -----------------------------------------------------------------------------
# macOS GLSL fallback (only if needed on some macs with older GLSL paths)
# -----------------------------------------------------------------------------
if hasattr(os, "uname") and os.uname().sysname == "Darwin":
    os.environ["PANDORA_GLSL_VERSION"] = "120"

# -----------------------------------------------------------------------------
# PRE-INIT CLEANUP (must happen before Ursina() init)
# -----------------------------------------------------------------------------
from ursina import application, window
application.hotkeys = {}          # disable default hotkeys (e.g., F11, etc.)
application.pause_enabled = False # no pause menu

# Create the app
app = Ursina()

# -----------------------------------------------------------------------------
# WINDOW CONFIG
# -----------------------------------------------------------------------------
window.title = "Super Mario 64 – Peach's Castle"
window.size = (600, 400)
window.borderless = False
window.fullscreen = False
window.color = color.rgb(135, 206, 250)  # Sky blue

# Turn off Ursina UI adornments (guard attributes to avoid crashes across versions)
for attr in ("exit_button", "cog_button", "fps_counter"):
    try:
        getattr(window, attr).enabled = False
    except Exception:
        pass
try:
    window.show_ursina_splash = False
except Exception:
    pass
try:
    window.show_ursina_icon = False
except Exception:
    pass

if hasattr(app, "editor_camera"):
    destroy(app.editor_camera)

# -----------------------------------------------------------------------------
# LIGHTING
# -----------------------------------------------------------------------------
AmbientLight(color=color.rgba(190, 190, 200, 255))
DirectionalLight(direction=Vec3(-1, -1, -1), color=color.rgb(255, 255, 245))

# -----------------------------------------------------------------------------
# CAMERA (Lakitu-style)
# -----------------------------------------------------------------------------
class LakituCamera(Entity):
    def __init__(self, target, distance=12, yaw=0.0, pitch=20):
        super().__init__()
        self.target = target
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self.smooth = 6.0
        self.min_pitch, self.max_pitch = -45.0, 70.0
        # start camera not at origin to avoid first-frame lerp jump
        camera.world_position = Vec3(0, 4, -self.distance)

    def update(self):
        if held_keys["right mouse"]:
            self.yaw  -= mouse.velocity[0] * 120
            self.pitch -= mouse.velocity[1] * 120
            self.pitch = clamp(self.pitch, self.min_pitch, self.max_pitch)

        target_pos = self.target.world_position + Vec3(0, 1.2, 0)
        cam_offset = Vec3(
            math.sin(math.radians(self.yaw)) * self.distance,
            math.sin(math.radians(self.pitch)) * self.distance * 0.6,
            math.cos(math.radians(self.yaw)) * self.distance
        )
        desired = target_pos + cam_offset
        # smooth step without relying on global lerp for Vec3
        t = min(time.dt * self.smooth, 1.0)
        camera.world_position = camera.world_position + (desired - camera.world_position) * t
        camera.look_at(target_pos)

        # expose yaw to world so movement can align with camera heading
        if "camera_pivot" in globals():
            camera_pivot.rotation_y = self.yaw

# -----------------------------------------------------------------------------
# PLAYER (Mario-ish capsule)
# -----------------------------------------------------------------------------
class Mario(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model="cube",
            color=color.rgb(255, 0, 0),
            scale=(1, 1.8, 1),
            collider="box",
            **kwargs
        )
        self.grounded = True
        self.vel_y = 0.0
        self.coins = 0

    def input_move_dir(self, cam_yaw: float) -> Vec3:
        x = held_keys["d"] - held_keys["a"]
        z = held_keys["w"] - held_keys["s"]
        if not x and not z:
            return Vec3(0, 0, 0)

        rad = math.radians(cam_yaw)
        wx = x * math.cos(rad) + z * math.sin(rad)
        wz = -x * math.sin(rad) + z * math.cos(rad)
        return Vec3(wx, 0, wz).normalized()

    def update(self):
        cam_yaw = getattr(globals().get("camera_pivot", object()), "rotation_y", 0.0)
        wish = self.input_move_dir(cam_yaw)
        self.position += wish * time.dt * 5.0

        # simple jump/gravity
        if self.grounded and held_keys["space"]:
            self.vel_y = 7.0
            self.grounded = False

        self.y += self.vel_y * time.dt
        self.vel_y -= 18.0 * time.dt

        if self.y <= 0:
            self.y = 0
            self.vel_y = 0
            self.grounded = True

        # coin collection (iterate over copy to avoid mutating while iterating)
        for c in list(coins):
            if (self.position - c.position).length() < 1.0:
                destroy(c)
                coins.remove(c)
                self.coins += 1
                coin_text.text = f"★ × {self.coins}/8"
                if self.coins == 8:
                    spawn_star()

# -----------------------------------------------------------------------------
# PEACH'S CASTLE – N64 ACCURATE LEVEL GEOMETRY
# -----------------------------------------------------------------------------
# Courtyard ground with checkerboard pattern
ground = Entity(model="plane", scale=(60, 1, 60), color=color.rgb(90, 160, 80), collider="box")

# Lighter grass patches for variation (checkerboard like N64)
for i in range(6):
    for j in range(6):
        if (i + j) % 2 == 0:
            Entity(
                model="plane",
                scale=(8, 1.01, 8),
                position=(-20 + i*8, 0.01, -20 + j*8),
                color=color.rgb(110, 175, 95)
            )

# Main castle base (wider and more imposing like N64)
castle_base = Entity(
    model="cube",
    scale=(18, 12, 14),
    position=(0, 6, -20),
    color=color.rgb(245, 235, 220),
    collider="box"
)

# Castle second tier (narrower upper section)
castle_upper = Entity(
    model="cube",
    scale=(15, 7, 11),
    position=(0, 15.5, -20),
    color=color.rgb(245, 235, 220),
    collider="box"
)

# Main red peaked roof base
castle_roof_base = Entity(
    model="cube",
    scale=(16, 0.5, 12),
    position=(0, 19, -20),
    color=color.rgb(200, 50, 50)
)

# Triangular roof peak (pyramid-like layers)
for i in range(6):
    roof_width = 16 - i * 2.5
    roof_depth = 12 - i * 2
    if roof_width > 0 and roof_depth > 0:
        Entity(
            model="cube",
            scale=(roof_width, 0.8, roof_depth),
            position=(0, 19.5 + i * 0.8, -20),
            color=color.rgb(200 - i*8, 50, 50)
        )

# Front left tower (cylindrical with cone roof)
left_tower_base = Entity(
    model="cylinder",
    scale=(3, 14, 3),
    position=(-9, 7, -13),
    color=color.rgb(245, 235, 220),
    collider="box",
    rotation_x=90  # Fix cylinder orientation
)

# Left tower cone roof
for i in range(7):
    cone_scale = 3.5 - i * 0.45
    Entity(
        model="cylinder",
        scale=(cone_scale, 0.6, cone_scale),
        position=(-9, 14 + i * 0.6, -13),
        color=color.rgb(200 - i*10, 50, 50),
        rotation_x=90
    )

# Left tower flag
Entity(
    model="cube",
    scale=(0.1, 3, 0.1),
    position=(-9, 18, -13),
    color=color.gray
)
Entity(
    model="cube",
    scale=(1, 0.6, 0.02),
    position=(-8.5, 19.5, -13),
    color=color.rgb(255, 200, 0)
)

# Front right tower (matching left)
right_tower_base = Entity(
    model="cylinder",
    scale=(3, 14, 3),
    position=(9, 7, -13),
    color=color.rgb(245, 235, 220),
    collider="box",
    rotation_x=90
)

# Right tower cone roof
for i in range(7):
    cone_scale = 3.5 - i * 0.45
    Entity(
        model="cylinder",
        scale=(cone_scale, 0.6, cone_scale),
        position=(9, 14 + i * 0.6, -13),
        color=color.rgb(200 - i*10, 50, 50),
        rotation_x=90
    )

# Right tower flag
Entity(
    model="cube",
    scale=(0.1, 3, 0.1),
    position=(9, 18, -13),
    color=color.gray
)
Entity(
    model="cube",
    scale=(1, 0.6, 0.02),
    position=(8.5, 19.5, -13),
    color=color.rgb(255, 200, 0)
)

# Back center tower (tallest)
back_tower = Entity(
    model="cylinder",
    scale=(3.5, 16, 3.5),
    position=(0, 8, -28),
    color=color.rgb(245, 235, 220),
    collider="box",
    rotation_x=90
)

# Back tower cone roof
for i in range(8):
    cone_scale = 4 - i * 0.45
    Entity(
        model="cylinder",
        scale=(cone_scale, 0.6, cone_scale),
        position=(0, 16 + i * 0.6, -28),
        color=color.rgb(200 - i*10, 50, 50),
        rotation_x=90
    )

# Castle main entrance (large arched door)
entrance = Entity(
    model="cube",
    scale=(4, 6, 0.5),
    position=(0, 3, -12.5),
    color=color.rgb(101, 67, 33),
    collider="box"
)

# Door arch decoration
Entity(
    model="cube",
    scale=(5, 1, 0.6),
    position=(0, 6.5, -12.4),
    color=color.rgb(220, 210, 200)
)

# Iconic star emblem above door
star_emblem = Entity(
    model="sphere",
    scale=(1.5, 1.5, 0.3),
    position=(0, 9, -12.3),
    color=color.yellow
)

# Princess Peach stained glass window (simplified)
Entity(
    model="cube",
    scale=(3, 3.5, 0.2),
    position=(0, 10, -12.2),
    color=color.rgba(255, 180, 200, 200)
)

# Side windows on main castle
for floor in [8, 13]:
    for side in [-6, 6]:
        Entity(
            model="cube",
            scale=(1.5, 2, 0.2),
            position=(side, floor, -12.7),
            color=color.rgba(100, 150, 220, 200)
        )

# Stone bridge/path to castle
bridge = Entity(
    model="cube",
    scale=(7, 0.2, 12),
    position=(0, 0.1, -6),
    color=color.rgb(180, 170, 160)
)

# Bridge railings
Entity(model="cube", scale=(0.3, 1, 12), position=(-3.5, 0.5, -6), color=color.rgb(160, 150, 140))
Entity(model="cube", scale=(0.3, 1, 12), position=(3.5, 0.5, -6), color=color.rgb(160, 150, 140))

# Castle entrance stairs (more gradual)
for i in range(5):
    Entity(
        model="cube",
        scale=(7 - i*0.4, 0.4, 2),
        position=(0, 0.2 + i * 0.4, -11.5 + i * 0.5),
        color=color.rgb(200, 190, 180),
        collider="box"
    )

# Garden hedges (maze-like)
hedge_positions = [
    (-12, 1, 0), (12, 1, 0),
    (-12, 1, -8), (12, 1, -8),
    (-18, 1, 5), (18, 1, 5)
]
for pos in hedge_positions:
    Entity(model="cube", scale=(1.5, 2.5, 6), position=pos, color=color.rgb(40, 120, 40), collider="box")

# Topiaries/trees around courtyard
tree_positions = [
    (-20, 3, -15), (20, 3, -15),
    (-20, 3, 8), (20, 3, 8),
    (-15, 3, 0), (15, 3, 0)
]
for pos in tree_positions:
    # Trunk
    Entity(
        model="cylinder",
        scale=(0.8, 4, 0.8),
        position=(pos[0], pos[1]-1, pos[2]),
        color=color.rgb(101, 67, 33),
        rotation_x=90
    )
    # Foliage (3 spheres for fuller look)
    Entity(model="sphere", scale=3, position=pos, color=color.rgb(34, 139, 34))
    Entity(model="sphere", scale=2.5, position=(pos[0], pos[1]+1, pos[2]), color=color.rgb(44, 149, 44))
    Entity(model="sphere", scale=2, position=(pos[0], pos[1]+2, pos[2]), color=color.rgb(54, 159, 54))

# Moat water (around castle sides - simplified)
Entity(
    model="plane",
    scale=(20, 1, 8),
    position=(-20, 0.02, -20),
    color=color.rgba(100, 150, 200, 180)
)
Entity(
    model="plane",
    scale=(20, 1, 8),
    position=(20, 0.02, -20),
    color=color.rgba(100, 150, 200, 180)
)

# -----------------------------------------------------------------------------
# COLLECTIBLES (8 coins styled like N64)
# -----------------------------------------------------------------------------
coins = []
coin_positions = [
    (-8, 1, 3), (8, 1, 3),
    (-5, 1, -2), (5, 1, -2),
    (-3, 1, 6), (3, 1, 6),
    (-10, 1, 10), (10, 1, 10)
]
for pos in coin_positions:
    e = Entity(
        model="cylinder",
        color=color.yellow,
        position=pos,
        scale=(0.8, 0.1, 0.8),
        rotation_x=90,
        double_sided=True
    )
    e.rotation_y = random.uniform(0, 360)
    coins.append(e)

star = None
def spawn_star():
    global star
    star = Entity(
        model="sphere",
        color=color.gold,
        position=(0, 5, -6),
        scale=1.5,
        collider="sphere"
    )
    # Make star rotate
    star.rotation_speed = Vec3(0, 100, 0)
    
    msg = Text(
        text="★ POWER STAR APPEARS! ★",
        origin=(0, 0),
        position=(0, 0.3),
        scale=get_text_scale() * 1.3,
        color=color.yellow,
        background=True
    )
    invoke(destroy, msg, delay=3)

# -----------------------------------------------------------------------------
# ENTITIES
# -----------------------------------------------------------------------------
player = Mario(position=(0, 1, 12))
camera_pivot = Entity()
lakitu = LakituCamera(target=player, distance=12)
sky = Sky()

# -----------------------------------------------------------------------------
# DYNAMIC HUD (N64 style)
# -----------------------------------------------------------------------------
def get_text_scale():
    """Calculate appropriate text scale based on window size (baseline 600×400)."""
    base_scale = 0.5
    width_ratio  = window.size[0] / 600.0
    height_ratio = window.size[1] / 400.0
    return base_scale * min(width_ratio, height_ratio)

coin_text = Text(
    text="★ × 0/8",
    position=(-0.85, 0.45),
    origin=(0, 0),
    scale=get_text_scale(),
    color=color.yellow,
    background=True
)

help_text = Text(
    text="WASD Move • Space Jump • RMB Camera • Esc Exit",
    origin=(0, 0),
    position=(0, -0.45),
    scale=get_text_scale() * 0.8,
    background=True
)

title_text = Text(
    text="PRINCESS PEACH'S CASTLE",
    origin=(0, 0),
    position=(0, 0.45),
    scale=get_text_scale() * 1.2,
    color=color.rgb(255, 215, 0),
    background=True
)

# -----------------------------------------------------------------------------
# MAIN UPDATE
# -----------------------------------------------------------------------------
def update():
    # keep HUD scaled and anchored
    s = get_text_scale()
    coin_text.scale = s
    help_text.scale = s * 0.8
    title_text.scale = s * 1.2
    coin_text.position = (-0.85, 0.45)
    help_text.position = (0, -0.45)
    title_text.position = (0, 0.45)

    # spin coins (rotate around Y axis for proper spinning)
    for c in coins:
        c.rotation_y += 180 * time.dt

    # rotate star if it exists
    if star:
        star.rotation_y += 100 * time.dt
        # bobbing effect
        star.y = 5 + math.sin(time.time * 2) * 0.3
        
        # star collection
        if (player.position - star.position).length() < 1.5:
            destroy(star)
            txt = Text(
                text="★ HERE WE GO! ★",
                origin=(0, 0),
                position=(0, 0.2),
                scale=get_text_scale() * 1.5,
                color=color.gold,
                background=True
            )
            invoke(destroy, txt, delay=3)

# -----------------------------------------------------------------------------
# INPUT + RUN
# -----------------------------------------------------------------------------
def input(key):
    if key == "escape":
        application.quit()

app.run()
