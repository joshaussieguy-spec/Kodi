#!/usr/bin/env python3
"""Generate brand assets: icon.png (512x512) + fanart.jpg (1920x1080).
Dark glassy look, glowing diamond, Arabic wordmark الطَّوِيل."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = os.path.dirname(os.path.abspath(__file__))
TEXT = "\u0627\u0644\u0637\u064e\u0651\u0648\u0650\u064a\u0644"  # الطَّوِيل
SHAPED = get_display(arabic_reshaper.reshape(TEXT))

ACCENT = (64, 224, 208)      # turquoise
ACCENT2 = (138, 43, 226)     # violet
BG_TOP = (10, 14, 26)
BG_BOT = (2, 4, 10)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def radial_gradient(size, inner, outer):
    img = Image.new("RGB", (size, size))
    px = img.load()
    cx = cy = size / 2
    m = math.hypot(cx, cy)
    for y in range(size):
        for x in range(size):
            t = min(1.0, math.hypot(x - cx, y - cy) / m)
            px[x, y] = lerp(inner, outer, t)
    return img


def diamond_pts(cx, cy, r):
    """True diamond: points up/right/down/left."""
    return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]


def gradient_layer(size, c_top, c_bot):
    g = Image.new("RGB", (size, size))
    gp = g.load()
    for y in range(size):
        col = lerp(c_top, c_bot, y / size)
        for x in range(size):
            gp[x, y] = col
    return g


def paste_masked(base, grad, mask):
    base.paste(Image.composite(grad, base, mask), (0, 0))


# ---------- ICON 512x512 ----------
S = 512
icon = radial_gradient(S, BG_TOP, BG_BOT)

# ambient glow behind center
glow = Image.new("RGB", (S, S), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([110, 60, S - 110, S - 130], fill=(26, 36, 74))
glow = glow.filter(ImageFilter.GaussianBlur(55))
icon = Image.blend(icon, Image.blend(icon, glow, 0.4), 0.6)
d = ImageDraw.Draw(icon, "RGBA")

CX = CY = 218          # diamond center (leaves room for wordmark below)
R_OUT, R_IN, R_CORE = 150, 134, 108

# outer double frame
d.polygon(diamond_pts(CX, CY, R_OUT), outline=(255, 255, 255, 30), width=8)
d.polygon(diamond_pts(CX, CY, R_IN), outline=ACCENT + (210,), width=4)

# glow under core diamond
glowlayer = Image.new("RGB", (S, S), (0, 0, 0))
gl = ImageDraw.Draw(glowlayer)
gl.polygon(diamond_pts(CX, CY, R_CORE), fill=(24, 96, 130))
glowlayer = glowlayer.filter(ImageFilter.GaussianBlur(26))
icon = Image.blend(icon, Image.blend(icon, glowlayer, 0.55), 0.75)
d = ImageDraw.Draw(icon, "RGBA")

# gradient-filled core diamond
grad = gradient_layer(S, ACCENT2, ACCENT)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).polygon(diamond_pts(CX, CY, R_CORE), fill=255)
icon.paste(Image.composite(grad, icon, mask), (0, 0))
d = ImageDraw.Draw(icon, "RGBA")

# top-half shine (subtle)
shine_mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(shine_mask).polygon(
    [(CX, CY - R_CORE), (CX + R_CORE, CY), (CX - R_CORE, CY)], fill=46)
white = Image.new("RGB", (S, S), (255, 255, 255))
icon.paste(Image.composite(white, icon, shine_mask), (0, 0))
d = ImageDraw.Draw(icon, "RGBA")

# facet lines from center
for p in diamond_pts(CX, CY, R_CORE):
    d.line([(CX, CY), p], fill=(255, 255, 255, 55), width=3)

# play triangle
d.polygon([(CX - 20, CY - 32), (CX - 20, CY + 32), (CX + 32, CY)],
          fill=(255, 255, 255, 240))

# Arabic wordmark bottom
font = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", 88)
word = SHAPED
bbox = d.textbbox((0, 0), word, font=font)
tw = bbox[2] - bbox[0]
tx, ty = (S - tw) / 2 - bbox[0], 392 - bbox[1]

tglow = Image.new("RGB", (S, S), (0, 0, 0))
td = ImageDraw.Draw(tglow)
td.text((tx, ty), word, font=font, fill=(40, 160, 200))
tglow = tglow.filter(ImageFilter.GaussianBlur(9))
icon = Image.blend(icon, Image.blend(icon, tglow, 0.5), 0.5)
d = ImageDraw.Draw(icon, "RGBA")
d.text((tx, ty), word, font=font, fill=(238, 247, 255, 255))

icon.save(os.path.join(ROOT, "icon.png"), "PNG")
print("icon.png done", icon.size)

# ---------- FANART 1920x1080 ----------
FW, FH = 1920, 1080
fan = Image.new("RGB", (FW, FH))
px = fan.load()
top, bot = (8, 10, 22), (2, 3, 8)
for y in range(FH):
    col = lerp(top, bot, y / FH)
    for x in range(FW):
        px[x, y] = col

# diagonal light streaks
streaks = Image.new("RGB", (FW, FH), (0, 0, 0))
sd2 = ImageDraw.Draw(streaks)
for x0 in (200, 700, 1200, 1600):
    sd2.line([(x0, FH), (x0 + 560, 0)], fill=(22, 66, 104), width=150)
streaks = streaks.filter(ImageFilter.GaussianBlur(95))
fan = Image.blend(fan, Image.blend(fan, streaks, 0.5), 0.5)

d = ImageDraw.Draw(fan, "RGBA")

# big diamond center-right
cx, cy, r = FW * 0.74, FH * 0.48, 310
d.polygon(diamond_pts(cx, cy, r), outline=(255, 255, 255, 26), width=12)
d.polygon(diamond_pts(cx, cy, r - 26), outline=ACCENT + (140,), width=5)

glowlayer = Image.new("RGB", (FW, FH), (0, 0, 0))
gl = ImageDraw.Draw(glowlayer)
gl.polygon(diamond_pts(cx, cy, r - 70), fill=(22, 84, 112))
glowlayer = glowlayer.filter(ImageFilter.GaussianBlur(46))
fan = Image.blend(fan, Image.blend(fan, glowlayer, 0.55), 0.7)
d = ImageDraw.Draw(fan, "RGBA")

grad2 = gradient_layer(FH, ACCENT2, ACCENT).resize((FW, FH))
mask2 = Image.new("L", (FW, FH), 0)
ImageDraw.Draw(mask2).polygon(diamond_pts(cx, cy, r - 70), fill=110)
fan.paste(Image.composite(grad2, fan, mask2), (0, 0))
d = ImageDraw.Draw(fan, "RGBA")

# facet lines
for p in diamond_pts(cx, cy, r - 70):
    d.line([(cx, cy), p], fill=(255, 255, 255, 45), width=4)

# wordmark — centered on left half, glow
font2 = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", 230)
word2 = SHAPED
bb2 = d.textbbox((0, 0), word2, font=font2)
tw2, th2 = bb2[2] - bb2[0], bb2[3] - bb2[1]
block_cx = FW * 0.30
tx2, ty2 = block_cx - tw2 / 2 - bb2[0], FH * 0.40 - th2 / 2 - bb2[1]

tglow2 = Image.new("RGB", (FW, FH), (0, 0, 0))
t2 = ImageDraw.Draw(tglow2)
t2.text((tx2, ty2), word2, font=font2, fill=(30, 120, 160))
tglow2 = tglow2.filter(ImageFilter.GaussianBlur(22))
fan = Image.blend(fan, Image.blend(fan, tglow2, 0.6), 0.65)
d = ImageDraw.Draw(fan, "RGBA")
d.text((tx2, ty2), word2, font=font2, fill=(240, 248, 255, 255))

f3 = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", 52)
sub = "K O D I   A P P S"
bb3 = d.textbbox((0, 0), sub, font=f3)
d.text((block_cx - (bb3[2] - bb3[0]) / 2, FH * 0.60), sub, font=f3,
       fill=(165, 185, 215, 210))

fan.save(os.path.join(ROOT, "fanart.jpg"), "JPEG", quality=88)
print("fanart.jpg done", fan.size)