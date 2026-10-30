"""
DeepCrop field sensor unit: parametric 3D model (build123d).

Builds the full field assembly around one potted tomato plant:
  - ESP32-S3 DevKit + sensor interface boards in a 3D-printable case on a stake
  - DHT22 inside a small radiation shield at canopy height
  - Resistive soil-moisture fork probe and Crowtail pH probe in the soil
  - Cable runs, cable glands, USB-C power to a 5V adapter

Outputs (all in millimetres, Z up, origin at the centre of the pot base):
  out/field_unit_assembly.step   full coloured assembly for Fusion 360 / FreeCAD / Onshape
  out/print/*.stl                3D-printable parts (case body, lid, shield)
  out/viewer/*.stl + parts.json  per-part meshes for the web viewer

Run:  python cad/field_unit.py
Board and sensor dimensions are nominal; measure your own parts before printing.
"""

import json
import math
from pathlib import Path

from build123d import (
    Align, Axis, Box, Circle, Color, Compound, Cone, Cylinder, Plane, Pos,
    Rot, Sphere, Spline, export_step, export_stl, fillet, scale, sweep,
)

OUT = Path(__file__).parent / "out"
MIN = (Align.CENTER, Align.CENTER, Align.MIN)

# --- Pot and soil ---
POT_R_BOTTOM, POT_R_TOP, POT_H, POT_WALL = 100.0, 125.0, 220.0, 6.0
SOIL_Z = 195.0

# --- Stake (hollow 12 mm conduit, carries the DHT22 cable) ---
STAKE_X, STAKE_R, STAKE_Z0, STAKE_Z1 = 98.0, 6.0, 110.0, 490.0

# --- Case: back face sits 8 mm off the stake, front is an open face closed by the lid ---
CASE_D, CASE_W, CASE_H, WALL = 36.0, 80.0, 104.0, 2.5
CASE_X0 = STAKE_X + 8.0                 # back face
CASE_X1 = CASE_X0 + CASE_D              # front (lid) face
CASE_ZC = 300.0
CASE_Z0 = CASE_ZC - CASE_H / 2          # underside of the floor
LID_T = 2.5

# --- ESP32-S3-DevKitC-1 (N16R8), nominal ---
ESP_L, ESP_W, PCB_T = 69.0, 26.0, 1.6

# --- Radiation shield for the DHT22 ---
SHIELD_X, SHIELD_R, SHIELD_HOLE_R = 63.0, 30.0, 12.0
SHIELD_PLATES_Z = [445.0, 455.0, 465.0, 475.0]
SHIELD_TOP_Z = 482.0

# --- Probe positions in the soil ---
MOIST_XY = (55.0, 55.0)
PH_XY = (55.0, -55.0)

GLAND_X = CASE_X0 + 26.0
GLAND_YS = {"moisture": 22.0, "dht22": 0.0, "ph": -22.0}
GLAND_Z1 = CASE_Z0                      # glands hang below the floor
GLAND_Z0 = GLAND_Z1 - 10.0

USB_X = CASE_X0 + WALL + 2.5 + PCB_T + 1.6   # centre of the USB-C plugs


def cable(points, r=2.0):
    path = Spline(*points)
    profile = Plane(origin=path @ 0, z_dir=path % 0) * Circle(r)
    return sweep(profile, path=path)


def build_pot():
    outer = Cone(POT_R_BOTTOM, POT_R_TOP, POT_H, align=MIN)
    inner_top = POT_R_TOP - POT_WALL + 0.3
    inner = Pos(0, 0, POT_WALL) * Cone(POT_R_BOTTOM - POT_WALL, inner_top, POT_H, align=MIN)
    rim = Pos(0, 0, POT_H - 8) * (Cylinder(POT_R_TOP + 5, 10, align=MIN) - Cylinder(inner_top - 0.5, 10, align=MIN))
    return outer - inner + rim


def build_soil():
    h = SOIL_Z - POT_WALL
    r0 = POT_R_BOTTOM - POT_WALL - 0.5
    r_top = r0 + (POT_R_TOP - POT_R_BOTTOM) * h / POT_H
    return Pos(0, 0, POT_WALL) * Cone(r0, r_top, h, align=MIN)


def leaf(length, width, at, yaw, pitch=-15):
    blade = scale(Sphere(1), by=(length / 2, width / 2, 1.2))
    return Pos(*at) * Rot(0, 0, yaw) * Rot(0, pitch, 0) * Pos(length / 2, 0, 0) * blade


def build_plant():
    stem = cable([(0, 0, SOIL_Z - 15), (4, -3, 330), (-3, 4, 500), (2, 0, 640)], r=6)
    parts = [stem]
    # (height on stem, branch direction in degrees, branch length)
    branches = [(270, 200, 70), (320, 110, 80), (360, 250, 85), (410, 160, 75),
                (455, 290, 70), (505, 210, 65), (550, 120, 60), (600, 230, 50)]
    for z, ang, length in branches:
        a = math.radians(ang)
        tip = (length * math.cos(a), length * math.sin(a), z + 25)
        mid = (0.5 * tip[0], 0.5 * tip[1], z + 18)
        parts.append(cable([(0, 0, z), mid, tip], r=2.5))
        for k, d_yaw in enumerate((-40, 0, 40)):
            parts.append(leaf(42 - 6 * abs(k - 1), 18, tip, ang + d_yaw))
    top = (2, 0, 640)
    for d_yaw in (0, 120, 240):
        parts.append(leaf(30, 14, top, d_yaw, pitch=-35))
    return Compound(children=parts)


def build_fruit():
    spots = [(-30, -38, 300, 19), (-48, -22, 285, 16), (-58, 20, 345, 20), (-40, 40, 330, 15)]
    return Compound(children=[Pos(x, y, z) * Sphere(r) for x, y, z, r in spots])


def build_stake():
    tube = Pos(STAKE_X, 0, STAKE_Z0) * (Cylinder(STAKE_R, STAKE_Z1 - STAKE_Z0, align=MIN)
                                        - Cylinder(STAKE_R - 1.5, STAKE_Z1 - STAKE_Z0, align=MIN))
    spike = Pos(STAKE_X, 0, STAKE_Z0) * Rot(180, 0, 0) * Cone(STAKE_R, 0.5, 25, align=MIN)
    return tube + spike


def build_case_body():
    outer = Pos((CASE_X0 + CASE_X1) / 2, 0, CASE_ZC) * Box(CASE_D, CASE_W, CASE_H)
    outer = fillet(outer.edges().filter_by(Axis.X), radius=5)
    cavity_d = CASE_D - WALL
    cavity = Pos(CASE_X0 + WALL + cavity_d / 2 + 0.01, 0, CASE_ZC) * Box(cavity_d, CASE_W - 2 * WALL, CASE_H - 2 * WALL)
    body = outer - cavity

    # Corner screw bosses for the lid (M3 self-tapping, 2.5 mm pilot)
    by, bz = CASE_W / 2 - WALL - 4, CASE_H / 2 - WALL - 4
    for sy in (-1, 1):
        for sz in (-1, 1):
            boss = Pos(CASE_X0 + WALL, sy * by, CASE_ZC + sz * bz) * Rot(0, 90, 0) * Cylinder(4, cavity_d, align=MIN)
            hole = Pos(CASE_X0 + WALL, sy * by, CASE_ZC + sz * bz) * Rot(0, 90, 0) * Cylinder(1.25, cavity_d + 1, align=MIN)
            body = body + boss - hole

    # Board standoffs on the back wall (ESP32 and the two sensor boards)
    for y, z in [(-10, CASE_ZC - 28), (10, CASE_ZC - 28), (-10, CASE_ZC + 28), (10, CASE_ZC + 28),
                 (-26, CASE_ZC + 10), (25, CASE_ZC + 10)]:
        body += Pos(CASE_X0 + WALL, y, z) * Rot(0, 90, 0) * Cylinder(2.5, 2.5, align=MIN)

    # USB-C slot (both ports) and three PG7 gland holes in the floor
    body -= Pos(USB_X, 0, CASE_Z0 + WALL / 2) * Box(10, 28, WALL + 2)
    for y in GLAND_YS.values():
        body -= Pos(GLAND_X, y, CASE_Z0 - 1) * Cylinder(6.3, WALL + 2, align=MIN)
    # Drip hood over the USB slot
    hood = Pos(USB_X, 0, CASE_Z0 - 4) * Box(14, 32, 1.5) + Pos(USB_X - 7.75 + 0.75, 0, CASE_Z0 - 2) * Box(1.5, 32, 5.5)
    body += hood

    # Stake clamps: C-rings joined to the back face
    for z in (CASE_ZC - 35, CASE_ZC + 35):
        ring = Pos(STAKE_X, 0, z - 6) * (Cylinder(STAKE_R + 4, 12, align=MIN) - Cylinder(STAKE_R + 0.2, 12, align=MIN))
        ring -= Pos(STAKE_X - STAKE_R - 4, 0, z) * Box(8, 6, 14)        # split for snap-fit
        bridge = Pos((STAKE_X + STAKE_R + CASE_X0) / 2 + 1, 0, z) * Box(CASE_X0 - STAKE_X - STAKE_R + 2, 12, 12)
        body += ring + bridge
    return body


def build_case_lid():
    lid = Pos(CASE_X1 + LID_T / 2, 0, CASE_ZC) * Box(LID_T, CASE_W, CASE_H)
    lid = fillet(lid.edges().filter_by(Axis.X), radius=5)
    by, bz = CASE_W / 2 - WALL - 4, CASE_H / 2 - WALL - 4
    for sy in (-1, 1):
        for sz in (-1, 1):
            lid -= Pos(CASE_X1 - 1, sy * by, CASE_ZC + sz * bz) * Rot(0, 90, 0) * Cylinder(1.7, LID_T + 2, align=MIN)
    # Gasket lip that sits just inside the walls
    lip_outer = Pos(CASE_X1 - 1.5, 0, CASE_ZC) * Box(3, CASE_W - 2 * WALL - 0.4, CASE_H - 2 * WALL - 0.4)
    lip_inner = Pos(CASE_X1 - 1.5, 0, CASE_ZC) * Box(3.2, CASE_W - 2 * WALL - 3.6, CASE_H - 2 * WALL - 3.6)
    return lid + (lip_outer - lip_inner)


def build_esp32():
    x_pcb = CASE_X0 + WALL + 2.5
    z0 = CASE_Z0 + WALL + 1.5
    pcb = Pos(x_pcb + PCB_T / 2, 0, z0 + ESP_L / 2) * Box(PCB_T, ESP_W, ESP_L)
    return pcb, x_pcb, z0


def build_esp32_parts():
    pcb, x_pcb, z0 = build_esp32()
    can = Pos(x_pcb + PCB_T + 1.6, 0, z0 + ESP_L - 9 - 3) * Box(3.2, 18, 18)       # WROOM-1 module shield
    antenna = Pos(x_pcb + PCB_T + 0.4, 0, z0 + ESP_L - 3) * Box(0.8, 18, 6)
    usb = Compound(children=[Pos(x_pcb + PCB_T + 1.6, y, z0 + 3.5) * Box(3.2, 9, 7.5) for y in (-7.5, 7.5)])
    buttons = Compound(children=[Pos(x_pcb + PCB_T + 0.8, y, z0 + 12) * Box(1.6, 4, 3) for y in (-9, 9)])
    return pcb, Compound(children=[can, usb, buttons]), antenna


def build_sensor_boards():
    x = CASE_X0 + WALL + 2.5
    lm393 = Pos(x + PCB_T / 2, 25, CASE_ZC + 10) * Box(PCB_T, 14, 32)
    lm393_pot = Pos(x + PCB_T + 2.5, 25, CASE_ZC + 18) * Box(5, 7, 7)
    ph_board = Pos(x + PCB_T / 2, -26, CASE_ZC + 10) * Box(PCB_T, 20, 40)
    bnc = Pos(x + PCB_T + 6, -26, CASE_ZC - 6) * Rot(0, 90, 0) * Cylinder(5, 12, align=MIN)
    return Compound(children=[lm393, ph_board]), Compound(children=[lm393_pot, bnc])


def build_glands():
    parts = []
    for y in GLAND_YS.values():
        parts.append(Pos(GLAND_X, y, GLAND_Z0) * Cylinder(7.5, GLAND_Z1 - GLAND_Z0, align=MIN))
        parts.append(Pos(GLAND_X, y, GLAND_Z1) * Cylinder(5.5, WALL + 3, align=MIN))
    return Compound(children=parts)


def build_shield():
    plates = []
    for z in SHIELD_PLATES_Z:
        ring = Pos(SHIELD_X, 0, z) * Cone(SHIELD_R, SHIELD_R - 6, 2, align=MIN) \
            - Pos(SHIELD_X, 0, z - 1) * Cylinder(SHIELD_HOLE_R, 4, align=MIN)
        plates.append(ring)
    top = Pos(SHIELD_X, 0, SHIELD_TOP_Z) * Cone(SHIELD_R + 4, SHIELD_R - 8, 4, align=MIN)
    shield = top
    for p in plates:
        shield += p
    for i in range(3):
        a = math.radians(90 + 120 * i)
        sx, sy = SHIELD_X + (SHIELD_R - 4) * math.cos(a), (SHIELD_R - 4) * math.sin(a)
        shield += Pos(sx, sy, SHIELD_PLATES_Z[0]) * Cylinder(2, SHIELD_TOP_Z - SHIELD_PLATES_Z[0], align=MIN)
    arm = Pos((SHIELD_X + STAKE_X) / 2, 0, SHIELD_TOP_Z + 2) * Box(STAKE_X - SHIELD_X, 10, 4)
    collar = Pos(STAKE_X, 0, SHIELD_TOP_Z - 6) * (Cylinder(STAKE_R + 3, 14, align=MIN) - Cylinder(STAKE_R + 0.2, 14, align=MIN))
    return shield + arm + collar


def build_dht22():
    body = Pos(SHIELD_X, 0, 446) * Box(15.1, 7.7, 25, align=MIN)
    grille = Pos(SHIELD_X, -3.9, 452) * Box(11, 0.6, 14, align=MIN)
    return body - grille


def build_moisture_probe():
    x, y = MOIST_XY
    head = Pos(x, y, SOIL_Z + 2) * Box(1.6, 20, 30, align=MIN)
    prongs = [Pos(x, y + s * 6, SOIL_Z - 45) * Box(1.6, 4, 47, align=MIN) for s in (-1, 1)]
    pins = Pos(x, y, SOIL_Z + 32) * Box(2.5, 5, 5, align=MIN)
    pcb = head
    for p in prongs:
        pcb += p
    return pcb, pins


def build_ph_probe():
    x, y = PH_XY
    body = Pos(x, y, 140) * Cylinder(6, 105, align=MIN)
    bulb = Pos(x, y, 140) * Sphere(4.5)
    cap = Pos(x, y, 245) * Cylinder(7.5, 22, align=MIN)
    return body + cap, bulb


def build_cables():
    mx, my = MOIST_XY
    px, py = PH_XY
    gm, gd, gp = (GLAND_X, GLAND_YS["moisture"], GLAND_Z0), (GLAND_X, GLAND_YS["dht22"], GLAND_Z0), (GLAND_X, GLAND_YS["ph"], GLAND_Z0)
    moisture = cable([(mx, my, SOIL_Z + 37), (mx + 5, my - 2, 252), (95, 40, 246), (GLAND_X - 4, gm[1] + 4, 230), (gm[0], gm[1], gm[2] + 0.5)])
    ph = cable([(px, py, 267), (px + 4, py + 2, 285), (90, -40, 262), (GLAND_X - 4, gp[1] - 4, 230), (gp[0], gp[1], gp[2] + 0.5)], r=2.4)
    dht = cable([(gd[0], gd[1], gd[2] + 0.5), (GLAND_X - 2, 2, 228), (STAKE_X + 6, 13, 236),
                 (STAKE_X, 13, 262), (STAKE_X, 13, 420), (STAKE_X - 6, 8, 474), (SHIELD_X + 4, 0, 474)])
    usb = cable([(USB_X, 0, CASE_Z0 + 0.5), (USB_X, 0, 228), (USB_X + 22, 0, 190), (150, 0, 90),
                 (168, 0, 12), (200, 0, 6), (262, 0, 12)], r=2.2)
    return moisture, ph, dht, usb


def build_adapter():
    adapter = Pos(282, 0, 0) * Box(40, 40, 28, align=MIN)
    adapter = fillet(adapter.edges().filter_by(Axis.Z), radius=4)
    return adapter


# name, builder result, colour (hex), group, description
def build_parts():
    pcb, chips, antenna = build_esp32_parts()
    boards, board_parts = build_sensor_boards()
    fork, fork_pins = build_moisture_probe()
    ph_body, ph_bulb = build_ph_probe()
    c_moist, c_ph, c_dht, c_usb = build_cables()
    return [
        ("pot", build_pot(), "#B7653F", "Plant", "Terracotta pot, 250 mm top diameter, 220 mm tall"),
        ("soil", build_soil(), "#4A3527", "Plant", "Potting soil, filled to 25 mm below the rim"),
        ("plant", build_plant(), "#3E8E41", "Plant", "Tomato plant (illustrative shape)"),
        ("fruit", build_fruit(), "#D7392B", "Plant", "Tomato fruit (illustrative)"),
        ("stake", build_stake(), "#D9D4C7", "Mount", "12 mm hollow PVC conduit stake; the DHT22 cable runs inside it"),
        ("case_body", build_case_body(), "#2F5D8A", "Case", "Printed case body 36 x 80 x 104 mm: board standoffs, 3 PG7 gland holes, USB-C slot with drip hood, snap clamps for the stake"),
        ("case_lid", build_case_lid(), "#9EC3E6", "Case", "Clear PETG printed lid with gasket lip, 4 x M3 screws"),
        ("esp32_pcb", pcb, "#1B1B1B", "Electronics", "ESP32-S3 DevKit (N16R8) board, 69 x 26 mm"),
        ("esp32_parts", chips, "#BFC4C9", "Electronics", "ESP32-S3-WROOM-1 module, 2 x USB-C ports, BOOT and RST buttons"),
        ("esp32_antenna", antenna, "#C9A227", "Electronics", "PCB antenna, pointing up and away from the soil"),
        ("sensor_boards", boards, "#1F6F43", "Electronics", "LM393 moisture board (left) and Crowtail pH interface board (right)"),
        ("sensor_board_parts", board_parts, "#7A7F86", "Electronics", "Moisture threshold trimmer and pH BNC socket"),
        ("glands", build_glands(), "#3A3A3A", "Case", "PG7 cable glands for moisture, DHT22 and pH cables"),
        ("shield", build_shield(), "#F2F2EE", "Mount", "Printed radiation shield: louvred plates keep sun and rain off the DHT22"),
        ("dht22", build_dht22(), "#FFFFFF", "Sensors", "DHT22 / AM2302 temperature and humidity sensor at canopy height"),
        ("moisture_probe", fork, "#2E7D4F", "Sensors", "Resistive soil-moisture fork, about 45 mm deep"),
        ("moisture_pins", fork_pins, "#222222", "Sensors", "Probe connector"),
        ("ph_probe", ph_body, "#2B2B2B", "Sensors", "Crowtail pH electrode, glass bulb in moist soil"),
        ("ph_bulb", ph_bulb, "#CFE8F2", "Sensors", "pH glass bulb"),
        ("cable_moisture", c_moist, "#E0A030", "Cables", "Moisture probe cable"),
        ("cable_ph", c_ph, "#6B6B6B", "Cables", "pH probe coax cable"),
        ("cable_dht22", c_dht, "#3B6FD0", "Cables", "DHT22 cable, routed inside the stake"),
        ("cable_usb", c_usb, "#202020", "Cables", "USB-C power and data cable"),
        ("adapter", build_adapter(), "#EDEDED", "Power", "5V USB wall adapter"),
    ]


def main():
    (OUT / "viewer").mkdir(parents=True, exist_ok=True)
    (OUT / "print").mkdir(parents=True, exist_ok=True)

    parts = build_parts()
    children, manifest = [], []
    for name, shape, color, group, desc in parts:
        shape.label = name
        shape.color = Color(color)
        children.append(shape)
        export_stl(shape, str(OUT / "viewer" / f"{name}.stl"), tolerance=0.15, angular_tolerance=0.3)
        manifest.append({"name": name, "file": f"{name}.stl", "color": color, "group": group, "description": desc})
        print(f"  built {name}")

    assembly = Compound(label="deepcrop_field_unit", children=children)
    export_step(assembly, str(OUT / "field_unit_assembly.step"))
    (OUT / "viewer" / "parts.json").write_text(json.dumps(manifest, indent=2))

    printable = {name: shape for name, shape, *_ in parts if name in ("case_body", "case_lid", "shield")}
    for name, shape in printable.items():
        export_stl(shape, str(OUT / "print" / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)

    bb = assembly.bounding_box()
    print(f"Assembly size: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")


if __name__ == "__main__":
    main()
