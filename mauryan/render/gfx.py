"""Motion-graphics cards (g001..g021). python gfx.py all | g001 ..."""
import json, sys, os, math, subprocess, numpy as np, cv2
from common import *
from PIL import ImageFont

CLIPS = "/home/user/video-skill/mauryan/media/zip_dl/x"
CMAP = json.load(open("/home/user/video-skill/mauryan/media/clip_map.json"))

def bg(t, kind="night", seed=3):
    """Animated dark background: deep gradient + slow smoke + vignette."""
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]; x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    if kind == "parch":
        base = np.array([0.42, 0.33, 0.21], np.float32) * (1 - 0.35 * ((x - .5) ** 2 + (y - .5) ** 2) * 2)
    elif kind == "red":
        base = np.array([0.10, 0.03, 0.02], np.float32) + np.array([0.25, 0.05, 0.02], np.float32) * np.exp(-((x - .5) ** 2 + (y - .6) ** 2) * 4)
    else:
        base = np.array([0.03, 0.035, 0.05], np.float32) + np.array([0.16, 0.09, 0.04], np.float32) * np.exp(-((x - .5) ** 2 * 3 + (y - .75) ** 2 * 5))
    smoke = _smoke(t, seed)
    out = base + smoke * (0.06 if kind != "parch" else 0.08)
    return np.ascontiguousarray(np.broadcast_to(out, (H, W, 3))).copy()

_SM = {}
def _smoke(t, seed):
    if seed not in _SM:
        r = np.random.default_rng(seed)
        _SM[seed] = [cv2.resize(r.random((9, 16)).astype(np.float32), (W + 400, H), interpolation=cv2.INTER_CUBIC) for _ in range(2)]
    a, b = _SM[seed]
    o1, o2 = int(t * 30) % 400, int(400 - (t * 18) % 400)
    return ((a[:, o1:o1 + W] + b[:, o2:o2 + W]) * 0.5)[..., None]

def finish(img, t, parts=None):
    if parts: img = parts.draw(img, t)
    img = img * vignette(0.55) + grain(amt=0.03, seed=int(t * 24) % 97)
    return np.clip(img, 0, 1)

def fade_io(t, dur, a=.35, b=.35): return ease(t / a) * (1 - ease((t - (dur - b)) / b))

def sweep_reveal(rgba, p):
    """Left-to-right soft reveal of an RGBA image (ink brush feel)."""
    out = rgba.copy(); w = out.shape[1]
    x = np.arange(w, dtype=np.float32)
    m = np.clip((p * (w + 120) - x) / 120, 0, 1)
    out[..., 3] *= m[None, :]
    return out

def frame_from_clip(cid, sec=3.0):
    f = os.path.join(CLIPS, CMAP[cid])
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(sec), "-i", f, "-frames:v", "1", "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255

def chakra(size, angle, color=(0.0, 0.16, 0.5), lw=None):
    img = np.zeros((size, size, 4), np.float32); c = size // 2; R = int(size * .46); lw = lw or max(2, size // 45)
    col = color + (1.0,)
    cv2.circle(img, (c, c), R, col, lw, cv2.LINE_AA); cv2.circle(img, (c, c), int(R * .18), col, -1, cv2.LINE_AA)
    for k in range(24):
        a = angle + k * math.pi / 12
        cv2.line(img, (c, c), (int(c + R * math.cos(a)), int(c + R * math.sin(a))), col, max(1, lw // 2), cv2.LINE_AA)
        cv2.circle(img, (int(c + R * .92 * math.cos(a + math.pi / 24)), int(c + R * .92 * math.sin(a + math.pi / 24))), max(1, lw // 2), col, -1, cv2.LINE_AA)
    return img

def counter_text(n): return f"{n:,}".replace(",", "X").replace("X", ",") if n < 1000 else _indian(n)
def _indian(n):
    s = str(n); last3 = s[-3:]; rest = s[:-3]; parts = []
    while len(rest) > 2: parts.insert(0, rest[-2:]); rest = rest[:-2]
    if rest: parts.insert(0, rest)
    return ",".join(parts + [last3])

def G(gid, dur):
    parts = Particles(60, "ember", seed=hash(gid) % 999)
    if gid in ("g001", "g010"):
        big = "चाणक्य और चंद्रगुप्त मौर्य" if gid == "g001" else "सम्राट अशोक"
        small = text_rgba("आज की रात…", "serif", 64, fill=(220, 205, 180)); T = text_rgba(big, "title", 150 if gid == "g010" else 120, fill=GOLD, glow=(150, 70, 10))
        def f(t):
            img = bg(t); img = over(img, small, W / 2, 400, alpha=ease((t - .1) / .5) * fade_io(t, dur))
            k = ease_out((t - .7) / .8)
            img = over(img, T, W / 2, 560, alpha=k * fade_io(t, dur), scale=1.12 - .12 * k)
            return finish(img, t, parts)
    elif gid == "g002":
        def f(t):
            img = bg(t, "red")
            for row, (lab, n_icons, col, y) in enumerate([("हज़ारों हाथी", 60, (230, 200, 150), 330), ("लाखों सैनिक", 120, (200, 200, 210), 680)]):
                st = .3 + row * 1.6
                k = ease((t - st) / 1.4)
                cnt = int(n_icons * k)
                for i in range(cnt):
                    cols = 30 if row else 20; xx = 700 + (i % cols) * (900 / cols) * (1.0 if row else 1.0); yy = y - 120 + (i // cols) * 34
                    cv2.circle(img, (int(xx), int(yy)), 9 if row == 0 else 6, tuple(c / 255 for c in col), -1, cv2.LINE_AA)
                img = over(img, text_rgba(lab, "title", 96, fill=GOLD, glow=(120, 40, 0)), 300, y - 60, alpha=ease((t - st) / .4))
            img = over(img, text_rgba("— यूनानी लेखकों के अनुसार", "body", 40, fill=(210, 200, 185)), W / 2, 1000, alpha=ease((t - 3) / .5))
            return finish(img, t, parts)
    elif gid == "g003":
        words = [text_rgba(w, "title", 120, fill=GOLD, glow=(120, 50, 0)) for w in ("राजनीति", "अर्थशास्त्र", "युद्धनीति")]
        def f(t):
            img = bg(t, "parch")
            for i, w in enumerate(words):
                p = ease((t - .15 - i * .75) / .6)
                if p > 0: img = over(img, sweep_reveal(w, p), W / 2, 260 + i * 260, alpha=1)
            return finish(img, t)
    elif gid == "g004":
        date = text_rgba("305 ईसा पूर्व", "semi", 70, fill=BONE)
        word = text_rgba("संधि", "title", 190, fill=(70, 40, 20), shadow=False)
        def f(t):
            img = bg(t); img = over(img, date, W / 2, 140, alpha=ease((t - .1) / .4))
            k = ease_out((t - .5) / 1.0)
            sw = int(1100 * k)
            if sw > 10:
                cv2.rectangle(img, (W // 2 - sw // 2, 300), (W // 2 + sw // 2, 800), (0.78, 0.66, 0.45), -1, cv2.LINE_AA)
                for yy in range(320, 800, 40): cv2.line(img, (W // 2 - sw // 2 + 20, yy), (W // 2 + sw // 2 - 20, yy), (0.7, 0.58, 0.38), 1, cv2.LINE_AA)
                cv2.rectangle(img, (W // 2 - sw // 2 - 26, 290), (W // 2 - sw // 2, 810), (0.45, 0.32, 0.18), -1)
                cv2.rectangle(img, (W // 2 + sw // 2, 290), (W // 2 + sw // 2 + 26, 810), (0.45, 0.32, 0.18), -1)
            img = over(img, word, W / 2, 520, alpha=ease((t - 1.4) / .6))
            s = ease_out((t - 2.6) / .25)
            if t > 2.6:
                r = int(95 * (1.6 - .6 * s))
                cv2.circle(img, (W // 2 + 380, 700), r, (0.62, 0.08, 0.06), -1, cv2.LINE_AA)
                cv2.circle(img, (W // 2 + 380, 700), int(r * .7), (0.48, 0.05, 0.04), 4, cv2.LINE_AA)
                img = over(img, text_rgba("मौर्य", "bold", 44, fill=(240, 200, 170), shadow=False), W / 2 + 380, 700, alpha=s)
            return finish(img, t, parts)
    elif gid in ("g005", "g006"):
        labels = ["उद्योग", "विदेशी मेहमान", "जन्म-मृत्यु", "व्यापार", "बिक्री", "कर-वसूली"]
        title = text_rgba("शहर की 6 समितियाँ · 30 अधिकारी", "title", 84, fill=GOLD, glow=(120, 50, 0))
        rng = np.random.default_rng(4); start = rng.uniform([200, 300], [1700, 950], (30, 2))
        def f(t):
            img = bg(t); img = over(img, title, W / 2, 110, alpha=ease((t - .1) / .4) if gid == "g005" else 1)
            k = ease_io((t - .6) / 1.6) if gid == "g005" else 1
            for i in range(30):
                g, j = divmod(i, 5); gx = 330 + (g % 3) * 630; gy = 400 + (g // 3) * 360
                tx, ty = gx - 120 + j * 60, gy
                x, y = lerp(start[i, 0], tx, k), lerp(start[i, 1], ty, k)
                cv2.circle(img, (int(x), int(y - 18)), 13, (0.92, 0.75, 0.42), -1, cv2.LINE_AA)
                cv2.ellipse(img, (int(x), int(y + 22)), (18, 24), 0, 180, 360, (0.92, 0.75, 0.42), -1, cv2.LINE_AA)
            if gid == "g006":
                for g, lab in enumerate(labels):
                    gx = 330 + (g % 3) * 630; gy = 400 + (g // 3) * 360
                    img = over(img, text_rgba(lab, "bold", 54, fill=BONE, glow=(0, 0, 0)), gx, gy + 110, alpha=ease((t - .2 - g * .45) / .35))
            return finish(img, t, parts)
    elif gid == "g007":
        q1 = text_rgba("“प्रजा के सुख में ही", "serif", 96, fill=(50, 28, 12), shadow=False)
        q2 = text_rgba("राजा का सुख है।”", "serif", 96, fill=(50, 28, 12), shadow=False)
        by = text_rgba("— चाणक्य (अर्थशास्त्र)", "semi", 52, fill=(90, 50, 20), shadow=False)
        def f(t):
            img = bg(t, "parch")
            img = over(img, sweep_reveal(q1, ease((t - .3) / 1.0)), W / 2, 420)
            img = over(img, sweep_reveal(q2, ease((t - 1.2) / 1.0)), W / 2, 560)
            img = over(img, by, W / 2 + 300, 720, alpha=ease((t - 2.4) / .6))
            return finish(img, t)
    elif gid == "g008":
        a = text_rgba("भाग 2", "title", 110, fill=(240, 120, 80), glow=(160, 30, 0)); b = text_rgba("सम्राट अशोक और कलिंग", "title", 120, fill=GOLD, glow=(150, 40, 0))
        def f(t):
            img = bg(t, "red"); img = over(img, a, W / 2, 380, alpha=ease((t - .1) / .4), scale=1.3 - .3 * ease_out(t / .5))
            img = over(img, b, W / 2, 580, alpha=ease((t - .8) / .6)); return finish(img, t, parts)
    elif gid == "g009":
        ch = text_rgba("रात और रिवर्ब", "title", 130, fill=GOLD, glow=(140, 60, 0)); gn = text_rgba("शुभ रात्रि", "serif", 70, fill=BONE)
        sub = text_rgba("सब्सक्राइब करें", "bold", 50, fill=(255, 255, 255), shadow=False)
        def f(t):
            img = bg(t); img = over(img, ch, W / 2, 360, alpha=ease((t - .1) / .5))
            k = ease_out((t - .7) / .4); bw, bh = int(460 * k), 100
            if bw > 10:
                pressed = 1.8 < t < 2.1
                c = (0.55, 0.55, 0.55) if t > 2.0 else (0.80, 0.08, 0.08)
                cv2.rectangle(img, (W // 2 - bw // 2, 560), (W // 2 + bw // 2, 560 + bh), c, -1, cv2.LINE_AA)
                img = over(img, sub if t <= 2.0 else text_rgba("सब्सक्राइब्ड ✓", "bold", 50, fill=(255, 255, 255), shadow=False), W / 2, 610, alpha=k, scale=.92 if pressed else 1)
            img = over(img, gn, W / 2, 800, alpha=ease((t - 2.4) / .6)); return finish(img, t, parts)
    elif gid == "g011":
        n = text_rgba("बिंदुसार", "title", 150, fill=GOLD, glow=(140, 60, 0)); s1 = text_rgba("“अमित्रघात”", "serif", 80, fill=BONE); s2 = text_rgba("= शत्रुओं का नाश करने वाला", "body", 56, fill=(220, 205, 180))
        def f(t):
            img = bg(t); img = over(img, n, W / 2, 380, alpha=ease((t - .1) / .4))
            img = over(img, s1, W / 2, 560, alpha=ease((t - .8) / .5)); img = over(img, s2, W / 2, 670, alpha=ease((t - 1.4) / .5)); return finish(img, t, parts)
    elif gid == "g012":
        names = [text_rgba(x, "title", 96, fill=GOLD, glow=(120, 50, 0)) for x in ("चंद्रगुप्त", "बिंदुसार", "अशोक")]
        def f(t):
            img = bg(t)
            for i, nm in enumerate(names):
                y = 220 + i * 320; a = ease((t - .2 - i * .9) / .4)
                img = over(img, nm, W / 2, y, alpha=a)
                if i < 2:
                    p = ease((t - .6 - i * .9) / .5)
                    if p > 0: cv2.line(img, (W // 2, y + 70), (W // 2, int(y + 70 + 180 * p)), (0.9, 0.7, 0.35), 5, cv2.LINE_AA)
            return finish(img, t, parts)
    elif gid in ("g013", "g014"):
        tgt, lab = (150000, "बंदी बनाए गए") if gid == "g013" else (100000, "मारे गए")
        src = text_rgba("— अशोक का 13वाँ शिलालेख", "body", 44, fill=(220, 200, 180))
        more = text_rgba("…और उससे कई गुना मर गए", "serif", 76, fill=(240, 120, 90), glow=(120, 20, 0))
        L = text_rgba(lab, "title", 84, fill=BONE)
        def f(t):
            img = bg(t, "red"); k = ease_out((t - .2) / 1.8)
            num = text_rgba(_indian(int(tgt * k)), "title", 220, fill=(255, 110, 70), glow=(160, 20, 0))
            img = over(img, num, W / 2, 400); img = over(img, L, W / 2, 600, alpha=ease((t - .6) / .5))
            if gid == "g014": img = over(img, more, W / 2, 760, alpha=ease((t - 2.4) / .6))
            img = over(img, src, W / 2, 960, alpha=ease((t - 1.0) / .5)); return finish(img, t, parts)
    elif gid == "g015":
        a = text_rgba("धम्म", "title", 230, fill=GOLD, glow=(160, 80, 0)); b = text_rgba("कोई नया धर्म नहीं — नैतिकता का रास्ता", "semi", 64, fill=BONE)
        def f(t):
            img = bg(t)
            ck = chakra(620, t * .6, color=(0.85, 0.65, 0.3)); img = over(img, ck, W / 2, 420, alpha=0.25 * ease(t / .6))
            img = over(img, a, W / 2, 420, alpha=ease((t - .1) / .5), scale=1.15 - .15 * ease_out(t / .8))
            img = over(img, b, W / 2, 760, alpha=ease((t - 1.2) / .5)); return finish(img, t, parts)
    elif gid in ("g016", "g017"):
        FS = {"brahmi": (f"{ROOT}/assets/fonts/NotoSansBrahmi-Regular.ttf", "𑀤𑁂𑀯𑀸𑀦𑀁𑀧𑀺𑀬"), "khar": (f"{ROOT}/assets/fonts/NotoSansKharoshthi-Regular.ttf", "𐨡𐨅𐨬𐨣𐨤𐨁𐨀"),
              "greek": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "ΒΑΣΙΛΕΥΣ"), "aram": (f"{ROOT}/assets/fonts/NotoSansImperialAramaic-Regular.ttf", "𐡌𐡋𐡊𐡀")}
        names = ["ब्राह्मी", "खरोष्ठी", "यूनानी", "अरामाइक"]
        glyph = []
        for k in ("brahmi", "khar", "greek", "aram"):
            fp, txt = FS[k]; fnt = ImageFont.truetype(fp, 72, layout_engine=ImageFont.Layout.RAQM)
            from PIL import Image, ImageDraw
            l, tt, r, b = fnt.getbbox(txt); im = Image.new("RGBA", (r - l + 40, b - tt + 40), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((20 - l, 20 - tt), txt, font=fnt, fill=(60, 45, 30, 255)); glyph.append(np.asarray(im).astype(np.float32) / 255)
        labs = [text_rgba(n, "bold", 60, fill=GOLD) for n in names]
        def f(t):
            img = bg(t)
            for i in range(4):
                x = 270 + i * 460
                if gid == "g016": k = ease_out((t - .2 - i * .35) / .5); x0 = lerp(W + 300, x, k); sc = 1
                else:
                    k = 1; m = ease_io((t - .4) / 1.6); x0 = lerp(x, 760 + i * 130, m); sc = 1 - .65 * m
                y = 520 if gid == "g016" else lerp(520, 520 + 120 * (i % 2), ease_io((t - .4) / 1.6))
                pw, ph = int(400 * sc), int(520 * sc)
                cv2.rectangle(img, (int(x0 - pw / 2), int(y - ph / 2)), (int(x0 + pw / 2), int(y + ph / 2)), (0.62, 0.55, 0.45), -1, cv2.LINE_AA)
                cv2.rectangle(img, (int(x0 - pw / 2), int(y - ph / 2)), (int(x0 + pw / 2), int(y + ph / 2)), (0.35, 0.28, 0.2), max(1, int(6 * sc)), cv2.LINE_AA)
                img = over(img, glyph[i], x0, y - 40 * sc, scale=sc * min(1.0, 360 / glyph[i].shape[1]))
                img = over(img, labs[i], x0, y + 170 * sc, scale=sc)
            if gid == "g017":
                img = over(img, text_rgba("एक साम्राज्य · चार लिपियाँ", "title", 80, fill=GOLD), W / 2, 150, alpha=ease((t - 1.6) / .5))
            return finish(img, t, parts)
    elif gid == "g018":
        fr = frame_from_clip("v094", 4.0)
        edges = cv2.Canny((fr * 255).astype(np.uint8), 60, 140).astype(np.float32) / 255
        edges = cv2.dilate(edges, np.ones((2, 2), np.uint8)); edges = cv2.GaussianBlur(edges, (0, 0), .8)[..., None]
        lab = text_rgba("भारत का राष्ट्रीय प्रतीक", "title", 90, fill=GOLD, glow=(120, 50, 0)); yr = text_rgba("26 जनवरी 1950 से", "semi", 54, fill=BONE)
        def f(t):
            img = bg(t); k = ease_io((t - .2) / 1.6)
            photo = fr * (1 - k) * 0.9
            line = edges * np.array([1.0, 0.78, 0.4], np.float32) * k * 1.3
            img = np.clip(img * (1 - (1 - k) * .9) + photo + line, 0, 1)
            img = over(img, lab, W / 2, 900, alpha=ease((t - 1.4) / .5)); img = over(img, yr, W / 2, 1000, alpha=ease((t - 2.0) / .5)); return finish(img, t)
    elif gid == "g019":
        def f(t):
            img = bg(t); k = ease_io((t - 1.0) / 1.8)
            fx0, fy0, fw, fh = 460, 230, 1000, 620
            if k > 0:
                a = k
                for i, col in enumerate([(1.0, 0.6, 0.2), (1, 1, 1), (0.07, 0.53, 0.03)]):
                    y0 = fy0 + i * fh // 3
                    img[y0:y0 + fh // 3, fx0:fx0 + fw] = img[y0:y0 + fh // 3, fx0:fx0 + fw] * (1 - a) + np.array(col, np.float32) * a
            m = ease_io(t / 2.6)
            cx, cy = lerp(W / 2, fx0 + fw / 2, m), lerp(H / 2, fy0 + fh / 2, m); size = int(lerp(700, fh // 3 - 10, m))
            ck = chakra(max(20, size), t * 2.5, color=(0.9, 0.7, 0.35) if m < .7 else (0.0, 0.16, 0.5))
            img = over(img, ck, cx, cy)
            img = over(img, text_rgba("अशोक चक्र · 24 तीलियाँ", "title", 80, fill=GOLD), W / 2, 960, alpha=ease((t - 2.4) / .5)); return finish(img, t)
    elif gid in ("g020", "g021"):
        lab1 = text_rgba("321 ईसा पूर्व", "bold", 60, fill=BONE); s1 = text_rgba("चंद्रगुप्त", "serif", 50, fill=GOLD)
        lab2 = text_rgba("185 ईसा पूर्व", "bold", 60, fill=BONE); s2 = text_rgba("बृहद्रथ", "serif", 50, fill=(240, 120, 90))
        big = text_rgba("137 साल", "title", 200, fill=GOLD, glow=(150, 60, 0))
        def f(t):
            img = bg(t); p = ease_io((t - .3) / 2.0) if gid == "g020" else 1
            x0, x1, y = 320, 1600, 620
            cv2.line(img, (x0, y), (int(x0 + (x1 - x0) * p), y), (0.9, 0.72, 0.4), 6, cv2.LINE_AA)
            for i in range(0, 8):
                xx = x0 + (x1 - x0) * i / 7
                if xx <= x0 + (x1 - x0) * p: cv2.line(img, (int(xx), y - 14), (int(xx), y + 14), (0.9, 0.72, 0.4), 3, cv2.LINE_AA)
            img = over(img, lab1, x0, y + 70); img = over(img, s1, x0, y + 140)
            a2 = ease((t - 2.0) / .4) if gid == "g020" else 1
            img = over(img, lab2, x1, y + 70, alpha=a2); img = over(img, s2, x1, y + 140, alpha=a2)
            if gid == "g021": img = over(img, big, W / 2, 380, alpha=ease((t - .2) / .5), scale=1.25 - .25 * ease_out(t / .6))
            return finish(img, t, parts)
    return f


def silhouette_man(img, cx, base_y, h, arm_up=0.0, col=(0.02, 0.015, 0.01)):
    """Simple standing figure silhouette with optional raised right arm (0..1)."""
    s = h / 100
    cv2.circle(img, (int(cx), int(base_y - 92 * s)), max(1, int(8 * s)), col, -1, cv2.LINE_AA)
    cv2.ellipse(img, (int(cx), int(base_y - 101 * s)), (int(3 * s), int(6 * s)), 0, 0, 360, col, -1, cv2.LINE_AA)   # shikha
    body = np.array([[cx - 14 * s, base_y - 82 * s], [cx + 14 * s, base_y - 82 * s], [cx + 18 * s, base_y - 40 * s], [cx + 22 * s, base_y],
                     [cx - 22 * s, base_y], [cx - 18 * s, base_y - 40 * s]], np.int32)
    cv2.fillPoly(img, [body], col, cv2.LINE_AA)
    ang = math.radians(lerp(100, 20, arm_up))
    ex, ey = cx + 14 * s + math.cos(ang) * 0, base_y - 80 * s
    hx, hy = cx + 14 * s + 42 * s * math.sin(math.radians(lerp(160, 20, arm_up))) * .6, base_y - 80 * s - 44 * s * math.cos(math.radians(lerp(160, 20, arm_up)))
    cv2.line(img, (int(ex), int(ey)), (int(hx), int(hy)), col, max(1, int(9 * s)), cv2.LINE_AA)
    cv2.line(img, (int(cx - 14 * s), int(base_y - 80 * s)), (int(cx - 22 * s), int(base_y - 38 * s)), col, max(1, int(9 * s)), cv2.LINE_AA)

def R(rid, dur):
    """Motion-graphics replacements for the clips that could not be generated (no clip is reused)."""
    parts = Particles(70, "ember", seed=hash(rid) % 997)
    if rid == "v004":
        q = text_rgba("“जब तक नंद वंश का नाश नहीं…”", "serif", 80, fill=BONE, glow=(120, 30, 0)); big = text_rgba("प्रतिज्ञा", "title", 200, fill=(255, 150, 70), glow=(170, 40, 0))
        def f(t):
            img = bg(t, "red"); pulse = .5 + .5 * math.sin(t * 7)
            img = np.clip(img + leak(t, 5, .25 + .1 * pulse), 0, 1)
            img = over(img, big, W / 2, 470, alpha=ease(t / .4), scale=1.3 - .3 * ease_out(t / .6) + .02 * pulse)
            img = over(img, q, W / 2, 700, alpha=ease((t - 1.2) / .5)); return finish(img, t, parts)
    elif rid == "v011":
        lab = text_rgba("सबसे ऊँचा आसन", "title", 110, fill=GOLD, glow=(120, 50, 0))
        def f(t):
            img = bg(t)
            for k in range(6):
                x = 220 + k * 300; cv2.rectangle(img, (x, 170), (x + 60, 980), (0.09, 0.07, 0.05), -1)
                cv2.rectangle(img, (x - 15, 150), (x + 75, 185), (0.12, 0.09, 0.06), -1)
            g = ease((t - .4) / 1.2)
            seat = np.zeros((H, W, 3), np.float32)
            cv2.rectangle(seat, (W // 2 - 170, 640), (W // 2 + 170, 700), (1, .75, .35), -1); cv2.rectangle(seat, (W // 2 - 140, 470), (W // 2 + 140, 640), (1, .75, .35), 6)
            img = np.clip(img + cv2.GaussianBlur(seat, (0, 0), 6) * g * .9 + seat * g * .5, 0, 1)
            silhouette_man(img, W // 2, 640, 230 * ease((t - 1.0) / .8) + 1)
            img = over(img, lab, W / 2, 860, alpha=ease((t - 1.6) / .5)); return finish(img, t, parts)
    elif rid == "v012":
        big = text_rgba("अपमान!", "title", 220, fill=(255, 90, 60), glow=(170, 20, 0))
        def f(t):
            img = bg(t, "red"); sh = (math.sin(t * 40) * 8 * max(0, 1 - t / .5))
            img = over(img, big, W / 2 + sh, 470, alpha=ease(t / .2), scale=1.5 - .5 * ease_out(t / .4))
            p = ease((t - .5) / 1.0)
            pts = [(W // 2 - 600 + int(1200 * j / 8), 640 + (40 if j % 2 else -30)) for j in range(9)]
            for j in range(int(8 * p)): cv2.line(img, pts[j], pts[j + 1], (1, .55, .3), 4, cv2.LINE_AA)
            return finish(img, t, parts)
    elif rid == "v015":
        q = text_rgba("“यह चोटी नहीं बाँधूँगा”", "serif", 92, fill=BONE, glow=(0, 0, 0))
        def f(t):
            img = bg(t); img *= np.array([.7, .8, 1.1], np.float32)
            fl = int(t * 24) in (5, 6, 30, 31, 70)
            if fl: img = np.clip(img + .55, 0, 1)
            silhouette_man(img, W // 2, 1000, 520, arm_up=ease_out((t - .3) / .8))
            img = over(img, q, W / 2, 200, alpha=ease((t - 1.2) / .5)); return finish(img, t, parts)
    elif rid == "v018":
        lab = text_rgba("युद्ध की योजना", "title", 110, fill=GOLD, glow=(120, 50, 0))
        def f(t):
            img = bg(t); img = np.clip(img + leak(t * .6, 4, .5 * (0.85 + .15 * math.sin(t * 11))), 0, 1)
            k = ease_io((t - .3) / 2.4)
            path = [(520, 820), (760, 640), (980, 700), (1220, 520), (1420, 380)]
            for j in range(4):
                if k * 4 > j:
                    pp = min(1, k * 4 - j); a, b = path[j], path[j + 1]
                    cv2.line(img, a, (int(lerp(a[0], b[0], pp)), int(lerp(a[1], b[1], pp))), (1, .8, .45), 5, cv2.LINE_AA)
            for (x, y) in path: cv2.circle(img, (x, y), 12, (1, .6, .3), -1, cv2.LINE_AA)
            cv2.circle(img, path[-1], int(40 + 10 * math.sin(t * 6)), (1, .3, .2), 4, cv2.LINE_AA)
            img = over(img, lab, W / 2, 180, alpha=ease((t - .2) / .5)); return finish(img, t, parts)
    elif rid == "v023":
        lab = text_rgba("गरम रोटी — बीच से!", "title", 104, fill=GOLD, glow=(120, 50, 0))
        def f(t):
            img = bg(t, "parch") * .55
            cv2.circle(img, (W // 2, 560), 300, (0.78, 0.6, 0.36), -1, cv2.LINE_AA)
            for j in range(40):
                r = np.random.default_rng(j); x, y = r.integers(W // 2 - 240, W // 2 + 240), r.integers(320, 800)
                if (x - W / 2) ** 2 + (y - 560) ** 2 < 280 ** 2: cv2.circle(img, (int(x), int(y)), int(r.integers(6, 16)), (0.5, 0.34, 0.18), -1, cv2.LINE_AA)
            g = np.zeros((H, W, 3), np.float32); cv2.circle(g, (W // 2, 560), 120, (1, .45, .15), -1)
            img = np.clip(img + cv2.GaussianBlur(g, (0, 0), 40) * (.7 + .3 * math.sin(t * 8)), 0, 1)
            img = over(img, lab, W / 2, 170, alpha=ease((t - .2) / .5)); return finish(img, t, parts)
    elif rid == "v033":
        lab = text_rgba("मौर्य  और  सेल्यूकस", "title", 96, fill=GOLD, glow=(120, 50, 0))
        def f(t):
            img = bg(t); k = ease_io(t / 1.6)
            silhouette_man(img, int(lerp(560, 820, k)), 900, 420, col=(0.03, 0.05, 0.02))
            silhouette_man(img, int(lerp(1360, 1100, k)), 900, 420, col=(0.07, 0.03, 0.02))
            if t > 1.6:
                g = np.zeros((H, W, 3), np.float32); cv2.circle(g, (W // 2, 640), 90, (1, .8, .4), -1)
                img = np.clip(img + cv2.GaussianBlur(g, (0, 0), 50) * ease((t - 1.6) / .5), 0, 1)
            img = over(img, lab, W / 2, 170, alpha=ease((t - .4) / .5)); return finish(img, t, parts)
    elif rid == "v044":
        title = text_rgba("राज्य का हिसाब-किताब", "title", 100, fill=GOLD, glow=(120, 50, 0))
        def f(t):
            img = bg(t, "parch") * .6
            for j, (lab, val) in enumerate([("कर", 70), ("न्याय", 45), ("व्यापार", 85), ("युद्ध", 55)]):
                k = ease_out((t - .3 - j * .3) / .6); y = 360 + j * 150
                cv2.rectangle(img, (620, y), (620 + int(val * 10 * k), y + 80), (0.62, 0.42, 0.18), -1)
                img = over(img, text_rgba(lab, "bold", 60, fill=BONE, stroke=2), 470, y + 40, alpha=k)
            img = over(img, title, W / 2, 180, alpha=ease((t - .1) / .5)); return finish(img, t)
    elif rid == "v070":
        fp = f"{ROOT}/assets/fonts/NotoSansBrahmi-Regular.ttf"
        from PIL import Image, ImageDraw
        fnt = ImageFont.truetype(fp, 64, layout_engine=ImageFont.Layout.RAQM)
        lines = ["𑀤𑁂𑀯𑀸𑀦𑀁𑀧𑀺𑀬𑁂𑀦 𑀧𑀺𑀬𑀤𑀲𑀺𑀦", "𑀮𑀸𑀚𑀺𑀦 𑀓𑀮𑀺𑀁𑀕𑀸 𑀯𑀺𑀚𑀺𑀢𑀸", "𑀅𑀦𑀼𑀲𑀬𑁂 𑀤𑁂𑀯𑀸𑀦𑀁𑀧𑀺𑀬𑀲", "𑀲𑀯𑁂 𑀫𑀼𑀦𑀺𑀲𑁂 𑀧𑀚𑀸 𑀫𑀫𑀸"]
        rows = []
        for ln in lines:
            l, tt, r_, b = fnt.getbbox(ln); im = Image.new("RGBA", (r_ - l + 40, b - tt + 40), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((20 - l, 20 - tt), ln, font=fnt, fill=(255, 205, 120, 255)); rows.append(np.asarray(im).astype(np.float32) / 255)
        rock = None
        def f(t):
            img = bg(t) * 0 + np.array([0.20, 0.17, 0.14], np.float32)
            img = img + _smoke(t * .2, 9) * .25 - .05
            for j, r_ in enumerate(rows):
                p = ease((t - .3 - j * .55) / .7)
                if p > 0: img = over(img, sweep_reveal(r_, p), W / 2, 330 + j * 130, alpha=1)
            img = over(img, text_rgba("अपनी ही जीत पर पछतावा", "bold", 64, fill=BONE, stroke=2), W / 2, 900, alpha=ease((t - 2.4) / .5))
            return finish(img, t)
    elif rid == "v083":
        def f(t):
            img = bg(t); k = ease_io((t - .3) / 2.2); val = int(lerp(1000, 2, k))
            n = int(lerp(60, 2, k))
            for j in range(n):
                x = 420 + (j % 12) * 90; y = 330 + (j // 12) * 90
                cv2.circle(img, (x, y), 20, (0.8, 0.55, 0.3), -1, cv2.LINE_AA)
            img = over(img, text_rgba(str(val), "title", 170, fill=(255, 140, 90), glow=(120, 30, 0)), 1500, 480)
            img = over(img, text_rgba("जानवर / रोज़", "body", 54, fill=BONE), 1500, 610)
            img = over(img, text_rgba("अब सिर्फ़ गिने-चुने", "title", 96, fill=GOLD), W / 2, 900, alpha=ease((t - 2.0) / .5))
            return finish(img, t, parts)
    return f

def leak(t, seed, strength=.35):
    r = np.random.default_rng(seed); cx = (r.uniform(-.2, .2) + t * .12) % 1.4 - .2; cy = r.uniform(.1, .9)
    yy, xx = np.ogrid[0:H // 4, 0:W // 4]
    g = np.exp(-(((xx / (W / 4) - cx) / .35) ** 2 + ((yy / (H / 4) - cy) / .6) ** 2)).astype(np.float32)
    return cv2.resize(g, (W, H))[..., None] * np.array([1.0, 0.55, 0.2], np.float32) * strength

REPL_IDS = ["v004", "v011", "v012", "v015", "v018", "v023", "v033", "v044", "v070", "v083"]

def render(gid, dur, out):
    f = R(gid, dur) if gid in REPL_IDS else G(gid, dur); w = Writer(out)
    for i in range(int(round(dur * FPS))): w.write(f(i / FPS))
    w.close()

if __name__ == "__main__":
    RR = {r["id"]: r for r in json.load(open("/home/user/video-skill/mauryan/shots_v2.json"))}
    ids = [k for k in RR if k.startswith("g")] if sys.argv[1] == "all" else sys.argv[1:]
    still = os.environ.get("STILL")
    for gid in ids:
        dur = RR[gid]["dur"] + 0.5
        if still:
            img = (R(gid, dur) if gid in REPL_IDS else G(gid, dur))(float(still) * dur)
            cv2.imwrite(f"{ROOT}/out/still_{gid}.jpg", (img[..., ::-1] * 255).astype(np.uint8)); continue
        render(gid, dur, f"{ROOT}/out/gfx/{gid}.mp4"); print("done", gid, flush=True)
