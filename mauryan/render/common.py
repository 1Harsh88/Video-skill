"""Shared helpers: canvas size, fonts, Devanagari text rendering, easing, ffmpeg writer."""
import numpy as np, subprocess, os, math, functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 24
ROOT = "/home/user/mproj"
F = f"{ROOT}/assets/fonts"
FONTS = {
    "title": f"{F}/YatraOne-Regular.ttf",       # display Devanagari
    "serif": f"{F}/TiroDevanagariHindi-Regular.ttf",
    "bold": f"{F}/Mukta-ExtraBold.ttf",
    "semi": f"{F}/Mukta-Bold.ttf",
    "body": f"{F}/Mukta-Medium.ttf",
    "latin": f"{F}/Cinzel-var.ttf",
}
GOLD = (232, 182, 92); EMBER = (255, 140, 50); BONE = (244, 232, 210); INK = (12, 10, 8)
MAURYA = (214, 168, 64); RED = (210, 60, 40); TEAL = (70, 150, 160)

@functools.lru_cache(maxsize=256)
def font(kind, size):
    return ImageFont.truetype(FONTS[kind], size, layout_engine=ImageFont.Layout.RAQM)

@functools.lru_cache(maxsize=512)
def text_rgba(txt, kind="bold", size=80, fill=BONE, stroke=0, stroke_fill=INK, shadow=True, glow=None, lang="hi"):
    """Render shaped text to an RGBA numpy array (premultiplied later)."""
    f = font(kind, size)
    l, t, r, b = f.getbbox(txt, stroke_width=stroke, language=lang)
    pad = int(size * 0.5)
    w, h = r - l + pad * 2, b - t + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pos = (pad - l, pad - t)
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text(pos, txt, font=f, fill=glow + (255,), language=lang, stroke_width=max(2, size // 18), stroke_fill=glow + (255,))
        g = g.filter(ImageFilter.GaussianBlur(size / 6))
        img = Image.alpha_composite(img, g)
    if shadow:
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(s).text((pos[0] + size // 22, pos[1] + size // 18), txt, font=f, fill=(0, 0, 0, 170), language=lang)
        s = s.filter(ImageFilter.GaussianBlur(size / 20))
        img = Image.alpha_composite(img, s)
    d = ImageDraw.Draw(img)
    d.text(pos, txt, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=stroke_fill + (255,), language=lang)
    return np.asarray(img).astype(np.float32) / 255.0

def over(base, rgba, x, y, alpha=1.0, scale=1.0, center=True):
    """Alpha-composite rgba (float 0..1, HxWx4) onto base (float 0..1 HxWx3) at x,y."""
    import cv2
    if alpha <= 0.002: return base
    if abs(scale - 1) > 1e-3:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    if center: x, y = int(round(x - w / 2)), int(round(y - h / 2))
    else: x, y = int(round(x)), int(round(y))
    H_, W_ = base.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W_, x + w), min(H_, y + h)
    if x1 <= x0 or y1 <= y0: return base
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = src[..., 3:4] * alpha
    base[y0:y1, x0:x1] = base[y0:y1, x0:x1] * (1 - a) + src[..., :3] * a
    return base

def ease(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def ease_out(t): t = min(1, max(0, t)); return 1 - (1 - t) ** 3
def ease_io(t): t = min(1, max(0, t)); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def lerp(a, b, t): return a + (b - a) * t

class Writer:
    """Pipe float frames (0..1 RGB) to ffmpeg."""
    def __init__(self, path, fps=FPS, w=W, h=H, crf=17):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                                   "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                                   "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    def write(self, f):
        self.p.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())
    def close(self):
        self.p.stdin.close(); self.p.wait()

def grain(h=H, w=W, amt=0.035, seed=None):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((h // 2, w // 2, 1)).astype(np.float32) * amt).repeat(2, 0).repeat(2, 1)

_VIG = {}
def vignette(strength=0.55, h=H, w=W):
    k = (h, w, strength)
    if k not in _VIG:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
        _VIG[k] = (1 - strength * np.clip(r, 0, 1) ** 2.2)[..., None]
    return _VIG[k]

class Particles:
    """Cheap embers / dust: drifting soft dots drawn additively."""
    def __init__(self, n=70, kind="ember", seed=1):
        r = np.random.default_rng(seed)
        self.kind = kind; self.n = n
        self.x = r.uniform(0, W, n); self.y = r.uniform(0, H, n)
        self.vx = r.uniform(-12, 12, n); self.vy = r.uniform(-60, -15, n) if kind == "ember" else r.uniform(-8, 8, n)
        self.s = r.uniform(1.2, 4.0, n); self.ph = r.uniform(0, 6.28, n)
    def draw(self, base, t):
        import cv2
        layer = np.zeros((H // 2, W // 2, 3), np.float32)
        col = np.array(EMBER if self.kind == "ember" else (230, 220, 200), np.float32) / 255
        for i in range(self.n):
            x = (self.x[i] + self.vx[i] * t + 20 * math.sin(t * .7 + self.ph[i])) % W
            y = (self.y[i] + self.vy[i] * t) % H
            a = (0.55 + 0.45 * math.sin(t * 3 + self.ph[i])) * (0.9 if self.kind == "ember" else 0.35)
            cv2.circle(layer, (int(x / 2), int(y / 2)), max(1, int(self.s[i] / 2)), (col * a).tolist(), -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 1.6)
        layer = cv2.resize(layer, (W, H))
        return np.clip(base + layer, 0, 1)
