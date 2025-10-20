#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# SM64 Peach's Castle – Tech Demo (UI-free clean build, proper dynamic scaling)
# -----------------------------------------------------------------------------
# • Peach's Castle exterior with towers, courtyard, and entrance
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
    def __init__(self, target, distance=7, yaw=0.0, pitch=20):
        super().__init__()
        self.target = target
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self.smooth = 6.0
        self.min_pitch, self.max_pitch = -45.0, 70.0
        # start camera not at origin to avoid first-frame lerp jump
        camera.world_position = Vec3(0, 2, -self.distance)

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
                coin_text.text = f"Coins: {self.coins}/8"
                if self.coins == 8:
                    spawn_star()

# -----------------------------------------------------------------------------
# PEACH'S CASTLE – LEVEL GEOMETRY
# -----------------------------------------------------------------------------
# Courtyard ground
ground = Entity(model="plane", scale=(50, 1, 50), color=color.rgb(120, 180, 100), collider="box")

# Main castle body
castle_main = Entity(
    model="cube",
    scale=(12, 8, 10),
    position=(0, 4, -15),
    color=color.rgb(255, 240, 220),
    collider="box"
)

# Castle roof
castle_roof = Entity(
    model="cube",
    scale=(13, 1, 11),
    position=(0, 8.5, -15),
    color=color.rgb(200, 50, 50)
)

# Left tower
left_tower = Entity(
    model="cube",
    scale=(3, 10, 3),
    position=(-7, 5, -15),
    color=color.rgb(255, 240, 220),
    collider="box"
)
left_tower_roof = Entity(
    model="cube",
    scale=(3.5, 2, 3.5),
    position=(-7, 11, -15),
    color=color.rgb(200, 50, 50)
)

# Right tower
right_tower = Entity(
    model="cube",
    scale=(3, 10, 3),
    position=(7, 5, -15),
    color=color.rgb(255, 240, 220),
    collider="box"
)
right_tower_roof = Entity(
    model="cube",
    scale=(3.5, 2, 3.5),
    position=(7, 11, -15),
    color=color.rgb(200, 50, 50)
)

# Castle entrance (door area)
entrance = Entity(
    model="cube",
    scale=(3, 5, 1),
    position=(0, 2.5, -10),
    color=color.rgb(100, 50, 30),
    collider="box"
)

# Front steps
for i in range(3):
    Entity(
        model="cube",
        scale=(6, 0.5, 2),
        position=(0, 0.25 + i * 0.5, -8 + i * 0.5),
        color=color.rgb(180, 180, 180),
        collider="box"
    )

# Bridge/path to castle
path = Entity(
    model="cube",
    scale=(6, 0.1, 8),
    position=(0, 0.05, -4),
    color=color.rgb(200, 180, 150)
)

# Garden hedges
Entity(model="cube", scale=(1, 2, 8), position=(-10, 1, -5), color=color.rgb(40, 120, 40), collider="box")
Entity(model="cube", scale=(1, 2, 8), position=(10, 1, -5), color=color.rgb(40, 120, 40), collider="box")

# Decorative trees
for pos in [(-15, 2, -10), (15, 2, -10), (-15, 2, 5), (15, 2, 5)]:
    Entity(model="cube", scale=(1, 4, 1), position=pos, color=color.rgb(101, 67, 33))        # trunk
    Entity(model="sphere", scale=3, position=(pos[0], pos[1] + 3, pos[2]), color=color.rgb(34, 139, 34))  # top

# -----------------------------------------------------------------------------
# COLLECTIBLES (8 coins in courtyard)
# -----------------------------------------------------------------------------
coins = []
coin_positions = [
    (-8, 1, 2), (8, 1, 2),
    (-6, 1, -2), (6, 1, -2),
    (-4, 1, 5), (4, 1, 5),
    (-10, 1, 8), (10, 1, 8)
]
for pos in coin_positions:
    e = Entity(
        model="circle",           # simple flat coin; billboard keeps it visible
        color=color.yellow,
        position=pos,
        scale=0.8,
        billboard=True,
        double_sided=True
    )
    e.rotation_z = random.uniform(0, 360)
    coins.append(e)

star = None
def spawn_star():
    global star
    star = Entity(model="sphere", color=color.gold, position=(0, 4, -6), scale=1.2, collider="sphere")
    msg = Text(
        text="★ A STAR HAS APPEARED! ★",
        origin=(0, 0),
        position=(0, 0.3),
        scale=get_text_scale() * 1.2,
        color=color.yellow,
        background=True
    )
    invoke(destroy, msg, delay=3)

# -----------------------------------------------------------------------------
# ENTITIES
# -----------------------------------------------------------------------------
player = Mario(position=(0, 1, 10))
camera_pivot = Entity()
lakitu = LakituCamera(target=player)
sky = Sky()

# -----------------------------------------------------------------------------
# DYNAMIC HUD (small, scales with window size)
# -----------------------------------------------------------------------------
def get_text_scale():
    """Calculate appropriate text scale based on window size (baseline 600×400)."""
    base_scale = 0.5  # tiny by design
    width_ratio  = window.size[0] / 600.0
    height_ratio = window.size[1] / 400.0
    return base_scale * min(width_ratio, height_ratio)

coin_text = Text(
    text="Coins: 0/8",
    position=(-0.85, 0.45),
    origin=(0, 0),
    scale=get_text_scale(),
    background=True
)

help_text = Text(
    text="WASD Move • Space Jump • RMB Orbit • Esc Quit",
    origin=(0, 0),
    position=(0, -0.45),
    scale=get_text_scale(),
    background=True
)

title_text = Text(
    text="PEACH'S CASTLE",
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
    help_text.scale = s
    title_text.scale = s * 1.2
    coin_text.position = (-0.85, 0.45)
    help_text.position = (0, -0.45)
    title_text.position = (0, 0.45)

    # spin coins (billboarded; rotate about facing axis)
    for c in coins:
        c.rotation_z += 180 * time.dt

    # optional: star pickup to celebrate completion
    if star and (player.position - star.position).length() < 1.2:
        destroy(star)
        txt = Text(
            text="★ STAR COLLECTED! ★",
            origin=(0, 0),
            position=(0, 0.2),
            scale=get_text_scale() * 1.2,
            color=color.azure,
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
