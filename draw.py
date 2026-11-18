#!/usr/bin/env python3
"""THE DAILY ATLAS — front page for Tuesday 17 November 2026.

Renders a 1024x1024 newspaper front page carrying 42 stories, applies a
paper-texture pass, and writes entry.png next to this file (JPEG bytes
under the .png name, per the competition rules).  Also renders
one procedural artwork panel (panels/proc-bahrain.png) at build time.
"""

import hashlib
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
PANELS = os.path.join(HERE, "panels")
ENTRY = os.path.join(HERE, "entry.png")

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
SERIF_BOLD = FONT_DIR + "DejaVuSerif-Bold.ttf"
SERIF = FONT_DIR + "DejaVuSerif.ttf"
SERIF_ITALIC = FONT_DIR + "DejaVuSerif-Italic.ttf"
SANS_BOLD = FONT_DIR + "DejaVuSans-Bold.ttf"
SANS = FONT_DIR + "DejaVuSans.ttf"

W = H = 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 248, 241)
CARD = (255, 255, 252)
INK = (18, 24, 38)
GREY = (102, 106, 114)
ACCENT = (23, 40, 72)
NAVY = (44, 66, 102)
BORDER = (198, 202, 212)

CONTINENTS = {
    "Americas": (172, 62, 42),
    "Europe": (58, 84, 128),
    "Mideast": (190, 124, 40),
    "Africa": (122, 106, 52),
    "Asia": (116, 80, 148),
    "Oceania": (44, 124, 134),
}

CLIPS = []
DRAWN = set()

_font_cache = {}


def F(path, size):
    if path == SERIF_ITALIC and not os.path.exists(path):
        path = SERIF
    key = (path, round(float(size), 2))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ---------------------------------------------------------------- helpers
def wrap(text, font, max_width, draw):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def block(draw, x, y, w, text, font, line_height, max_y):
    """Draw wrapped lines from y while each still fits at or below max_y."""
    lines = wrap(text, font, w, draw)
    for line in lines:
        if y + line_height > max_y + 1e-6:
            CLIPS.append((text[:32], round(y, 1), round(max_y, 1)))
            break
        draw.text((x, y), line, font=font, fill=INK)
        y += line_height
    return y


def _crop_cover(src, w, h, fx, fy):
    sw, sh = src.size
    target = w / h
    if sw / sh > target:                       # source too wide
        new_w = max(1, int(round(sh * target)))
        left = int(round((sw - new_w) * fx))
        left = max(0, min(sw - new_w, left))
        box = (left, 0, left + new_w, sh)
    else:                                      # source too tall
        new_h = max(1, int(round(sw / target)))
        top = int(round((sh - new_h) * fy))
        top = max(0, min(sh - new_h, top))
        box = (0, top, sw, top + new_h)
    return src.crop(box).resize((w, h), Image.LANCZOS)


def panel(img, path, x, y, w, h, fx=0.5):
    src = Image.open(path).convert("RGB")
    img.paste(_crop_cover(src, w, h, fx, 0.5), (x, y))
    ImageDraw.Draw(img).rectangle(
        [x, y, x + w - 1, y + h - 1], outline=INK, width=1)


def paste_fit(img, path, x, y, w, h, fy=0.5):
    src = Image.open(path).convert("RGB")
    img.paste(_crop_cover(src, w, h, 0.5, fy), (x, y))


def contain_fit(img, path, x, y, w, h):
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    new_w = w
    new_h = max(1, int(round(sh * w / sw)))
    scaled = src.resize((new_w, new_h), Image.LANCZOS)
    img.paste((255, 255, 255), (x, y, x + w, y + h))
    img.paste(scaled, (x, y + (h - new_h) // 2))


def chip(draw, cx, cy, r, n, fill):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    f = F(SANS_BOLD, max(6.0, r * 1.12))
    draw.text((cx, cy + 0.2), str(n), font=f, fill="white", anchor="mm")


# ---------------------------------------------------------------- story data
FEATURED = [
    dict(n=1, kicker="UKRAINE · KERCH BRIDGE",
         head="Ukraine brings down a span of Putin's Crimea bridge",
         summ=("Kyiv's seven-stage operation dropped the road arch into the Kerch "
               "Strait overnight; two killed, the road shut, rail on one track. "
               "Moscow vows to rebuild it."),
         art="ultra-kerch.png", fx=0.5, tag="ROAD ARCH DOWN", tagcol=ACCENT),
    dict(n=2, kicker="IRAN · BAHRAIN / QESHM",
         head="Iran drones at Bahrain; US strikes Qeshm",
         summ=("Drones hit a US radar at Sheikh Isa — a third attack in five days; "
               "US jets struck an IRGC missile site on Qeshm Island. Two tankers "
               "ablaze in Hormuz; a third US carrier arrives. Tehran denies the "
               "‘dirty bomb’ plot report."),
         art="proc-bahrain.png", fx=0.5, tag="DRONES AT BAHRAIN", tagcol=NAVY),
    dict(n=3, kicker="ASIA · APEC SUMMIT",
         head="Trump lands in Manila; summit set for Thursday",
         summ=("ASEAN and Quad critical-minerals deals signed in Manila; on Thursday "
               "in Shenzhen, the first Trump–Xi–Putin summit: nuclear arms, Ukraine "
               "and Iran on the agenda."),
         art="ultra-shenzhen.png", fx=0.5, tag="MANILA FIRST", tagcol=(16, 22, 34)),
]

GRID = [
    dict(n=4, kicker="UKRAINE · WAR",
         head="Russian missiles hit Kyiv's two Dnipro bridges",
         summ="Heat and water cut across the capital.",
         kind="img", art="ultra-dnipro.png", fy=0.5),
    dict(n=5, kicker="MARKETS · TECH",
         head="Nvidia revenue doubles to $115.8bn; guides $130bn",
         summ="First earnings since Huang's exit.",
         kind="img", art="ultra-nvidia.png", fy=0.5),
    dict(n=6, kicker="UNITED STATES · MARKETS",
         head="Dow falls 849 points in AI selloff",
         summ="Slide deepened on NSA outage report.",
         kind="proc", proc="dow"),
    dict(n=7, kicker="UNITED STATES · BANKING",
         head="JPMorgan blames software bug for outage",
         summ="Payments and Zelle slowed; not hackers.",
         kind="imgf", art="ultra-jpmorgan.png"),
    dict(n=8, kicker="SCIENCE · SPACE",
         head="Vulcan rocket fails; 40 Amazon satellites lost",
         summ="Anomaly minutes after liftoff, Florida.",
         kind="img", art="ultra-vulcan.png", fy=0.55),
    dict(n=9, kicker="JAPAN · AIRSPACE",
         head="Japan scrambles jets, protests to Moscow",
         summ="Suspected Russian jets, early Tuesday.",
         kind="proc", proc="jets"),
    dict(n=10, kicker="AMERICAS · HEALTH",
         head="US loses measles-free status after 26 years",
         summ="PAHO: endemic again; 5,412 cases in 2026.",
         kind="proc", proc="measles"),
    dict(n=11, kicker="AFRICA · HEALTH",
         head="Ebola cases double in three months to 11,000+",
         summ="WHO counts ~5,400 dead in DR Congo.",
         kind="proc", proc="ebola"),
    dict(n=12, kicker="FRANCE · LABOUR",
         head="France: 146,000 march in public-sector pay strike",
         summ="Third unified stoppage since September.",
         kind="proc", proc="strike"),
    dict(n=13, kicker="GLOBAL · CLIMATE",
         head="COP31 enters final days split on fossil fuels",
         summ="Phase-out and $120bn goal split talks.",
         kind="proc", proc="cop"),
    dict(n=14, kicker="ISRAEL · POLITICS",
         head="Knesset elects Eisenkot ally as speaker",
         summ="Kahana wins 66–52; six-hour filibuster.",
         kind="proc", proc="knesset"),
    dict(n=15, kicker="INDIA · CLIMATE",
         head="Cyclone Akvan takes aim at India's east coast",
         summ="Third storm in weeks; landfall ~20 Nov.",
         kind="proc", proc="cyclone"),
]

BRIEFS = [
    "Mongolia's president quits over graft claims",
    "Five EU states plan Rwanda return hub",
    "Xi–Carney: China cuts $280m of Canada tariffs",
    "US closes AI-chip loophole; Singapore seeks access",
    "Pentagon fails its ninth straight audit",
    "Geneva talks on killer robots open",
    "West urges Israel to open Gaza crossings",
    "Houthis close in on Aden as Saudis pull back",
    "UK sanctions eight settlement builders; settler kills woman, 72",
    "Russian An-12 crash in Siberia kills all 19 aboard",
    "Bus plunges into Uttarakhand ravine; at least 6 dead",
    "17 killed in two South Africa shootings",
    "Bangladesh police tear-gas garment workers",
    "Turkey seizes opposition broadcaster Sözcü TV",
    "Serbia: student-led parliament first meets",
    "NASA marks Voyager 1's light-day approach; public shines lights",
    "Dhoni retires from the IPL, turns CSK mentor",
    "Brazil rout Singapore 7–0; Vinícius hat-trick",
    "Two trains collide near Prague; 46 injured",
    "Moldova shuts its airspace over a Shahed-type drone",
    "Gaza winter rains flood tent shelters — UN",
    "Pakistan seeks to revive US–Iran talks",
    "IMF lines up ~$1.6bn more for Ukraine",
    "Jordan and Iraq block Telegram",
    "UN: ~4m displaced Syrians have returned home",
    "WHO warns superbugs could kill 39m+ people",
    "Fela Kuti, first African in the Rock & Roll Hall of Fame",
]

PINS = {
    1: (37.0, 45.4, 0, 0), 2: (50.57, 26.23, 6, 6), 3: (121.0, 14.6, -6, -12),
    4: (30.5, 50.4, 8, -2), 5: (-122.0, 37.4, -8, -6), 6: (-74, 40.7, -2, -10),
    7: (-74, 40.7, 12, 8), 8: (-80.6, 28.5, 0, 6), 9: (138, 37, 0, 0),
    10: (-98, 39, 0, 0), 11: (23, -2, 0, 0), 12: (2.35, 48.9, -12, -4),
    13: (30.7, 36.9, 4, -10), 14: (35.2, 31.8, -14, -4), 15: (88, 17, 6, 2),
    16: (106.9, 47.9, 0, -6), 17: (30, -2, 10, 10), 18: (-75.7, 45.4, -6, 10),
    19: (103.8, 1.35, 2, 10), 20: (-77, 38.9, 14, 12), 21: (6.1, 46.2, -8, -8),
    22: (34.3, 31.4, -12, 6), 23: (45.0, 12.8, 6, 6), 24: (-0.1, 51.5, -10, -6),
    25: (86.1, 54.7, 0, -6), 26: (79.3, 30.1, 8, 4), 27: (25, -29, 0, 4),
    28: (90.4, 23.8, 8, -6), 29: (28.9, 41.0, -6, -12), 30: (20.5, 44.8, -4, 8),
    32: (80.3, 13.1, -2, 8), 33: (103.8, 1.35, 16, -6),
    34: (14.4, 50.1, 6, -8), 35: (28.8, 47.0, -14, 8), 36: (34.3, 31.4, 4, 14),
    37: (73.0, 33.7, 6, -4), 38: (30.5, 50.4, -16, 10), 39: (40.0, 32.5, 0, 12),
    40: (38.0, 35.0, 12, -2), 41: (6.1, 46.2, 12, 8), 42: (3.4, 6.5, 0, 6),
}

REGION = {
    1: "Europe", 2: "Mideast", 3: "Asia", 4: "Europe", 5: "Americas",
    6: "Americas", 7: "Americas", 8: "Americas", 9: "Asia", 10: "Americas",
    11: "Africa", 12: "Europe", 13: "Mideast", 14: "Mideast", 15: "Asia",
    16: "Asia", 17: "Africa", 18: "Americas", 19: "Asia", 20: "Americas",
    21: "Europe", 22: "Mideast", 23: "Mideast", 24: "Europe", 25: "Asia",
    26: "Asia", 27: "Africa", 28: "Asia", 29: "Mideast", 30: "Europe",
    32: "Asia", 33: "Asia", 34: "Europe", 35: "Europe", 36: "Mideast",
    37: "Asia", 38: "Europe", 39: "Mideast", 40: "Mideast", 41: "Europe",
    42: "Africa",
}

SPANS = {
    0: [(8, 11), (27, 30), (48, 50), (59, 61)],
    1: [(1, 6), (9, 23), (26, 31), (44, 70)],
    2: [(1, 7), (8, 25), (27, 31), (38, 70)],
    3: [(2, 8), (9, 26), (28, 30), (37, 70)],
    4: [(3, 8), (10, 26), (31, 31), (37, 70)],
    5: [(5, 8), (11, 25), (32, 33), (34, 70)],
    6: [(10, 24), (32, 32), (33, 69)],
    7: [(10, 23), (32, 45), (46, 66)],
    8: [(10, 23), (33, 44), (45, 66)],
    9: [(10, 23), (33, 43), (44, 63)],
    10: [(10, 22), (32, 38), (39, 47), (48, 64)],
    11: [(11, 21), (33, 53), (55, 62)],
    12: [(11, 17), (33, 48), (49, 53), (54, 60)],
    13: [(13, 16), (33, 45), (49, 52), (55, 60)],
    14: [(11, 11), (34, 45), (50, 51), (56, 58)],
    15: [(34, 44), (46, 47), (56, 58), (60, 61)],
    16: [(34, 45), (56, 62)],
    17: [(35, 45), (58, 63)],
    18: [(17, 22), (35, 45), (58, 64)],
    19: [(17, 23), (37, 44), (60, 66)],
    20: [(18, 23), (38, 44), (64, 68)],
    21: [(18, 24), (38, 44), (60, 67)],
    22: [(18, 24), (39, 44), (46, 46), (60, 68)],
    23: [(18, 24), (39, 44), (46, 46), (59, 68)],
    24: [(18, 23), (39, 44), (46, 46), (59, 67)],
    25: [(18, 23), (40, 44), (60, 66)],
    26: [(18, 22), (40, 43), (61, 65)],
    27: [(18, 22), (40, 43), (61, 65), (71, 71)],
    28: [(19, 21), (40, 42), (62, 64)],
    29: [(19, 21), (40, 42), (62, 63), (71, 72)],
    30: [(19, 20), (63, 63)],
    31: [(19, 20), (70, 71)],
    32: [(19, 19)],
    33: [(19, 19)],
    34: [(19, 19)],
    35: [(19, 19)],
    36: [(19, 19)],
}

LEGEND = ["Americas", "Europe", "Mideast", "Africa", "Asia", "Oceania"]


# ---------------------------------------------------------------- gulf panel
def make_gulf_panel(path):
    Wp, Hp = 634, 184
    im = Image.new("RGB", (Wp, Hp), (163, 192, 205))
    d = ImageDraw.Draw(im)
    LAND_A = (224, 207, 170)
    LAND_B = (208, 188, 146)

    d.polygon([(300, 0), (634, 0), (634, 96), (540, 88), (452, 104),
               (392, 78), (348, 44), (318, 12)], fill=LAND_B)
    d.polygon([(0, 184), (0, 118), (84, 96), (150, 82), (206, 92), (238, 118),
               (252, 150), (258, 184)], fill=LAND_A)
    d.polygon([(196, 90), (214, 76), (226, 92), (216, 108), (200, 104)],
              fill=LAND_A)
    d.ellipse([222, 92, 234, 104], fill=LAND_A)
    d.polygon([(398, 66), (446, 60), (452, 70), (404, 78)], fill=LAND_B)

    for t in range(0, 100, 9):
        px = 420 + (228 - 420) * t / 100.0
        py = 52 + (96 - 52) * t / 100.0 - 16 * math.sin(math.pi * t / 100.0)
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(90, 96, 104))

    for (bx, by, col) in ((228, 98, ACCENT), (424, 68, (214, 110, 30))):
        for k in range(8):
            ang = math.radians(k * 45)
            d.line([bx, by, bx + 13 * math.cos(ang), by + 13 * math.sin(ang)],
                   fill=col, width=3)
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=col)

    d.text((528, 22), "IRAN", font=F(SANS_BOLD, 17), fill=(96, 82, 54), anchor="mm")
    d.multiline_text((66, 106), "SAUDI\nARABIA", font=F(SANS_BOLD, 12),
                     fill=(120, 104, 70), spacing=2)
    d.text((318, 116), "PERSIAN GULF", font=F(SANS_BOLD, 12), fill=(70, 96, 116),
           anchor="mm")
    d.text((424, 88), "QESHM", font=F(SANS_BOLD, 11), fill=(150, 76, 20),
           anchor="ma")

    im.save(path)


# ---------------------------------------------------------------- proc banners
def proc_banner(img, d, kind, x, y0):
    """Draw a procedural 238x40 banner on its own layer, then paste it.

    Drawing into a strip-sized layer keeps every shape and glyph inside the
    banner so nothing bleeds onto the card below it.
    """
    layer = Image.new("RGB", (238, 40), PAPER)
    d = ImageDraw.Draw(layer)
    _proc_shapes(d, kind, 0, 0)
    img.paste(layer, (x, y0))


def _proc_shapes(d, kind, x, y0):
    cy = y0 + 20
    strip = (x, y0, x + 237, y0 + 39)

    if kind == "dow":
        d.rectangle(strip, fill=(24, 26, 34))
        pts = [(x + 8, y0 + 6), (x + 42, y0 + 12), (x + 74, y0 + 20),
               (x + 102, y0 + 27), (x + 126, y0 + 34)]
        d.line(pts, fill=(240, 90, 80), width=3)
        d.polygon([(x + 126, y0 + 34), (x + 116, y0 + 32), (x + 124, y0 + 24)],
                  fill=(240, 90, 80))
        d.text((x + 140, cy), "DOW −849", font=F(SANS_BOLD, 15),
               fill=(240, 90, 80), anchor="lm")

    elif kind == "jets":
        d.rectangle(strip, fill=(150, 182, 214))
        d.rectangle([x, y0 + 26, x + 238, y0 + 40], fill=(128, 164, 200))
        for (jx, jy, s) in ((x + 26, y0 + 8, 1.0), (x + 96, y0 + 16, 0.8)):
            pts = [(jx + 0 * s, jy + 0 * s), (jx + 44 * s, jy + 7 * s),
                   (jx + 30 * s, jy + 10 * s), (jx + 34 * s, jy + 16 * s),
                   (jx + 12 * s, jy + 13 * s), (jx + 4 * s, jy + 18 * s),
                   (jx + 6 * s, jy + 9 * s)]
            d.polygon(pts, fill=(52, 58, 66))
            d.line([(jx - 16, jy + 15 * s), (jx + 2, jy + 12 * s)],
                   fill=(240, 244, 248), width=2)
        d.polygon([(x + 168, y0 + 18), (x + 218, y0 + 25), (x + 200, y0 + 29),
                   (x + 206, y0 + 36), (x + 182, y0 + 32), (x + 174, y0 + 38),
                   (x + 176, y0 + 27)], fill=ACCENT)
        d.line([(x + 146, y0 + 34), (x + 168, y0 + 27)], fill=ACCENT, width=2)
        d.line([(x + 150, y0 + 38), (x + 170, y0 + 31)], fill=(240, 120, 90),
               width=2)

    elif kind == "measles":
        d.rectangle(strip, fill=(250, 246, 238))
        d.rectangle([x + 22, y0 + 8, x + 34, y0 + 34], fill=ACCENT)
        d.rectangle([x + 15, y0 + 15, x + 41, y0 + 27], fill=ACCENT)
        d.text((x + 56, cy), "ENDEMIC AGAIN", font=F(SANS_BOLD, 13), fill=INK,
               anchor="lm")

    elif kind == "ebola":
        d.rectangle(strip, fill=(58, 20, 24))
        gx, gy, col = x + 30, cy, (240, 170, 150)
        for k in range(8):
            ang = math.radians(k * 45)
            ex, ey = gx + 13 * math.cos(ang), gy + 13 * math.sin(ang)
            d.line([gx, gy, ex, ey], fill=col, width=2)
            d.ellipse([ex - 3, ey - 3, ex + 3, ey + 3], fill=col)
        d.ellipse([gx - 8, gy - 8, gx + 8, gy + 8], fill=col)
        d.text((x + 58, cy), "CASES DOUBLED", font=F(SANS_BOLD, 13), fill="white",
               anchor="lm")

    elif kind == "strike":
        d.rectangle(strip, fill=(240, 238, 230))
        for i in range(6):
            hx = x + 18 + i * 22
            d.ellipse([hx - 6, y0 + 13, hx + 6, y0 + 25], fill=INK)
            d.pieslice([hx - 9, y0 + 22, hx + 9, y0 + 40], 180, 360, fill=INK)
        d.line([(x + 168, y0 + 22), (x + 168, y0 + 40)], fill=INK, width=2)
        d.rectangle([x + 146, y0 + 3, x + 232, y0 + 23], fill="white",
                    outline=ACCENT, width=2)
        d.text((x + 189, y0 + 13), "PAY NOW", font=F(SANS_BOLD, 11), fill=ACCENT,
               anchor="mm")

    elif kind == "cop":
        d.rectangle(strip, fill=(26, 84, 80))
        d.text((x + 16, cy), "COP31", font=F(SANS_BOLD, 19), fill="white",
               anchor="lm")
        d.line([(x + 118, y0 + 28), (x + 148, y0 + 12)], fill=(140, 230, 200),
               width=3)
        d.polygon([(x + 148, y0 + 12), (x + 138, y0 + 13), (x + 146, y0 + 21)],
                  fill=(140, 230, 200))
        d.line([(x + 118, y0 + 14), (x + 148, y0 + 30)], fill=(240, 160, 90),
               width=3)
        d.polygon([(x + 148, y0 + 30), (x + 138, y0 + 29), (x + 146, y0 + 21)],
                  fill=(240, 160, 90))
        d.text((x + 162, cy), "SPLIT TALKS", font=F(SANS_BOLD, 11), fill="white",
               anchor="lm")

    elif kind == "knesset":
        d.rectangle(strip, fill=NAVY)
        d.text((x + 18, cy), "66–52", font=F(SANS_BOLD, 19), fill="white",
               anchor="lm")
        d.text((x + 118, cy), "SPEAKER VOTE", font=F(SANS_BOLD, 11), fill="white",
               anchor="lm")

    elif kind == "cyclone":
        d.rectangle(strip, fill=(44, 92, 140))
        sx, sy = x + 44, cy
        for r in (6, 11, 16):
            box = [sx - r, sy - r, sx + r, sy + r]
            d.arc(box, 20, 290, fill="white", width=3)
            d.arc(box, 200, 110, fill=(170, 210, 240), width=3)
        d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill="white")
        d.text((x + 84, cy), "CYCLONE AKVAN", font=F(SANS_BOLD, 13), fill="white",
               anchor="lm")


# ---------------------------------------------------------------- page
def draw_page():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ---- masthead
    d.text((24, 4), "THE WORLD'S NEWS IN ONE PICTURE", font=F(SANS_BOLD, 12.5),
           fill=ACCENT)
    d.text((1000, 4), "42 STORIES · ONE PAGE", font=F(SANS_BOLD, 12.5), fill=INK,
           anchor="ra")

    title_size = 40
    for s in range(66, 39, -2):
        f = F(SERIF_BOLD, s)
        if d.textlength("THE DAILY ATLAS", font=f) <= 900:
            title_size = s
            break
    d.text((512, 16), "THE DAILY ATLAS", font=F(SERIF_BOLD, title_size),
           fill=INK, anchor="ma")

    r1 = 16 + title_size + 7
    d.rectangle([24, r1, 1000, r1 + 2], fill=ACCENT)
    d.rectangle([24, r1 + 5, 1000, r1 + 5], fill=ACCENT)

    dy = r1 + 10
    d.text((512, dy), "Tuesday 17 November 2026", font=F(SERIF_BOLD, 25),
           fill=ACCENT, anchor="ma")

    sy = dy + 33
    d.text((24, sy), "EVERY STORY REPORTED ON THE DAY", font=F(SANS, 10.5),
           fill=GREY)
    d.text((1000, sy), "TUESDAY EDITION · NO. 17", font=F(SANS_BOLD, 11), fill=INK,
           anchor="ra")

    fy = sy + 18

    # ---- featured row
    for i, st in enumerate(FEATURED):
        x = 24 + i * 329
        y = fy
        d.rectangle([x, y, x + 317, y + 232], fill=CARD, outline=BORDER, width=1)
        if st["art"].startswith("proc"):
            path = os.path.join(PANELS, st["art"])
        else:
            path = os.path.join(ASSETS, st["art"])
        panel(img, path, x, y, 317, 84, st["fx"])

        d = ImageDraw.Draw(img)
        d.rectangle([x, y + 58, x + 317, y + 84], fill=st["tagcol"])
        stub = INK if st["tagcol"] == ACCENT else ACCENT
        d.rectangle([x, y + 58, x + 4, y + 84], fill=stub)
        d.text((x + 14, y + 71), st["tag"], font=F(SANS_BOLD, 12), fill="white",
               anchor="lm")

        chip(d, x + 20, y + 98, 10, st["n"], ACCENT)
        d.text((x + 38, y + 98), st["kicker"], font=F(SANS_BOLD, 10.5), fill=ACCENT,
               anchor="lm")

        end = block(d, x + 10, y + 110, 297, st["head"], F(SERIF_BOLD, 19), 20,
                    y + 170)
        block(d, x + 10, end + 2, 297, st["summ"], F(SERIF, 10.5), 13, y + 229)
        DRAWN.add(st["n"])

    # ---- grid
    gy = fy + 232 + 16
    d = ImageDraw.Draw(img)
    d.rectangle([24, gy - 8, 1000, gy - 8], fill=INK)

    for i, st in enumerate(GRID):
        c, r = i % 4, i // 4
        x = 24 + c * 246
        y0 = gy + r * 104

        d.rectangle([x, y0, x + 238, y0 + 94], fill=CARD, outline=BORDER, width=1)

        if st["kind"] == "img":
            paste_fit(img, os.path.join(ASSETS, st["art"]), x, y0, 238, 40,
                      st["fy"])
            d = ImageDraw.Draw(img)
        elif st["kind"] == "imgf":
            contain_fit(img, os.path.join(ASSETS, st["art"]), x, y0, 238, 40)
            d = ImageDraw.Draw(img)
        else:
            proc_banner(img, d, st["proc"], x, y0)

        chip(d, x + 14, y0 + 48, 6.5, st["n"], ACCENT)
        d.text((x + 26, y0 + 48), st["kicker"], font=F(SANS_BOLD, 8.5),
               fill=ACCENT, anchor="lm")
        end = block(d, x + 8, y0 + 56, 222, st["head"], F(SERIF_BOLD, 12.5), 13,
                    y0 + 82)
        block(d, x + 8, end + 1, 222, st["summ"], F(SERIF, 9), 10.5, y0 + 94)
        DRAWN.add(st["n"])

    # ---- bottom band
    by = gy + 3 * 94 + 2 * 10 + 14
    d.rectangle([24, by, 1000, by], fill=INK)
    hy = by + 8

    d.text((24, hy), "WHERE IT HAPPENED", font=F(SANS_BOLD, 12), fill=ACCENT)

    widths = [d.textlength(n, font=F(SANS, 8.5)) for n in LEGEND]
    total = sum(widths) + 25 * 6 - 14
    lx = 512 - total / 2.0
    for name, lw in zip(LEGEND, widths):
        d.ellipse([lx, hy + 2, lx + 7, hy + 9], fill=CONTINENTS[name])
        d.text((lx + 11, hy), name, font=F(SANS, 8.5), fill=INK)
        lx += 11 + lw + 14

    d.text((1000, hy), "ALSO ON TUESDAY 17 NOVEMBER", font=F(SANS_BOLD, 12),
           fill=INK, anchor="ra")

    my = hy + 22

    # ---- briefs sizing
    col_x = [348, 564, 780]
    LIMIT_Y = 970
    chosen = None
    for size in (10.5, 10.0, 9.5):
        lh = size + 2.3
        font = F(SANS, size)
        heights = [len(wrap(b, font, 184, d)) * lh for b in BRIEFS]
        best = None
        for a in range(7, 12):
            for b2 in range(7, 12):
                c3 = len(heights) - a - b2
                if not 7 <= c3 <= 11:
                    continue
                sums = [sum(heights[:a]), sum(heights[a:a + b2]),
                        sum(heights[a + b2:])]
                cols = [sums[0] + 2.5 * (a - 1), sums[1] + 2.5 * (b2 - 1),
                        sums[2] + 2.5 * (c3 - 1)]
                spread = max(cols) - min(cols)
                if best is None or spread < best[0]:
                    best = (spread, a, b2, cols)
        if best is None:
            continue
        band_h = int(max(best[3]))
        if my + band_h <= LIMIT_Y:
            chosen = (size, lh, best, band_h)
            break
    if chosen is None:
        raise RuntimeError("no brief size fits the band")

    bsize, blh, (spread, split1, split2, cols_h), band_h = chosen
    bfont = F(SANS, bsize)
    BRIEF_SIZE[0] = bsize

    # ---- map (LEFT)
    mapx, mapy, mapw = 24, my, 300
    maph = band_h
    d.rectangle([mapx, mapy, mapx + mapw, mapy + maph], fill=(240, 238, 230),
                outline=BORDER, width=1)

    cw = mapw / 73.0
    ch = maph / 37.0

    def region_of(lon, lat):
        if lon < -30:
            return "Americas"
        if lon >= 112 and lat < -11:
            return "Oceania"
        if lon >= 52:
            return "Asia"
        if lat >= 42:
            return "Europe"
        if lon >= 20 and lat >= 12:
            return "Mideast"
        if lat >= 35:
            return "Europe"
        return "Africa"

    muted = {k: tuple(int(round(c * 0.48 + p * 0.52))
                      for c, p in zip(v, PAPER)) for k, v in CONTINENTS.items()}

    for r in range(37):
        spans = SPANS.get(r, [])
        if not spans:
            continue
        clat = 78 - (r + 0.5) * (134.0 / 37.0)
        for (c0, c1) in spans:
            for c in range(c0, c1 + 1):
                clon = -168 + (c + 0.5) * (360.0 / 73.0)
                col = muted[region_of(clon, clat)]
                d.rectangle([mapx + c * cw, mapy + r * ch,
                             mapx + (c + 1) * cw + 0.6,
                             mapy + (r + 1) * ch + 0.6], fill=col)

    for n, (lon, lat, dx, dy) in PINS.items():
        px = mapx + (lon + 168) / 360.0 * mapw + dx
        py = mapy + (78 - lat) / 134.0 * maph + dy
        chip(d, px, py, 7, n, CONTINENTS[REGION[n]])

    # ---- briefs (RIGHT)
    idx = 0
    for ci, count in enumerate((split1, split2, len(BRIEFS) - split1 - split2)):
        x = col_x[ci]
        y = my
        for j in range(count):
            st = BRIEFS[idx]
            idx += 1
            num = 16 + idx - 1
            chip(d, x + 7, y + 6, 6.5, num, ACCENT)
            lines = wrap(st, bfont, 184, d)
            for line in lines:
                d.text((x + 18, y), line, font=bfont, fill=INK)
                y += blh
            if j < count - 1:
                for px in range(0, 201, 5):
                    d.point((x + px, y + 1), fill=BORDER)
                y += 2.5
            DRAWN.add(num)

    # ---- footer
    fy2 = my + band_h + 12
    d.rectangle([24, fy2, 1000, fy2], fill=INK)
    d.text((512, fy2 + 4),
           "And the day's quieter line: Fela Kuti becomes the first African in "
           "the Rock & Roll Hall of Fame.",
           font=F(SERIF_ITALIC, 10), fill=INK, anchor="ma")
    d.text((512, fy2 + 23),
           "Every story happened or was first reported on Tuesday 17 November "
           "2026 · Disputed claims are attributed · Sources: Reuters · AP · AFP "
           "· BBC · Al Jazeera · CNN · NPR · UN News",
           font=F(SANS, 8.5), fill=GREY, anchor="ma")

    return img, band_h


# ---------------------------------------------------------------- texture
def paper_texture(img):
    blurred = img.filter(ImageFilter.GaussianBlur(0.35))
    a = (np.asarray(img, dtype=np.float32) * 0.5
         + np.asarray(blurred, dtype=np.float32) * 0.5)

    rng = np.random.default_rng(7)

    # low-frequency mottling
    gw, gh = 1024 // 12 + 2, 1024 // 12 + 2
    grid = rng.standard_normal((gh, gw)).astype(np.float32)
    grid = (grid - grid.min()) / (grid.max() - grid.min()) * 255.0
    m_img = Image.fromarray(grid.astype(np.uint8), "L").resize(
        (1024, 1024), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    m = np.asarray(m_img, dtype=np.float32) / 255.0
    a = a * (1.0 + (m - 0.5) * 0.22)[:, :, None]

    # warm age blotches
    mask = Image.new("L", (1024, 1024), 0)
    md = ImageDraw.Draw(mask)
    for (cx, cy, r, v) in ((120, 880, 260, 26), (905, 140, 220, 20),
                           (700, 960, 300, 18), (80, 120, 180, 14)):
        md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=v)
    mask = mask.filter(ImageFilter.GaussianBlur(60))
    b = (np.asarray(mask, dtype=np.float32) / 255.0)[:, :, None]
    tint = np.array([0.92, 0.86, 0.76], dtype=np.float32)
    a = a * (1.0 - b) + (a * tint) * b

    # band-pass fibre noise
    fine = rng.standard_normal((1024, 1024)).astype(np.float32)
    fine = (fine - fine.min()) / (fine.max() - fine.min()) * 255.0
    fimg = Image.fromarray(fine.astype(np.uint8), "L")
    band = (np.asarray(fimg, dtype=np.float32)
            - np.asarray(fimg.filter(ImageFilter.GaussianBlur(3)),
                         dtype=np.float32))
    band = band / band.std() * 10.0
    a = a + band[:, :, None]

    # print grain
    a = a + rng.standard_normal((1024, 1024, 1)).astype(np.float32) * 6.5

    a = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGB")


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PANELS, exist_ok=True)
    make_gulf_panel(os.path.join(PANELS, "proc-bahrain.png"))

    flat, band_h = draw_page()
    assert not CLIPS, f"CLIP failures: {CLIPS}"
    assert DRAWN == set(range(1, 43)), (
        f"drawn story set mismatch: missing={sorted(set(range(1, 43)) - DRAWN)} "
        f"extra={sorted(DRAWN - set(range(1, 43)))}")

    out = paper_texture(flat)
    assert out.size == (1024, 1024)

    quality = 90
    while True:
        # JPEG bytes under the entry.png name: the rules sniff the type from
        # the first bytes, so the format must be stated explicitly.
        out.save(ENTRY, format="JPEG", quality=quality)
        size = os.path.getsize(ENTRY)
        if size <= 1048576 or quality <= 40:
            break
        quality = 86 if quality == 90 else max(40, quality - 4)

    with open(ENTRY, "rb") as fh:
        blob = fh.read()
    assert blob[:3] == b"\xff\xd8\xff", "entry.png is not a JPEG"
    with Image.open(ENTRY) as chk:
        assert chk.size == (1024, 1024), f"bad size {chk.size}"
    assert len(blob) <= 1048576, f"entry.png too large: {len(blob)}"

    print(f"band_height={band_h} brief_size={BRIEF_SIZE[0]} quality={quality}")
    print(f"entry.png bytes={len(blob)}")
    print(f"entry.png sha256={hashlib.sha256(blob).hexdigest()}")


BRIEF_SIZE = [None]

if __name__ == "__main__":
    main()
