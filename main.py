#!/usr/bin/env python3
"""Charm the Cartographers -- a one-day treasure map sprint entry.

Draws a treasure map of an island that does not exist, with eight
witty labeled places, a dotted route to a big red X, a compass rose,
a sea serpent, a ship, and a note to the museum curator. Pure
standard library: the PNG is encoded by hand (zlib + struct), the
lettering is a small bitmap font drawn pixel by pixel, and every
stroke is deterministic, so two runs produce byte-identical files.

Writes /output/entry.png (1024x1024, under 1 MiB) when /output
exists, otherwise ./entry.png next to the program.
"""

import math
import os
import random
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- PNG ---

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, rgb):
    """rgb: bytearray of W*H*3 bytes. Writes a plain RGB PNG."""
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 6)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", data)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# -------------------------------------------------------------- canvas ---

class Canvas:
    def __init__(self):
        self.px = bytearray(W * H * 3)

    def set(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill(self, color):
        r, g, b = color
        for i in range(0, len(self.px), 3):
            self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def disc(self, cx, cy, rad, color):
        r2 = rad * rad
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    self.set(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        rad = max(width // 2, 1)
        for s in range(steps + 1):
            t = s / steps
            self.disc(round(x0 + dx * t), round(y0 + dy * t), rad, color)

    def polyline(self, pts, color, width=1, closed=False):
        seq = list(pts) + ([pts[0]] if closed and len(pts) > 1 else [])
        for a, b in zip(seq, seq[1:]):
            self.line(a[0], a[1], b[0], b[1], color, width)

    def fill_poly(self, pts, color):
        """Scanline fill of a simple polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(min(ys), 0), min(max(ys), H - 1) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(max(int(math.ceil(a)), 0),
                               min(int(b), W - 1) + 1):
                    self.set(x, y, color)

    def dotted(self, x0, y0, x1, y1, color, dot=4, gap=7):
        dx, dy = x1 - x0, y1 - y0
        dist = math.hypot(dx, dy)
        steps = int(dist / (dot + gap))
        for s in range(steps + 1):
            t = s * (dot + gap) / max(dist, 1)
            cx = round(x0 + dx * t)
            cy = round(y0 + dy * t)
            self.disc(cx, cy, dot, color)

    def arc(self, cx, cy, rad, a0, a1, color, width=2):
        steps = max(int(rad * abs(a1 - a0) / 3), 8)
        prev = None
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            p = (round(cx + rad * math.cos(a)), round(cy + rad * math.sin(a)))
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], color, width)
            prev = p


# -------------------------------------------------------------- letters ---

# A small 5x7 bitmap font, uppercase plus digits and common marks.
# Each glyph is 7 rows of 5 cells; '#' is ink.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, color, scale=3):
    """Draw s in the bitmap font, upper-left corner at (x, y)."""
    for ci, ch in enumerate(s.upper()):
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        ox = x + ci * 6 * scale
        for gy, row in enumerate(glyph):
            for gx, cell in enumerate(row):
                if cell == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            cv.set(ox + gx * scale + dx,
                                   y + gy * scale + dy, color)


def draw_text_centered(cv, cx, y, s, color, scale=3):
    draw_text(cv, cx - text_width(s, scale) // 2, y, s, color, scale)

# ----------------------------------------------------------------- map ---

SEA = (154, 188, 198)
SEA_DARK = (110, 155, 168)
SAND = (239, 221, 176)
LAND = (183, 201, 138)
LAND_DARK = (140, 165, 100)
INK = (74, 50, 32)
RED = (178, 58, 44)
RIVER = (111, 168, 184)
PARCH = (242, 227, 182)
SNOW = (250, 248, 240)
SAIL = (250, 244, 224)

COAST = [(300, 250), (380, 215), (480, 210), (580, 235), (670, 290),
         (740, 370), (775, 470), (760, 580), (700, 690), (640, 790),
         (540, 850), (430, 845), (330, 800), (250, 720), (200, 600),
         (195, 480), (230, 360), (260, 300)]


def inside_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi:
                inside = not inside
    return inside


def ellipse_outline(cv, cx, cy, rx, ry, color, width=2):
    prev = None
    steps = 72
    for s in range(steps + 1):
        a = 2 * math.pi * s / steps
        p = (round(cx + rx * math.cos(a)), round(cy + ry * math.sin(a)))
        if prev is not None:
            cv.line(prev[0], prev[1], p[0], p[1], color, width)
        prev = p


def draw_palm(cv, x, y, s=1.0):
    cv.line(x, y, x, y - int(34 * s), INK, 3)
    for ang in (-150, -110, -70, -30, -170, -10):
        a = math.radians(ang)
        x2 = x + int(26 * s * math.cos(a))
        y2 = y - int(34 * s) + int(16 * s * math.sin(a))
        cv.line(x, y - int(34 * s), x2, y2, LAND_DARK, 3)
    cv.disc(x, y - int(36 * s), 4, INK)
    cv.disc(x - 4, y - int(36 * s) + 2, 3, INK)
    cv.disc(x + 4, y - int(36 * s) + 2, 3, INK)


def draw_mountain(cv, x, y, w, h):
    cv.fill_poly([(x - w, y), (x, y - h), (x + w, y)], LAND_DARK)
    cv.polyline([(x - w, y), (x, y - h), (x + w, y)], INK, 2)
    cap = int(h * 0.32)
    cv.fill_poly([(x - int(w * 0.32), y - h + cap),
                  (x, y - h),
                  (x + int(w * 0.32), y - h + cap)], SNOW)


def draw_house(cv, x, y):
    cv.fill_poly([(x, y), (x + 22, y), (x + 22, y + 16), (x, y + 16)],
                 PARCH)
    cv.polyline([(x, y), (x + 22, y), (x + 22, y + 16), (x, y + 16),
                 (x, y)], INK, 2)
    cv.fill_poly([(x - 2, y), (x + 11, y - 12), (x + 24, y)], RED)
    cv.polyline([(x - 2, y), (x + 11, y - 12), (x + 24, y)], INK, 2)
    cv.disc(x + 11, y + 9, 2, INK)


def draw_compass(cv, cx, cy):
    cv.disc(cx, cy, 58, PARCH)
    ellipse_outline(cv, cx, cy, 58, 58, INK, 3)
    ellipse_outline(cv, cx, cy, 44, 44, INK, 2)
    for ang, length, color in [(270, 56, INK), (90, 56, INK),
                               (0, 56, RED), (180, 56, RED),
                               (45, 40, INK), (135, 40, INK),
                               (225, 40, INK), (315, 40, INK)]:
        a = math.radians(ang)
        tip = (round(cx + length * math.cos(a)),
               round(cy + length * math.sin(a)))
        side = math.radians(ang + 90)
        wdt = 9 if length > 50 else 7
        b1 = (round(cx + wdt * math.cos(side)),
              round(cy + wdt * math.sin(side)))
        b2 = (round(cx - wdt * math.cos(side)),
              round(cy - wdt * math.sin(side)))
        cv.fill_poly([tip, b1, b2], color)
    cv.disc(cx, cy, 6, RED)
    draw_text(cv, cx - 7, cy - 74, "N", INK, 2)


def draw_ship(cv, cx, cy):
    cv.fill_poly([(cx - 52, cy), (cx + 52, cy), (cx + 38, cy + 26),
                  (cx - 38, cy + 26)], INK)
    cv.fill_poly([(cx - 52, cy), (cx + 52, cy), (cx + 38, cy + 26),
                  (cx - 38, cy + 26)], (122, 84, 52))
    cv.polyline([(cx - 52, cy), (cx + 52, cy), (cx + 38, cy + 26),
                 (cx - 38, cy + 26), (cx - 52, cy)], INK, 2)
    cv.line(cx - 18, cy, cx - 18, cy - 62, INK, 3)
    cv.line(cx + 22, cy, cx + 22, cy - 48, INK, 3)
    cv.fill_poly([(cx - 18, cy - 60), (cx - 18, cy - 8),
                  (cx + 8, cy - 34)], SAIL)
    cv.polyline([(cx - 18, cy - 60), (cx - 18, cy - 8),
                 (cx + 8, cy - 34)], INK, 2)
    cv.fill_poly([(cx + 22, cy - 46), (cx + 22, cy - 6),
                  (cx + 44, cy - 26)], SAIL)
    cv.polyline([(cx + 22, cy - 46), (cx + 22, cy - 6),
                 (cx + 44, cy - 26)], INK, 2)
    cv.fill_poly([(cx - 18, cy - 62), (cx - 2, cy - 58),
                  (cx - 18, cy - 54)], RED)


def draw_serpent(cv):
    pts = []
    for x in range(70, 215, 4):
        pts.append((x, 868 + int(12 * math.sin((x - 70) / 24.0))))
    cv.polyline(pts, SEA_DARK, 9)
    cv.polyline(pts, (96, 140, 152), 5)
    hx, hy = 214, 852
    cv.ellipse(hx, hy, 16, 12, (96, 140, 152))
    ellipse_outline(cv, hx, hy, 16, 12, INK, 2)
    cv.disc(hx + 5, hy - 4, 2, INK)
    cv.arc(hx + 2, hy + 1, 7, 0.15 * math.pi, 0.85 * math.pi, INK, 2)
    cv.line(hx - 8, hy - 10, hx - 12, hy - 20, INK, 2)
    cv.line(hx - 2, hy - 12, hx - 4, hy - 22, INK, 2)


def draw_wave(cv, x, y, s=1.0):
    cv.arc(x, y, int(9 * s), math.pi, 2 * math.pi, SEA_DARK, 2)
    cv.arc(x + int(18 * s), y, int(9 * s), math.pi, 2 * math.pi, SEA_DARK, 2)


def build():
    rng = random.Random(20261124)
    cv = Canvas()
    cv.fill(SEA)

    # Sea texture: scattered wave marks, kept out of the island.
    for _ in range(70):
        for _try in range(8):
            x = rng.randint(30, 990)
            y = rng.randint(120, 990)
            if not inside_poly(x, y, COAST):
                draw_wave(cv, x, y, rng.choice([0.8, 1.0, 1.2]))
                break

    # Island: sand rim, green heart, ink coastline.
    cv.fill_poly(COAST, SAND)
    cx = sum(p[0] for p in COAST) / len(COAST)
    cy = sum(p[1] for p in COAST) / len(COAST)
    inner = [(round(cx + (x - cx) * 0.86), round(cy + (y - cy) * 0.86))
             for x, y in COAST]
    cv.fill_poly(inner, LAND)
    cv.polyline(COAST, INK, 3, closed=True)

    # Lake and river, mountain to south bay.
    cv.ellipse(430, 335, 42, 28, SAND)
    cv.ellipse(430, 335, 34, 21, RIVER)
    ellipse_outline(cv, 430, 335, 34, 21, INK, 2)
    river = [(430, 356), (402, 440), (420, 540), (392, 640),
             (414, 720), (420, 782)]
    cv.polyline(river, RIVER, 6)
    cv.polyline(river, INK, 1)

    # Tea Kettle Falls where the river drops to the bay.
    for dx in (-8, 0, 8):
        cv.line(420 + dx, 748, 420 + dx, 778, SNOW, 3)
    cv.disc(412, 780, 3, SNOW)
    cv.disc(428, 781, 3, SNOW)

    # Mount Grumble and a pair of round-top trees.
    draw_mountain(cv, 400, 380, 52, 96)
    draw_mountain(cv, 452, 382, 40, 70)
    for tx, ty in [(610, 580), (350, 620), (460, 745)]:
        cv.line(tx, ty, tx, ty - 18, INK, 3)
        cv.disc(tx, ty - 26, 14, LAND_DARK)
        cv.disc(tx - 9, ty - 18, 9, LAND_DARK)
        cv.disc(tx + 9, ty - 18, 9, LAND_DARK)

    # Whispering Palms grove.
    draw_palm(cv, 520, 520)
    draw_palm(cv, 578, 492, 0.85)
    draw_palm(cv, 462, 566, 0.9)

    # The Very Lost Lagoon, east shore.
    cv.ellipse(690, 480, 50, 32, SAND)
    cv.ellipse(690, 480, 42, 25, RIVER)
    ellipse_outline(cv, 690, 480, 42, 25, INK, 2)

    # Captain's Beard Bay: a curl of water on the north-east coast.
    cv.arc(712, 332, 26, 0.3, 2.6, SEA_DARK, 3)
    cv.arc(712, 332, 18, 0.3, 2.6, SEA_DARK, 2)

    # Port Pickle: three little houses and an anchor on the south-west.
    draw_house(cv, 268, 700)
    draw_house(cv, 300, 716)
    draw_house(cv, 252, 726)
    cv.disc(330, 748, 5, INK)
    cv.line(330, 743, 330, 764, INK, 3)
    cv.arc(330, 762, 8, 0.1 * math.pi, 0.9 * math.pi, INK, 3)
    cv.line(322, 748, 338, 748, INK, 3)

    # The Giggling Shoals: three rocks that cannot keep a straight face.
    for rx, ry, rr in [(806, 690, 12), (836, 700, 15), (820, 716, 10)]:
        cv.disc(rx, ry, rr, SAND)
        ellipse_outline(cv, rx, ry, rr, rr, INK, 2)
        cv.disc(rx - 4, ry - 3, 1, INK)
        cv.disc(rx + 4, ry - 3, 1, INK)
        cv.arc(rx, ry + 1, 5, 0.15 * math.pi, 0.85 * math.pi, INK, 2)

    # Dotted route from Port Pickle to the X.
    route = [(330, 700), (450, 650), (560, 630), (618, 606)]
    for a, b in zip(route, route[1:]):
        cv.dotted(a[0], a[1], b[0], b[1], INK, 4, 7)

    # X Marks the Spot.
    cv.line(618, 578, 662, 622, INK, 12)
    cv.line(662, 578, 618, 622, INK, 12)
    cv.line(618, 578, 662, 622, RED, 7)
    cv.line(662, 578, 618, 622, RED, 7)
    ellipse_outline(cv, 640, 600, 56, 56, INK, 2)

    # Compass rose, ship, and serpent in the open sea.
    draw_compass(cv, 880, 190)
    draw_ship(cv, 880, 820)
    draw_serpent(cv)

    # Title cartouche.
    cv.fill_poly([(82, 26), (942, 26), (942, 96), (82, 96)], PARCH)
    cv.polyline([(82, 26), (942, 26), (942, 96), (82, 96), (82, 26)],
                INK, 3)
    cv.polyline([(90, 34), (934, 34), (934, 88), (90, 88), (90, 34)],
                INK, 1)
    draw_text_centered(cv, 512, 44, "THE ISLE OF HALF-FORGOTTEN THINGS",
                       INK, 4)

    # Labels: eight named places, all spelled out where a traveller
    # could actually find them.
    draw_text_centered(cv, 415, 242, "MOUNT GRUMBLE", INK, 3)
    draw_text_centered(cv, 560, 428, "WHISPERING PALMS", INK, 3)
    draw_text_centered(cv, 470, 806, "TEA KETTLE FALLS", INK, 2)
    draw_text_centered(cv, 690, 522, "THE VERY LOST LAGOON", INK, 2)
    draw_text_centered(cv, 790, 285, "CAPTAIN'S BEARD BAY", INK, 2)
    draw_text_centered(cv, 820, 738, "THE GIGGLING SHOALS", INK, 2)
    draw_text_centered(cv, 250, 776, "PORT PICKLE", INK, 3)
    draw_text_centered(cv, 640, 678, "X MARKS THE SPOT", INK, 3)

    # Sea jokes and the scale bar. The seagull warning lives in the
    # open water west of the island, clear of the Port Pickle label.
    draw_text_centered(cv, 130, 330, "HERE BE SLIGHTLY", INK, 2)
    draw_text_centered(cv, 130, 352, "RUDE SEAGULLS", INK, 2)
    draw_text_centered(cv, 860, 878, "THE GOOD SHIP SOMEDAY", INK, 2)
    draw_text(cv, 50, 138, "3 LEAGUES, GIVE OR TAKE", INK, 2)
    cv.line(50, 166, 200, 166, INK, 3)
    cv.line(50, 160, 50, 172, INK, 2)
    cv.line(125, 160, 125, 172, INK, 2)
    cv.line(200, 160, 200, 172, INK, 2)
    draw_text(cv, 44, 178, "0", INK, 2)
    draw_text(cv, 194, 178, "3", INK, 2)

    # A word to the curator, and the map's own small print.
    draw_text_centered(cv, 512, 938,
                       "DEAR CURATOR: EVERY NAME HERE WAS INVENTED "
                       "THIS MORNING.", INK, 2)
    draw_text_centered(cv, 512, 962, "THE X IS REAL. PROBABLY.", INK, 2)

    # Burnt-paper edge and a little age.
    cv.polyline([(8, 8), (1016, 8), (1016, 1016), (8, 1016), (8, 8)],
                INK, 5)
    cv.polyline([(20, 20), (1004, 20), (1004, 1004), (20, 1004),
                 (20, 20)], INK, 1)
    for _ in range(2200):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        i = (y * W + x) * 3
        r, g, b = cv.px[i], cv.px[i + 1], cv.px[i + 2]
        cv.px[i] = max(r - 14, 0)
        cv.px[i + 1] = max(g - 12, 0)
        cv.px[i + 2] = max(b - 10, 0)
    return cv


def main():
    cv = build()
    if os.path.isdir("/output"):
        path = "/output/entry.png"
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "entry.png")
    size = write_png(path, cv.px)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))
    if size > 1048576:
        print("WARNING: over the 1 MiB gate", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
