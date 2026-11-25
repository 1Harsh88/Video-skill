"""Bisleri explainer: 1080x1920 vertical, user clips b01-b10 + heavy news-style motion graphics.
usage: python render.py SEG_INDEX   (renders one section to out/seg_XX.mp4)   |  python render.py still T
"""
import sys, os, math, json, subprocess, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 24
ROOT = "/home/user/bproj"; CLIPS = "/home/user/bisleri/dl/x/zip-staging/videos"
FD = "/home/user/mproj/assets/fonts"
FONTS = {"xb": f"{FD}/Mukta-ExtraBold.ttf", "b": f"{FD}/Mukta-Bold.ttf", "m": f"{FD}/Mukta-Medium.ttf",
         "sym": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"}
WHITE = (245, 248, 252); RED = (235, 45, 55); GREEN = (40, 215, 110); AMBER = (255, 190, 40); CYAN = (60, 200, 255)
NAVY = (10, 18, 36); BLUE = (40, 110, 235); YEL = (255, 222, 60); GREY = (150, 160, 175)

WORDS = [(l.split()[0], float(l.split()[1]), float(l.split()[2])) for l in open(f"{ROOT}/words.txt", encoding="utf8")]
END = 98.04
SECT = [0.0, 9.86, 17.78, 25.24, 36.58, 46.63, 54.50, 64.18, 75.84, 85.77, END]
TITLES = ["क्या बिसलेरी सेफ है?", "30 सितंबर 2025 · गोवा", "ब्रोमेट: 12 बनाम 10", "अपील · दूसरी लैब", "PAH क्या है?",
          "तीसरी लैब", "कोई जवाब नहीं", "मुकदमे की मंजूरी", "बिसलेरी का जवाब", "अब आगे क्या?"]
TINT = [(1.0, .95, 1.05), (1.0, 1.0, 1.04), (1.02, 1.0, .98), (.97, 1.0, 1.05), (1.06, .95, .95),
        (.96, 1.0, 1.06), (.98, .99, 1.05), (1.06, .96, .94), (1.0, 1.0, 1.02), (.98, 1.03, 1.0)]

# ---------------------------------------------------------------- helpers
def ease_out(t): t = min(1, max(0, t)); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(1, max(0, t)); c = 1.9; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def ease(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def clamp01(x): return min(1.0, max(0.0, x))

@functools.lru_cache(maxsize=64)
def font(k, s): return ImageFont.truetype(FONTS[k], s, layout_engine=ImageFont.Layout.RAQM)

@functools.lru_cache(maxsize=1024)
def txt(s, k="xb", size=60, fill=WHITE, stroke=0, sfill=(0, 0, 0), glow=None, shadow=True):
    f = font(k, size); l, t, r, b = f.getbbox(s, stroke_width=stroke)
    pad = int(size * .45); w, h = r - l + 2 * pad, b - t + 2 * pad
    img = Image.new("RGBA", (w, h)); pos = (pad - l, pad - t)
    if glow:
        g = Image.new("RGBA", (w, h)); ImageDraw.Draw(g).text(pos, s, font=f, fill=glow + (255,), stroke_width=max(2, size // 16), stroke_fill=glow + (255,))
        img = Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(size / 5)))
    if shadow:
        sh = Image.new("RGBA", (w, h)); ImageDraw.Draw(sh).text((pos[0] + size // 20, pos[1] + size // 16), s, font=f, fill=(0, 0, 0, 200), stroke_width=stroke)
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(size / 18)))
    ImageDraw.Draw(img).text(pos, s, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=sfill + (255,))
    return np.asarray(img).astype(np.float32) / 255

def tw(s, k="xb", size=60): l, t, r, b = font(k, size).getbbox(s); return r - l

def over(base, rgba, x, y, a=1.0, sc=1.0, center=True, rot=0.0):
    if a <= .003 or sc <= .01: return
    if abs(sc - 1) > 1e-3 or rot:
        h, w = rgba.shape[:2]
        if rot:
            M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc); c, s_ = abs(M[0, 0]), abs(M[0, 1])
            nw, nh = int(h * s_ + w * c) + 2, int(h * c + w * s_) + 2
            M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
            rgba = cv2.warpAffine(rgba, M, (nw, nh), flags=cv2.INTER_LINEAR)
        else:
            rgba = cv2.resize(rgba, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    if center: x, y = int(round(x - w / 2)), int(round(y - h / 2))
    else: x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    s = rgba[y0 - y:y1 - y, x0 - x:x1 - x]; al = s[..., 3:4] * a
    base[y0:y1, x0:x1] = base[y0:y1, x0:x1] * (1 - al) + s[..., :3] * al

def panel(base, x, y, w, h, a=1.0, col=NAVY, border=None, op=.72, blur=True, rad=26):
    """Glass card: blurred+darkened background, rounded, optional coloured border/accent."""
    if a <= .003: return
    x, y, w, h = int(x), int(y), int(w), int(h)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    reg = base[y0:y1, x0:x1]
    if blur: reg2 = cv2.GaussianBlur(reg, (0, 0), 14)
    else: reg2 = reg.copy()
    c = np.array(col, np.float32) / 255
    reg2 = reg2 * (1 - op) + c * op
    m = np.zeros((h, w), np.float32); cv2.rectangle(m, (rad, 0), (w - rad, h), 1, -1); cv2.rectangle(m, (0, rad), (w, h - rad), 1, -1)
    for cx, cy in ((rad, rad), (w - rad, rad), (rad, h - rad), (w - rad, h - rad)): cv2.circle(m, (cx, cy), rad, 1, -1, cv2.LINE_AA)
    m = m[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * a
    base[y0:y1, x0:x1] = reg * (1 - m) + reg2 * m
    if border:
        lay = np.zeros((h, w, 4), np.float32); bc = tuple(v / 255 for v in border) + (1.0,)
        cv2.rectangle(lay, (rad, 1), (w - rad, 1), bc, 3); cv2.rectangle(lay, (rad, h - 3), (w - rad, h - 3), bc, 2)
        cv2.line(lay, (2, rad), (2, h - rad), bc, 7)
        over(base, lay, x, y, a * .95, center=False)

def glowline(base, pts, col, th=6, a=1.0, glow=True):
    if a <= 0: return
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    pad = 40; x0, y0 = int(min(xs)) - pad, int(min(ys)) - pad; w, h = int(max(xs)) - x0 + pad, int(max(ys)) - y0 + pad
    lay = np.zeros((h, w, 4), np.float32); c = tuple(v / 255 for v in col) + (1.0,)
    p = np.array([[px - x0, py - y0] for px, py in pts], np.int32)
    if glow:
        g = np.zeros_like(lay); cv2.polylines(g, [p], False, c, th * 3, cv2.LINE_AA); g = cv2.GaussianBlur(g, (0, 0), th * 1.6)
        over(base, g, x0, y0, a * .8, center=False)
    cv2.polylines(lay, [p], False, c, th, cv2.LINE_AA); over(base, lay, x0, y0, a, center=False)

def tick(base, cx, cy, s, col, prog, a=1.0):
    pts = [(cx - s * .5, cy), (cx - s * .15, cy + s * .38), (cx + s * .55, cy - s * .42)]
    L1 = math.dist(pts[0], pts[1]); L2 = math.dist(pts[1], pts[2]); d = prog * (L1 + L2)
    if d <= 0: return
    if d <= L1: q = [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * d / L1, pts[0][1] + (pts[1][1] - pts[0][1]) * d / L1)]
    else: f = (d - L1) / L2; q = [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * f, pts[1][1] + (pts[2][1] - pts[1][1]) * f)]
    glowline(base, q, col, max(4, int(s / 7)), a)

def cross(base, cx, cy, s, col, prog, a=1.0):
    p1 = clamp01(prog * 2); p2 = clamp01(prog * 2 - 1); r = s * .42
    glowline(base, [(cx - r, cy - r), (cx - r + 2 * r * p1, cy - r + 2 * r * p1)], col, max(4, int(s / 7)), a)
    if p2 > 0: glowline(base, [(cx + r, cy - r), (cx + r - 2 * r * p2, cy - r + 2 * r * p2)], col, max(4, int(s / 7)), a)

def ring(base, cx, cy, r, col, th=4, a=1.0, prog=1.0):
    lay = np.zeros((int(2 * r + 60), int(2 * r + 60), 4), np.float32); c = tuple(v / 255 for v in col) + (1.0,)
    cv2.ellipse(lay, (int(r + 30), int(r + 30)), (int(r), int(r)), -90, 0, 360 * prog, c, th, cv2.LINE_AA)
    g = cv2.GaussianBlur(lay, (0, 0), 6); over(base, g, cx, cy, a * .7); over(base, lay, cx, cy, a)

def bottle(base, cx, cy, s, col, a=1.0):
    lay = np.zeros((int(s * 2.4), int(s * 1.2), 4), np.float32); c = tuple(v / 255 for v in col) + (1.0,)
    w_, h_ = lay.shape[1], lay.shape[0]
    body = np.array([[w_ * .18, h_ * .35], [w_ * .32, h_ * .22], [w_ * .40, h_ * .10], [w_ * .60, h_ * .10], [w_ * .68, h_ * .22], [w_ * .82, h_ * .35],
                     [w_ * .82, h_ * .95], [w_ * .18, h_ * .95]], np.int32)
    cv2.fillPoly(lay, [body], tuple(x * .35 for x in c[:3]) + (.85,), cv2.LINE_AA)
    cv2.polylines(lay, [body], True, c, 3, cv2.LINE_AA)
    cv2.rectangle(lay, (int(w_ * .38), int(h_ * .02)), (int(w_ * .62), int(h_ * .10)), c, -1)
    cv2.rectangle(lay, (int(w_ * .18), int(h_ * .5)), (int(w_ * .82), int(h_ * .68)), c, -1)
    over(base, lay, cx, cy, a)

def shake(t0, t, amp=18, dur=.35):
    d = t - t0
    if d < 0 or d > dur: return 0, 0
    k = (1 - d / dur) ** 2 * amp; return k * math.sin(d * 95), k * math.cos(d * 77)

def appear(t, t0, t1, fin=.25, fout=.3):
    if t < t0 or t > t1 + fout: return 0.0
    return min(ease_out((t - t0) / fin), 1 - ease((t - t1) / fout) if t > t1 else 1.0)

def slide(t, t0, t1, dist=140, fin=.35):
    a = appear(t, t0, t1, fin); return a, (1 - ease_out((t - t0) / fin)) * dist

def stamp(base, t, t0, t1, s, col, cx, cy, size=96, rot=-7):
    if t < t0 or t > t1 + .3: return
    d = t - t0; sc = 2.4 - 1.4 * ease_out(d / .16) if d < .16 else 1.0 + .03 * math.sin(d * 3)
    a = clamp01(d / .08) * (1 - ease((t - t1) / .3) if t > t1 else 1)
    im = txt(s, "xb", size, col, shadow=False)
    h, w = im.shape[:2]; pad = 16
    box = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32); c = tuple(v / 255 for v in col) + (1.0,)
    cv2.rectangle(box, (6, 6), (w + 2 * pad - 7, h + 2 * pad - 7), c, 9); cv2.rectangle(box, (20, 20), (w + 2 * pad - 21, h + 2 * pad - 21), c, 3)
    box[pad:pad + h, pad:pad + w] = np.maximum(box[pad:pad + h, pad:pad + w], im) if False else box[pad:pad + h, pad:pad + w]
    over_rgba(box, im, pad, pad)
    rng = np.random.default_rng(7); holes = (rng.random(box.shape[:2]) > .93).astype(np.float32); holes = cv2.GaussianBlur(holes, (0, 0), 1.2)
    box[..., 3] *= (1 - .55 * holes)
    bg = np.zeros_like(box); bg[..., :3] = .03; bg[..., 3] = .55 * (box[..., 3] > -1)
    over(base, bg, cx, cy, a * .7, sc, rot=rot)
    over(base, box, cx, cy, a, sc, rot=rot)

def over_rgba(dst, src, x, y):
    h, w = src.shape[:2]; a = src[..., 3:4]
    dst[y:y + h, x:x + w, :3] = dst[y:y + h, x:x + w, :3] * (1 - a) + src[..., :3] * a
    dst[y:y + h, x:x + w, 3:4] = np.maximum(dst[y:y + h, x:x + w, 3:4], a)

def chip(base, t, t0, t1, s, x, y, col=RED, size=52, tcol=WHITE, anchor="l", fromx=-1):
    a, off = slide(t, t0, t1, 160)
    if a <= 0: return 0
    im = txt(s, "xb", size, tcol, shadow=False); w = im.shape[1] - int(size * .5); h = int(size * 1.55)
    if anchor == "c": x = x - w / 2 - 24
    elif anchor == "r": x = x - w - 48
    x = x + fromx * off
    panel(base, x, y - h / 2, w + 48, h, a, col, None, op=.9, blur=False, rad=int(h / 2.6))
    over(base, im, x + 24 + w / 2, y, a); return w + 48

def date_card(base, t, t0, t1, day, month, x, y, col=RED):
    a, off = slide(t, t0, t1, 200)
    if a <= 0: return
    x -= off; d = t - t0
    panel(base, x, y, 300, 330, a, (245, 245, 248), None, op=.96, blur=False, rad=22)
    panel(base, x, y, 300, 86, a, col, None, op=1, blur=False, rad=22)
    base_flip = clamp01((d - .1) / .35); sc_y = abs(math.cos(base_flip * math.pi)) if base_flip < 1 else 1
    im = txt(day, "xb", 150, (20, 24, 34), shadow=False)
    if base_flip >= .5 or base_flip >= 1:
        imr = cv2.resize(im, (im.shape[1], max(1, int(im.shape[0] * max(.02, sc_y)))))
        over(base, imr, x + 150, y + 205, a)
    over(base, txt(month, "xb", 44, WHITE, shadow=False), x + 150, y + 43, a)
    for rx in (70, 230): cv2.circle(base, (int(x + rx), int(y + 8)), 12, (.2, .2, .25), -1, cv2.LINE_AA)

def counter(v, dec): return f"{v:.{dec}f}"

# ---------------------------------------------------------------- per-section motion graphics
def mg(base, t):
    S = SECT
    # ---- B01 hook
    if t < S[1] + .4:
        words = [("क्या", .0, 330, CYAN), ("बिसलेरी", .42, 330, WHITE), ("पीना", 1.14, 470, WHITE), ("सेफ", 1.56, 470, YEL), ("है?", 1.88, 470, RED)]
        rows = {330: ["क्या", "बिसलेरी"], 470: ["पीना", "सेफ", "है?"]}
        for wd, t0, yy, col in words:
            if t < t0 or t > 2.9: continue
            row = rows[yy]; sz = 132; gap = 30; widths = [tw(r, "xb", sz) for r in row]; tot = sum(widths) + gap * (len(row) - 1)
            xx = W / 2 - tot / 2 + sum(widths[:row.index(wd)]) + gap * row.index(wd) + widths[row.index(wd)] / 2
            a = clamp01((t - t0) / .1) * (1 - ease((t - 2.55) / .35)); sc = ease_back((t - t0) / .28)
            up = ease((t - 2.55) / .35) * 120
            over(base, txt(wd, "xb", sz, col, stroke=3, glow=(0, 90, 200) if col != RED else (160, 0, 0)), xx, yy - up, a, sc)
        chip(base, t, 2.87, 6.0, "भारत की सबसे बड़ी बोतलबंद पानी कंपनी", 60, 300, BLUE, 46)
        if 6.25 <= t < 9.9:
            a, off = slide(t, 6.25, 9.6, 200)
            panel(base, 60 - off, 380, 420, 150, a, (16, 60, 150), CYAN, op=.92, blur=False)
            over(base, txt("FSSAI", "sym", 64, WHITE), 270 - off, 435, a)
            over(base, txt("खाद्य सुरक्षा नियामक", "b", 34, (190, 220, 255), shadow=False), 270 - off, 495, a)
        stamp(base, t, 7.25, 9.75, "मुकदमे की मंजूरी", RED, W / 2, 720, 92)
    # ---- B02 date, Goa, 6 samples
    if S[1] <= t < S[2] + .4:
        date_card(base, t, 10.95, 17.6, "30", "सितंबर 2025", 60, 260)
        chip(base, t, 13.44, 17.6, "FSSAI की टीम", 60, 650, BLUE, 44)
        if t >= 15.0:
            a, off = slide(t, 15.0, 17.6, 160)
            w = chip(base, t, 15.0, 17.6, "   गोवा फैक्ट्री", 60, 760, (200, 30, 40), 48)
            # map pin
            px, py = 60 - off + 46, 760; bounce = -abs(math.sin((t - 15) * 6)) * 14 * max(0, 1 - (t - 15) / 1.2)
            cv2.circle(base, (int(px), int(py - 10 + bounce)), 16, (1, 1, 1), -1, cv2.LINE_AA)
            cv2.circle(base, (int(px), int(py - 10 + bounce)), 7, (.85, .12, .15), -1, cv2.LINE_AA)
        if t >= 16.1:
            a = appear(t, 16.1, 17.6, .2)
            panel(base, 40, 840, 520, 300, a, NAVY, CYAN, op=.75)
            over(base, txt("6 सैंपल", "xb", 70, WHITE), 300, 905, a)
            for i in range(6):
                ti = 16.1 + i * .09; aa = clamp01((t - ti) / .12) * a
                bottle(base, 100 + i * 80, 1045 - 20 * (1 - ease_back((t - ti) / .3)), 52, CYAN, aa)
    # ---- B03 5 pass 1 fail; bromate meter
    if S[2] <= t < S[3] + .4:
        a = appear(t, 17.78, 25.0, .25)
        if a > 0:
            panel(base, 40, 230, 1000, 250, a, NAVY, None, op=.62)
            over(base, txt("6 सैंपल · जाँच नतीजा", "b", 40, (200, 215, 235), shadow=False), 540, 270, a)
            for i in range(6):
                cx = 125 + i * 166; cy = 390
                if i < 5:
                    ti = 17.8 + i * .2
                    if t >= ti: ring(base, cx, cy, 58, GREEN, 5, a, clamp01((t - ti) / .25)); tick(base, cx, cy, 62, GREEN, clamp01((t - ti - .1) / .25), a)
                else:
                    ti = 19.52
                    if t >= ti:
                        ring(base, cx, cy, 58, RED, 6, a, clamp01((t - ti) / .2)); cross(base, cx, cy, 70, RED, clamp01((t - ti - .05) / .25), a)
                        if t < ti + 1.5: over(base, txt("फेल", "xb", 40, RED), cx, cy + 85, a)
        a = appear(t, 20.0, 25.0, .3)
        if a > 0:
            y0 = 560; panel(base, 40, y0, 1000, 330, a, NAVY, RED, op=.75)
            over(base, txt("ब्रोमेट", "xb", 54, WHITE), 170, y0 + 60, a)
            v = 12 * ease_out((t - 20.97) / .8) if t > 20.97 else 0
            over(base, txt(counter(v, 0), "sym", 96, RED if v > 10 else WHITE, glow=(150, 0, 0) if v > 10 else None), 700, y0 + 70, a)
            over(base, txt("µg/L", "sym", 44, (220, 225, 235), shadow=False), 870, y0 + 82, a)
            bx, by, bw, bh = 90, y0 + 170, 900, 56; vmax = 15
            cv2.rectangle(base, (bx, by), (bx + bw, by + bh), (.15, .17, .22), -1)
            fw = int(bw * v / vmax)
            if fw > 0:
                cv2.rectangle(base, (bx, by), (bx + min(fw, int(bw * 10 / vmax)), by + bh), (.15, .8, .4), -1)
                if fw > bw * 10 / vmax: cv2.rectangle(base, (bx + int(bw * 10 / vmax), by), (bx + fw, by + bh), (.95, .15, .2), -1)
            lx = bx + int(bw * 10 / vmax); fl = 1.0 if t < 23.3 else (.55 + .45 * math.sin((t - 23.3) * 14))
            cv2.line(base, (lx, by - 22), (lx, by + bh + 22), (fl, fl, fl), 5)
            over(base, txt("लिमिट 10", "xb", 40, YEL if t >= 23.3 else WHITE), lx, by + bh + 52, a)
            if t >= 24.0: over(base, txt("+20% ज़्यादा", "xb", 46, RED, glow=(120, 0, 0)), bx + bw - 120, by - 46, a * clamp01((t - 24) / .15), ease_back((t - 24) / .25))
    # ---- B04 appeal, second lab, but...
    if S[3] <= t < S[4] + .4:
        date_card(base, t, 25.24, 28.7, "22", "नवंबर 2025", 60, 250, BLUE)
        chip(base, t, 28.05, 33.4, "बिसलेरी की अपील", 400, 420, (200, 120, 0), 50)
        a = appear(t, 28.78, 33.4, .3)
        if a > 0:
            y = 660; panel(base, 40, y - 110, 1000, 220, a, NAVY, CYAN, op=.72)
            for i, (lab, cx) in enumerate((("लैब 1", 200), ("लैब 2", 880))):
                ring(base, cx, y, 66, RED if i == 0 else GREEN if t > 30.9 else CYAN, 5, a)
                over(base, txt(lab, "xb", 40, WHITE), cx, y, a)
            pr = clamp01((t - 29.4) / .9); glowline(base, [(280, y), (280 + 520 * pr, y)], CYAN, 6, a)
            if pr > .05: bottle(base, 280 + 520 * pr, y - 2, 30, WHITE, a)
            if t > 30.9: chip(base, t, 30.9, 33.4, "ब्रोमेट: लिमिट के अंदर ✓".replace(" ✓", ""), 540, y + 170, (20, 150, 80), 46, anchor="c", fromx=0)
        if t >= 33.5:
            a = appear(t, 33.5, 36.45, .1)
            g = 10 * max(0, 1 - (t - 33.5) / .5) + 3 * (math.sin(t * 40) > .7)
            im = txt("लेकिन…", "xb", 150, WHITE, glow=(200, 0, 0))
            over(base, txt("लेकिन…", "xb", 150, (255, 0, 0), shadow=False), W / 2 - g, 480, a * .6)
            over(base, txt("लेकिन…", "xb", 150, (0, 200, 255), shadow=False), W / 2 + g, 480, a * .6)
            over(base, im, W / 2, 480, a)
            if t >= 34.7: chip(base, t, 34.7, 36.45, "एक और चीज़ मिली!", W / 2, 660, RED, 58, anchor="c", fromx=0)
    # ---- B05 PAH
    if S[4] <= t < S[5] + .4:
        a = appear(t, 36.58, 46.45, .15)
        if a > 0:
            # rotating fused-hexagon molecule
            ang = (t - 36.58) * 25; cx, cy, r = 830, 520, 62
            pts = []
            for k, (ox, oy) in enumerate(((0, 0), (r * 1.732, 0), (r * .866, r * 1.5))):
                hexp = []
                for j in range(7):
                    th = math.radians(60 * j + 30 + ang); ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                    rx, ry = ox - r * .866, oy - r * .5; px = rx * ca - ry * sa; py = rx * sa + ry * ca
                    hexp.append((cx + px + r * math.cos(th), cy + py + r * math.sin(th)))
                prog = clamp01((t - 36.6 - k * .25) / .5)
                glowline(base, hexp[:max(2, int(7 * prog))], (255, 80, 60), 5, a)
        if t < 42.1:
            aa = appear(t, 36.58, 41.9, .12); g = 12 * max(0, 1 - (t - 36.58) / .6) + 4 * (math.sin(t * 33) > .8)
            over(base, txt("PAH", "sym", 190, (255, 0, 0), shadow=False), 380 - g, 470, aa * .55)
            over(base, txt("PAH", "sym", 190, (0, 220, 255), shadow=False), 380 + g, 470, aa * .55)
            over(base, txt("PAH", "sym", 190, WHITE, glow=(200, 0, 0)), 380, 470, aa)
            if t >= 38.16:
                a2, off = slide(t, 38.16, 41.9, 150)
                panel(base, 60 - off, 640, 640, 100, a2, (170, 20, 30), YEL, op=.92, blur=False)
                tri = np.array([[118 - off, 662], [94 - off, 712], [142 - off, 712]], np.int32)
                cv2.fillPoly(base, [tri], (1, .85, .2), cv2.LINE_AA)
                over(base, txt("कैंसर से जुड़ा केमिकल", "xb", 50, WHITE, shadow=False), 410 - off, 690, a2)
            chip(base, t, 39.4, 41.9, "पीने के पानी में होना ही नहीं चाहिए", 60, 820, NAVY, 42)
        a = appear(t, 42.18, 46.45, .2)
        if a > 0:
            panel(base, 60, 330, 960, 330, a, NAVY, RED, op=.8)
            over(base, txt("मात्रा मिली", "b", 44, (200, 210, 230), shadow=False), 540, 385, a)
            v = .144 * ease_out((t - 42.9) / 1.6) if t > 42.9 else 0
            roll = "" if t > 44.5 else ""
            over(base, txt(f"{v:.3f}", "sym", 140, RED, glow=(140, 0, 0)), 470, 520, a)
            over(base, txt("µg/L", "sym", 56, WHITE, shadow=False), 820, 540, a)
            chip(base, t, 44.6, 46.45, "पीने के पानी में: 0 होना चाहिए", 540, 720, (170, 20, 30), 42, anchor="c", fromx=0)
    # ---- B06 third lab report
    if S[5] <= t < S[6] + .4:
        a, off = slide(t, 46.63, 54.3, 220)
        if a > 0:
            x0 = 50 - off; y0 = 260
            panel(base, x0, y0, 600, 640, a, (240, 242, 246), None, op=.95, blur=False, rad=18)
            panel(base, x0, y0, 600, 110, a, (20, 40, 80), None, op=1, blur=False, rad=18)
            over(base, txt("लैब 3 · जाँच रिपोर्ट", "xb", 46, WHITE, shadow=False), x0 + 300, y0 + 55, a)
            for i in range(3): cv2.line(base, (int(x0 + 40), int(y0 + 470 + i * 40)), (int(x0 + 560 - i * 90), int(y0 + 470 + i * 40)), (.75, .77, .8), 8)
            over(base, txt("ब्रोमेट", "xb", 52, (20, 24, 34), shadow=False), x0 + 130, y0 + 200, a)
            over(base, txt("PAH", "sym", 50, (20, 24, 34), shadow=False), x0 + 130, y0 + 330, a)
            cv2.line(base, (int(x0 + 30), int(y0 + 265)), (int(x0 + 570), int(y0 + 265)), (.8, .82, .85), 2)
            if t >= 49.5:
                over(base, txt("पास", "xb", 52, (10, 150, 70), shadow=False), x0 + 400, y0 + 200, a * clamp01((t - 49.5) / .15), ease_back((t - 49.5) / .3))
                tick(base, x0 + 520, y0 + 200, 50, (10, 170, 80), clamp01((t - 49.6) / .3), a)
            if t >= 51.3:
                blink = 1 if (t - 51.3) % .5 < .3 else .25
                over(base, txt("— ?", "sym", 58, (220, 140, 0), shadow=False), x0 + 430, y0 + 330, a * blink)
            stamp(base, t, 52.9, 54.3, "कोई ज़िक्र नहीं", RED, x0 + 320, y0 + 470, 70, -9)
    # ---- B07 2 Feb 2026, sent to FSSAI, no reply
    if S[6] <= t < S[7] + .4:
        date_card(base, t, 54.5, 57.0, "2", "फरवरी 2026", 60, 250, BLUE)
        a = appear(t, 56.9, 59.45, .25)
        if a > 0:
            y = 640; panel(base, 40, y - 120, 1000, 240, a, NAVY, CYAN, op=.72)
            over(base, txt("बिसलेरी", "xb", 46, WHITE), 170, y, a)
            panel(base, 760, y - 60, 230, 120, a, (16, 60, 150), None, op=1, blur=False, rad=16)
            over(base, txt("FSSAI", "sym", 46, WHITE, shadow=False), 875, y, a)
            pr = clamp01((t - 57.3) / 1.4); ex = 300 + 400 * ease(pr); ey = y - 60 * math.sin(pr * math.pi)
            env = np.zeros((80, 120, 4), np.float32); cv2.rectangle(env, (2, 2), (117, 77), (1, 1, 1, 1), -1)
            cv2.polylines(env, [np.array([[2, 2], [60, 45], [117, 2]], np.int32)], False, (.3, .35, .45, 1), 4, cv2.LINE_AA)
            if pr < 1: over(base, env, ex, ey, a, rot=-10 * math.sin(pr * 6))
            if t > 58.4: over(base, txt("रिपोर्ट भेजी", "b", 40, (170, 230, 255)), 540, y + 85, a)
        a = appear(t, 59.58, 63.95, .25)
        if a > 0:
            panel(base, 560, 330, 470, 150, a, (235, 238, 244), None, op=.95, blur=False, rad=40)
            if t < 60.7:
                for i in range(3):
                    s = .5 + .5 * math.sin(t * 9 - i * .9); cv2.circle(base, (int(720 + i * 70), 405), int(14 + 6 * s), (.45, .5, .6), -1, cv2.LINE_AA)
            else:
                over(base, txt("कोई जवाब नहीं", "xb", 54, (40, 44, 60), shadow=False), 795, 405, a)
            chip(base, t, 59.6, 63.95, "FSSAI · चुप्पी", 560, 540, (90, 96, 110), 40)
        if t >= 62.63:
            a = appear(t, 62.63, 63.98, .2)
            over(base, txt("मामला बंद?", "xb", 110, WHITE, glow=(80, 80, 90)), 330, 820, a, ease_back((t - 62.63) / .3))
    # ---- B08 one year later: prosecution
    if S[7] <= t < S[8] + .4:
        a = appear(t, 64.18, 69.3, .3)
        if a > 0:
            y = 330; panel(base, 40, y - 100, 1000, 290, a, NAVY, AMBER, op=.78)
            pr = ease((t - 64.6) / 2.4)
            cv2.line(base, (110, y + 20), (970, y + 20), (.25, .28, .35), 10)
            cv2.line(base, (110, y + 20), (int(110 + 860 * pr), y + 20), (1, .75, .15), 10)
            for k in range(13):
                xx = int(110 + 860 * k / 12); cv2.line(base, (xx, y + 4), (xx, y + 36), (.7, .7, .75) if 860 * k / 12 <= 860 * pr else (.3, .3, .35), 3)
            over(base, txt("22 नवं 2025", "b", 38, WHITE), 170, y - 40, a)
            over(base, txt("22 नवं 2026", "b", 38, AMBER if pr > .98 else GREY), 900, y - 40, a)
            cv2.circle(base, (int(110 + 860 * pr), y + 20), 18, (1, .8, .2), -1, cv2.LINE_AA)
            if t >= 66.64: over(base, txt("ठीक 1 साल बाद", "xb", 56, AMBER), 540, y + 110, a * clamp01((t - 66.64) / .15), ease_back((t - 66.64) / .3))
        stamp(base, t, 69.64, 75.6, "मुकदमे की मंजूरी", RED, W / 2, 380, 100, -6)
        if t >= 72.27:
            a = appear(t, 72.27, 75.6, .2)
            over(base, txt("वजह", "b", 48, (220, 225, 235)), W / 2, 590, a)
            for i, (s, t0, xx) in enumerate((("ब्रोमेट", 72.67, 320), ("PAH", 73.86, 760))):
                if t >= t0:
                    sc = ease_back((t - t0) / .3)
                    panel(base, xx - 190, 640, 380, 130, a * clamp01((t - t0) / .1), (170, 20, 30), YEL, op=.9, blur=False)
                    over(base, txt(s, "sym" if s == "PAH" else "xb", 70, WHITE, shadow=False), xx, 705, a, sc)
            if t > 73.6: over(base, txt("+", "sym", 80, WHITE), 540, 705, a)
    # ---- B09 Bisleri's reply, batch, 1 of 143
    if S[8] <= t < S[9] + .4:
        a, off = slide(t, 75.9, 79.6, 180)
        if a > 0:
            panel(base, 50 - off, 250, 980, 360, a, (235, 238, 244), None, op=.95, blur=False, rad=24)
            over(base, txt("“", "sym", 160, (0, 120, 220), shadow=False), 120 - off, 330, a)
            over(base, txt("बिसलेरी का जवाब", "xb", 44, (0, 90, 180), shadow=False), 400 - off, 310, a)
            q = "हमें कोई नोटिस ही नहीं मिला"; n = int(len(q) * clamp01((t - 77.3) / 1.6))
            ws = q.split(); shown = []; cnt = 0
            for wd in ws:
                cnt += len(wd) + 1
                if cnt <= n + 1: shown.append(wd)
            if shown:
                line = " ".join(shown); over(base, txt(line, "xb", 64, (20, 24, 34), shadow=False), 540 - off, 470, a)
        a = appear(t, 79.7, 82.9, .25)
        if a > 0:
            chip(base, t, 79.7, 82.9, "सिर्फ 1 बैच", 60, 300, RED, 50)
            panel(base, 60, 380, 620, 260, a, (245, 245, 248), None, op=.96, blur=False, rad=14)
            rng = np.random.default_rng(3); xx = 100
            while xx < 640:
                wbar = int(rng.integers(3, 12)); cv2.rectangle(base, (xx, 410), (xx + wbar, 540), (.05, .05, .08), -1); xx += wbar + int(rng.integers(4, 10))
            sc = 1 if t < 81.2 else 1 + .05 * max(0, 1 - (t - 81.2) / .3)
            over(base, txt("बैच  GO 270", "xb", 60, (20, 24, 34), shadow=False), 370, 590, a, sc)
            sy = 410 + 130 * ((t * .9) % 1); cv2.line(base, (80, int(sy)), (660, int(sy)), (1, .1, .1), 3)
        a = appear(t, 83.02, 85.6, .2)
        if a > 0:
            panel(base, 40, 240, 1000, 640, a, NAVY, CYAN, op=.8)
            over(base, txt("143 प्लांट में से 1", "xb", 62, WHITE), 540, 310, a)
            for i in range(143):
                r_, c_ = divmod(i, 13); cx = 120 + c_ * 70; cy = 400 + r_ * 42
                ti = 83.05 + (r_ + c_) * .025
                if t < ti: continue
                hot = (i == 77); s = clamp01((t - ti) / .15)
                col = (.95, .15, .2) if hot and t > 84.0 else (.25, .75, .95)
                rr = int(11 * s * (1.5 + .4 * math.sin(t * 8) if hot and t > 84.0 else 1))
                cv2.circle(base, (cx, cy), rr, col, -1, cv2.LINE_AA)
            if t > 84.0: ring(base, 120 + (77 % 13) * 70, 400 + (77 // 13) * 42, 34 + 8 * math.sin(t * 8), RED, 4, a)
    # ---- B10 no ban, 14 vs 6 months, court, CTA
    if S[9] <= t:
        a = appear(t, 86.0, 89.0, .25)
        if a > 0:
            panel(base, 40, 250, 1000, 230, a, (12, 90, 50), GREEN, op=.88)
            ring(base, 150, 365, 66, WHITE, 6, a); tick(base, 150, 365, 70, WHITE, clamp01((t - 86.2) / .35), a)
            over(base, txt("दुकान की बोतल पर", "b", 46, (210, 255, 225), shadow=False), 600, 320, a)
            over(base, txt("कोई बैन नहीं", "xb", 84, WHITE), 600, 405, a, ease_back((t - 88.0) / .3) if t > 88.0 else 1)
        a = appear(t, 89.17, 94.2, .25)
        if a > 0:
            panel(base, 40, 250, 1000, 470, a, NAVY, AMBER, op=.82)
            over(base, txt("जाँच वाली बोतल", "b", 44, WHITE), 260, 320, a)
            p1 = ease_out((t - 90.1) / 1.2); bw = 860 / 14
            cv2.rectangle(base, (80, 370), (int(80 + 14 * bw * p1), 440), (.92, .2, .22), -1)
            if t > 90.1: over(base, txt(f"{int(round(14 * p1))} महीने पुरानी", "xb", 46, WHITE), 300, 405, a)
            over(base, txt("एक्सपायरी", "b", 44, WHITE), 200, 520, a)
            p2 = ease_out((t - 92.6) / .6)
            cv2.rectangle(base, (80, 570), (int(80 + 6 * bw * p2), 640), (.15, .8, .4), -1)
            if t > 92.6: over(base, txt(f"{int(round(6 * p2))} महीने", "xb", 46, WHITE), int(80 + 6 * bw * p2) + 120, 605, a)
            if t > 93.2:
                xl = int(80 + 6 * bw); cv2.line(base, (xl, 360), (xl, 660), (1, 1, 1), 3)
                over(base, txt("8 महीने ज़्यादा", "xb", 40, AMBER), 760, 520, a * clamp01((t - 93.2) / .2))
        stamp(base, t, 94.67, 96.75, "फैसला कोर्ट करेगा", AMBER, W / 2, 420, 92, -5)
        if t >= 96.89:
            a = clamp01((t - 96.89) / .2)
            panel(base, 40, 250, 1000, 420, a, NAVY, YEL, op=.85)
            over(base, txt("आप क्या सोचते हैं?", "xb", 84, YEL, glow=(120, 90, 0)), 540, 340, a, ease_back((t - 96.89) / .3))
            over(base, txt("बिसलेरी पीना सेफ है या नहीं?", "b", 46, WHITE), 540, 450, a)
            pulse = 1 + .05 * math.sin(t * 9)
            panel(base, 300, 520, 480, 100, a, (220, 20, 30), None, op=1, blur=False, rad=50)
            over(base, txt("कमेंट में बताइए", "xb", 50, WHITE, shadow=False), 540, 570, a, pulse)

# ---------------------------------------------------------------- persistent chrome: header, captions, ticker
TICK = "  FSSAI ने बिसलेरी पर मुकदमे की मंजूरी दी   •   बैच GO 270   •   ब्रोमेट 12 µg/L (लिमिट 10)   •   PAH 0.144 µg/L   •   बिसलेरी: हमें नोटिस नहीं मिला   •   दुकानों की बोतलों पर कोई बैन नहीं   •   फैसला कोर्ट करेगा  "
@functools.lru_cache(maxsize=1)
def ticker_img(): return txt(TICK, "b", 36, WHITE, shadow=False)
@functools.lru_cache(maxsize=1)
def grad_top():
    g = np.linspace(1, 0, 230, dtype=np.float32) ** 1.3; return g[:, None, None]

CHUNKS = []
def build_chunks():
    cur = []
    for i, (w_, s, e) in enumerate(WORDS):
        cur.append(i)
        nxt_gap = WORDS[i + 1][1] - e if i + 1 < len(WORDS) else 9
        if len(cur) >= 4 or w_[-1] in "।?,!" or nxt_gap > .3: CHUNKS.append(cur); cur = []
    if cur: CHUNKS.append(cur)
build_chunks()

def chrome(base, t, sec):
    # top gradient + header
    base[:230] = base[:230] * (1 - .85 * grad_top()) + np.array([.02, .03, .06], np.float32) * .85 * grad_top()
    panel(base, 30, 34, 200, 66, 1, RED, None, op=1, blur=False, rad=12)
    dot = .5 + .5 * math.sin(t * 6); cv2.circle(base, (62, 67), 11, (1, 1, 1 * dot), -1, cv2.LINE_AA)
    over(base, txt("जाँच", "xb", 40, WHITE, shadow=False), 148, 66)
    over(base, txt(TITLES[sec], "xb", 46, WHITE), 260 + tw(TITLES[sec], "xb", 46) / 2 + 22, 66)
    over(base, txt(f"{sec + 1:02d}/10", "sym", 30, (200, 210, 225), shadow=False), 1010, 66)
    # progress bar with 10 segments
    for i in range(10):
        x0 = 30 + i * 103; x1 = x0 + 95
        cv2.rectangle(base, (x0, 128), (x1, 134), (.3, .32, .38), -1)
        if i < sec: cv2.rectangle(base, (x0, 128), (x1, 134), (1, 1, 1), -1)
        elif i == sec:
            f = (t - SECT[i]) / (SECT[i + 1] - SECT[i]); cv2.rectangle(base, (x0, 128), (int(x0 + 95 * f), 134), (1, .25, .3), -1)
    # lower-third strip (covers clip's burned chips) + bottom panel
    LT = ["भारत की सबसे बड़ी पानी कंपनी पर केस", "गोवा फैक्ट्री से 6 सैंपल", "1 सैंपल फेल: ब्रोमेट ज़्यादा", "दूसरी लैब: ब्रोमेट ठीक, पर…",
          "PAH: कैंसर से जुड़ा केमिकल", "तीसरी लैब: PAH पर चुप", "FSSAI से कोई जवाब नहीं", "ब्रोमेट + PAH पर मुकदमा", "बिसलेरी: सिर्फ 1 बैच", "दुकान की बोतलों पर बैन नहीं"]
    base[1428:1560] = base[1428:1560] * .0 + np.array([.03, .05, .1], np.float32)
    cv2.rectangle(base, (0, 1440), (250, 1530), (.85, .12, .17), -1)
    over(base, txt("FSSAI बनाम", "xb", 30, WHITE, shadow=False), 125, 1468); over(base, txt("बिसलेरी", "xb", 38, WHITE, shadow=False), 125, 1506)
    tl_ = t - SECT[sec]; a = ease_out(tl_ / .4); s_ = LT[sec]
    cv2.rectangle(base, (250, 1440), (int(250 + 830 * a), 1530), (.96, .96, .97), -1)
    if a > .5: over(base, txt(s_, "xb", 50, (15, 20, 35), shadow=False), 250 + 30 + tw(s_, "xb", 50) / 2, 1485, clamp01((a - .5) * 2))
    y0 = 1560
    g = np.linspace(0, 1, 90, dtype=np.float32)[:, None, None]
    base[1338:1428] = base[1338:1428] * (1 - .9 * g) + np.array([.03, .05, .1], np.float32) * .9 * g
    base[y0:] = np.array([.03, .05, .1], np.float32)
    cv2.rectangle(base, (0, y0), (W, y0 + 5), (.9, .15, .2), -1)
    # captions (karaoke)
    ch = None
    for c in CHUNKS:
        if WORDS[c[0]][1] - .15 <= t <= WORDS[c[-1]][2] + .35: ch = c
    if ch is None:
        for c in CHUNKS:
            if WORDS[c[0]][1] > t: break
            last = c
        ch = None
    if ch:
        sz = 76; gap = 22; ims = []
        for i in ch:
            wd, s, e = WORDS[i]; active = s - .03 <= t <= e + .12 or (t > e and (i + 1 >= len(WORDS) or t < WORDS[i + 1][1] - .03) and t < e + .35)
            ims.append((txt(wd, "xb", sz, (20, 20, 20) if active else WHITE, shadow=not active), active, tw(wd, "xb", sz), s))
        tot = sum(w_ for _, _, w_, _ in ims) + gap * (len(ims) - 1); x = W / 2 - tot / 2; cy = 1700
        a = clamp01((t - WORDS[ch[0]][1] + .15) / .12)
        for im, active, w_, s in ims:
            if active:
                panel(base, x - 14, cy - 52, w_ + 28, 104, 1, YEL, None, op=1, blur=False, rad=18)
            pop = 1 + .12 * max(0, 1 - (t - s) / .15) if t >= s else 1
            over(base, im, x + w_ / 2, cy - 4, a, pop if active else 1)
            x += w_ + gap
    # ticker
    cv2.rectangle(base, (0, 1832), (W, 1900), (.85, .12, .17), -1)
    panel(base, 0, 1832, 190, 68, 1, (255, 255, 255), None, op=1, blur=False, rad=0)
    tk = ticker_img(); tw_ = tk.shape[1]; off = (t * 120) % tw_
    for k in range(2): over(base, tk, 190 + k * tw_ - off + tw_ / 2, 1866)
    cv2.rectangle(base, (0, 1832), (190, 1900), (1, 1, 1), -1)
    over(base, txt("ताज़ा", "xb", 40, (200, 20, 30), shadow=False), 95, 1866)

# ---------------------------------------------------------------- bubbles (water theme) + grain + vignette
rngb = np.random.default_rng(11); NB = 34
BX = rngb.uniform(0, W, NB); BY = rngb.uniform(0, 1560, NB); BV = rngb.uniform(40, 120, NB); BR = rngb.uniform(4, 16, NB); BP = rngb.uniform(0, 6.3, NB)
def bubbles(base, t):
    lay = np.zeros((H // 2, W // 2, 3), np.float32)
    for i in range(NB):
        x = (BX[i] + 18 * math.sin(t * 1.3 + BP[i])) / 2; y = ((BY[i] - BV[i] * t) % 1500 + 60) / 2; r = BR[i] / 2
        cv2.circle(lay, (int(x), int(y)), max(1, int(r)), (.35, .55, .7), 1, cv2.LINE_AA)
        cv2.circle(lay, (int(x - r * .35), int(y - r * .35)), max(1, int(r * .25)), (.6, .8, .9), -1, cv2.LINE_AA)
    lay = cv2.resize(cv2.GaussianBlur(lay, (0, 0), .8), (W, H)); lay[1560:] = 0
    np.add(base, lay * .55, out=base)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - .5 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - 800) / (H / 2)) ** 2) / 1.414, 0, 1) ** 2.2)[..., None]
del yy, xx

# ---------------------------------------------------------------- footage
class Clip:
    def __init__(self, sec):
        self.sec = sec; s0, s1 = SECT[sec], SECT[sec + 1]; self.dur = s1 - s0
        self.rate = min(1.0, 9.75 / self.dur); self.off = 0.12
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", f"{CLIPS}/b{sec + 1:02d}-designed.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx = -1; self.fr = None; self.prev = None
    def get(self, tl):
        want = int((self.off + tl * self.rate) * 24)
        while self.idx < want:
            b = self.p.stdout.read(720 * 1280 * 3)
            if len(b) < 720 * 1280 * 3: break
            self.prev = self.fr; self.fr = np.frombuffer(b, np.uint8).reshape(1280, 720, 3); self.idx += 1
        return self.fr

PUNCH = [7.25, 19.52, 21.0, 33.54, 36.58, 52.9, 62.63, 69.64, 72.67, 73.86, 84.0, 88.07, 94.67, 96.89]
SHAKES = [7.25, 19.52, 33.54, 36.58, 52.9, 69.64, 94.67]
TRANS = ["flash", "glitch", "whip", "zoom", "leak", "glitch", "whip", "flash", "zoom"]

def frame(t, clip, sec):
    tl = t - SECT[sec]; f = clip.get(tl).astype(np.float32) / 255
    zoom = 1.17 + .08 * (tl / clip.dur) if sec % 2 == 0 else 1.25 - .08 * (tl / clip.dur)
    for p in PUNCH:
        if 0 <= t - p < .5: zoom += .05 * (1 - (t - p) / .5) ** 2
    dx = 18 * math.sin(tl * .4 + sec); dy = -1560 * 0  # framing
    sx, sy = 0, 0
    for s in SHAKES: a, b = shake(s, t); sx += a; sy += b
    # transitions at section start
    tr = TRANS[(sec - 1) % len(TRANS)] if sec > 0 else None; k = tl / .35
    if tr == "zoom" and k < 1: zoom += .35 * (1 - ease_out(k))
    if tr == "whip" and k < 1: dx += 500 * (1 - ease_out(k))
    sc = 1.5 * zoom
    M = np.float32([[sc, 0, W / 2 - 360 * sc + dx + sx], [0, sc, 800 - 640 * sc * (1) + (640 * sc - 800) * 0 + sy + (H / 2 - 800) * 0]])
    # map clip centre (360,640) -> (540+dx, 800)
    M[1, 2] = 800 - 640 * sc + sy
    img = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if tr == "whip" and k < 1:
        n = int(60 * (1 - k)) | 1; img = cv2.blur(img, (n, 1))
    # sharpen + grade
    bl = cv2.GaussianBlur(img, (0, 0), 2.0); img = img + .55 * (img - bl)
    img = (img - .5) * 1.08 + .5
    img *= np.array(TINT[sec], np.float32)
    if tr == "glitch" and k < 1:
        g = int(30 * (1 - k)); img[..., 0] = np.roll(img[..., 0], g, 1); img[..., 2] = np.roll(img[..., 2], -g, 1)
        for b_ in range(5):
            y = int((b_ * 397 + tl * 2000) % 1500); img[y:y + 30] = np.roll(img[y:y + 30], int(80 * (1 - k)) * (1 if b_ % 2 else -1), 1)
    np.clip(img, 0, 1, out=img)
    bubbles(img, t)
    # scan-line HUD sweep
    sy_ = int(170 + (tl * 260) % 1390); img[sy_:sy_ + 3] = img[sy_:sy_ + 3] * .5 + .5 * np.array([.4, .85, 1.0], np.float32)
    img *= VIG
    mg(img, t)
    chrome(img, t, sec)
    if tr == "flash" and k < 1: img += (1 - k) ** 2 * .9
    if tr == "leak" and k < 1.6:
        xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
        img += (1 - k / 1.6) * .7 * np.exp(-((xs - k / 1.6) ** 2) / .03) * np.array([1, .55, .2], np.float32)
    for p in (7.25, 69.64, 94.67, 19.52):
        if 0 <= t - p < .12: img += .35 * (1 - (t - p) / .12)
    if t > END - .5: img *= clamp01((END - t) / .5) * .7 + .3
    if tl < .25 and sec == 0: img *= ease(tl / .25)
    img += np.random.default_rng(int(t * 24)).standard_normal((H // 3, W // 3, 1)).astype(np.float32).repeat(3, 0).repeat(3, 1) * .022
    return img

def render_sec(sec):
    os.makedirs(f"{ROOT}/out", exist_ok=True)
    s0, s1 = SECT[sec], SECT[sec + 1]; n0, n1 = round(s0 * FPS), round(s1 * FPS)
    clip = Clip(sec)
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", f"{ROOT}/out/seg_{sec:02d}.mp4"], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        img = frame(n / FPS, clip, sec)
        p.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); print("done", sec, n1 - n0, flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "still":
        for tt in sys.argv[2:]:
            t = float(tt); sec = max(i for i in range(10) if SECT[i] <= t)
            c = Clip(sec); img = frame(t, c, sec); c.p.kill()
            cv2.imwrite(f"{ROOT}/stills/{t:06.2f}.jpg", cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
    else:
        render_sec(int(sys.argv[1]))
