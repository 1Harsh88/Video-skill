"""2.5D 'documentary' map renderer: tilted relief map with animated regions, arrows, pins, labels.
python maps.py m001 [m002 ...] | all     -> renders out/maps/mXXX.mp4"""
import json, math, sys, os, numpy as np, cv2
from common import *

LON0, LON1, LAT0, LAT1, S = 25.0, 100.0, 0.0, 45.0, 64.0   # texture px per degree
TW, TH = int((LON1 - LON0) * S), int((LAT1 - LAT0) * S)
def P(lon, lat): return ((lon - LON0) * S, (LAT1 - lat) * S)
G = f"{ROOT}/assets/geo"
CACHE = f"{ROOT}/cache"; os.makedirs(CACHE, exist_ok=True)

def _polys(geom):
    t = geom["type"]; c = geom["coordinates"]
    if t == "Polygon": return [c]
    if t == "MultiPolygon": return c
    return []

def build_base():
    """Dark parchment relief map texture (uint8) + land mask + modern-borders layer + rivers layer."""
    fn = f"{CACHE}/base.npz"
    if os.path.exists(fn):
        z = np.load(fn); return z["base"], z["land"], z["borders"], z["rivers"]
    land = np.zeros((TH, TW), np.uint8)
    for f in json.load(open(f"{G}/ne_50m_land.geojson"))["features"]:
        for poly in _polys(f["geometry"]):
            for k, ring in enumerate(poly):
                pts = np.array([P(x, y) for x, y in ring], np.int32)
                cv2.fillPoly(land, [pts], 0 if k else 255, cv2.LINE_AA)
    borders = np.zeros((TH, TW), np.uint8)
    for f in json.load(open(f"{G}/ne_50m_admin_0_countries.geojson"))["features"]:
        for poly in _polys(f["geometry"]):
            for ring in poly:
                pts = np.array([P(x, y) for x, y in ring], np.int32)
                cv2.polylines(borders, [pts], True, 255, 2, cv2.LINE_AA)
    rivers = np.zeros((TH, TW), np.uint8)
    for f in json.load(open(f"{G}/ne_50m_rivers_lake_centerlines.geojson"))["features"]:
        g = f["geometry"]; lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        sr = f["properties"].get("scalerank", 5) or 5
        for ln in lines:
            pts = np.array([P(x, y) for x, y in ln], np.int32)
            cv2.polylines(rivers, [pts], False, 255, 3 if sr <= 3 else 2, cv2.LINE_AA)
    rng = np.random.default_rng(7)
    # fractal relief noise
    relief = np.zeros((TH, TW), np.float32)
    for oc, amp in ((8, 1.0), (32, .5), (128, .25), (512, .12)):
        n = rng.standard_normal((max(2, TH // (TH // oc) if False else oc * TH // TW + 2), oc + 2)).astype(np.float32)
        relief += cv2.resize(n, (TW, TH), interpolation=cv2.INTER_CUBIC) * amp
    # mountains: Himalaya / Hindu Kush band + Western/Eastern Ghats + Vindhya
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    lon = xx / S + LON0; lat = LAT1 - yy / S
    sm = lambda v, a, b, w=2.0: np.clip((v - a) / w, 0, 1) * np.clip((b - v) / w, 0, 1)
    mtn = np.exp(-((lat - (30 + 0.25 * np.clip(80 - lon, -12, 15))) ** 2) / 4.0) * sm(lon, 66, 97, 3)
    mtn += np.exp(-((lat - 35.5) ** 2) / 3) * sm(lon, 63, 75, 2) * 0.8
    mtn += np.exp(-((lon - 74.5) ** 2) / 0.8) * sm(lat, 9, 21, 2) * 0.6
    mtn += np.exp(-((lat - 23.2) ** 2) / 0.6) * sm(lon, 74, 83, 2) * 0.35
    mtn += np.exp(-((lat - 33) ** 2) / 20) * sm(lon, 44, 60, 4) * 0.5
    h = relief * 0.25 + mtn * (1.2 + relief * 0.6)
    h = cv2.GaussianBlur(h, (0, 0), 2)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    shade = np.clip(0.75 + (-gx - gy) * 1.6, 0.35, 1.25)
    lm = (land.astype(np.float32) / 255)[..., None]
    # colors: earthy dark parchment land, deep teal ocean
    landc = np.array([118, 96, 66], np.float32) / 255
    mtnc = np.array([150, 128, 96], np.float32) / 255
    lowc = np.array([84, 92, 58], np.float32) / 255  # greener plains
    mt = np.clip(mtn, 0, 1)[..., None]
    plains = np.clip(1 - mt * 2, 0, 1) * np.clip((lat[..., None] - 18) / 12, 0, 1) * np.clip((30 - lat[..., None]) / 5, 0, 1)
    col = landc * (1 - mt) + mtnc * mt
    col = col * (1 - plains * .5) + lowc * plains * .5
    col = col * shade[..., None]
    dist = cv2.distanceTransform(255 - land, cv2.DIST_L2, 5)
    sea = np.array([18, 44, 58], np.float32) / 255
    deep = np.array([8, 22, 34], np.float32) / 255
    sk = np.clip(dist / (S * 4), 0, 1)[..., None]
    seac = sea * (1 - sk) + deep * sk
    # coastal glow
    coast = np.exp(-(dist / 6) ** 2)[..., None] * (1 - lm)
    seac = seac + coast * np.array([0.12, 0.18, 0.18], np.float32)
    base = col * lm + seac * (1 - lm)
    # paper texture
    paper = cv2.GaussianBlur(rng.standard_normal((TH, TW)).astype(np.float32), (0, 0), 1.2)[..., None] * 0.035
    base = np.clip(base + paper, 0, 1)
    # rivers in base
    rv = (cv2.GaussianBlur(rivers, (0, 0), 0.8).astype(np.float32) / 255)[..., None] * lm
    base = base * (1 - rv * .75) + np.array([60, 120, 150], np.float32) / 255 * rv * .75
    base = (base * 255).astype(np.uint8)
    np.savez_compressed(fn, base=base, land=land, borders=borders, rivers=rivers)
    return base, land, borders, rivers

BASE, LAND, BORD, RIV = build_base()

# ---------------- geography ----------------
PL = {"पाटलिपुत्र": (85.14, 25.61), "तक्षशिला": (72.83, 33.75), "उज्जैन": (75.78, 23.18), "श्रवणबेलगोला": (76.48, 12.86),
      "धौली": (85.84, 20.19), "जौगड़": (84.83, 19.52), "सारनाथ": (83.02, 25.38), "लुंबिनी": (83.28, 27.47), "कंधार": (65.71, 31.61),
      "शाहबाज़गढ़ी": (72.18, 34.23), "गिरनार": (70.50, 21.52), "मास्की": (76.66, 15.96), "साँची": (77.74, 23.48),
      "लौरिया नंदनगढ़": (84.40, 27.00), "पटना": (85.14, 25.61), "श्रीलंका": (80.7, 7.9), "इप्सस": (31.0, 38.6)}
JANAPADA = [("गांधार", 72.5, 34.0), ("कंबोज", 70.5, 35.0), ("कुरु", 77.0, 29.0), ("पांचाल", 79.5, 28.0), ("मत्स्य", 76.0, 27.0),
            ("शूरसेन", 78.0, 26.6), ("कोसल", 82.2, 26.8), ("मल्ल", 84.2, 27.3), ("वज्जि", 85.4, 26.1), ("मगध", 85.4, 25.0),
            ("अंग", 87.0, 25.2), ("काशी", 83.2, 24.6), ("वत्स", 81.8, 25.4), ("चेदि", 79.9, 24.5), ("अवंति", 75.8, 23.2), ("अश्मक", 76.5, 19.5)]
MAGADHA = [(84.0, 26.0), (86.0, 26.2), (87.8, 25.6), (87.5, 24.0), (85.5, 23.6), (84.0, 24.2)]
PUNJAB = [(70.5, 34.5), (75.5, 34.0), (76.8, 31.0), (75.0, 29.0), (71.0, 28.5), (69.5, 31.0)]
SELEUCID = [(25, 45), (68, 39), (71, 36.5), (70.5, 32), (68, 28), (66.5, 24.6), (57, 24), (48, 27), (35, 28), (25, 30)]
CEDED = [(61.5, 25.2), (61, 30.5), (62, 36.5), (70, 36.5), (71, 34.5), (70.5, 31), (68, 27.5), (66.5, 24.6)]
EMPIRE_CG = [(61.5, 25.2), (61, 30.5), (62, 36.5), (70, 36.5), (74, 35.5), (76, 33), (79, 30.5), (81, 29.5), (84.5, 27.5), (88, 27), (90, 26.5), (91, 24),
            (89, 21.8), (86.8, 21.6), (84, 22.3), (82, 22), (80, 21.5), (77, 21.3), (73, 21), (72.6, 21.8), (70, 20.5), (68.8, 22.8), (67.3, 24.6), (66.5, 24.6)]
SOUTH_BIND = [(72.6, 21.8), (73, 21), (77, 21.3), (80, 21.5), (82, 20.2), (81.3, 17.5), (80.3, 14.5), (79.5, 12.5), (77.5, 11.6),
              (75.5, 12.2), (74.6, 14.0), (73.6, 16.5), (72.6, 19.5)]
KALINGA = [(80.2, 21.5), (84, 22.3), (86.8, 21.6), (87.6, 21.4), (86.2, 19.6), (84.6, 18.5), (83.3, 17.6), (82.2, 18.4), (81.0, 19.5), (80.5, 20.6)]
ALEX = [(52.0, 36.0), (59.6, 36.3), (62.2, 34.35), (65.7, 31.6), (69.2, 34.5), (71.5, 34.0), (72.8, 33.7), (73.6, 32.9), (74.8, 31.6)]
ALEX_BACK = [(74.8, 31.6), (72.5, 30.6), (71.0, 28.8), (69.0, 26.5), (68.4, 25.2), (66.5, 25.3), (61.5, 25.4), (57.0, 26.0)]
CG_MARCH = [(72.8, 33.7), (75.0, 31.5), (77.2, 29.6), (79.8, 27.4), (82.5, 26.3), (85.14, 25.61)]
SEL_PUSH = [(55, 33), (60.5, 33), (65.5, 32.4), (69.5, 31.5)]
ELE_WEST = [(70.5, 30.5), (64, 31.0), (57, 31.8), (50, 32.5), (44, 34.5), (38, 37), (31.0, 38.6)]
TO_SHRAVANA = [(85.14, 25.61), (83, 23), (80.5, 20.3), (78.5, 17.5), (77.2, 14.8), (76.48, 12.86)]
TO_KALINGA = [(85.14, 25.61), (85.6, 23.8), (86.0, 22.2), (85.84, 20.19)]
TO_LANKA = [(85.14, 25.61), (86.2, 22.0), (84.8, 18.6), (82.2, 15.8), (80.6, 12.0), (80.6, 8.6)]
TO_WEST = [(85.14, 25.61), (78, 28.6), (70, 32), (62, 33.5), (52, 34), (42, 34.5), (34, 33.5)]
UJ_TAX = [(75.78, 23.18), (74.8, 26.5), (73.8, 30.2), (72.83, 33.75)]
SEA_LANKA = [(86.0, 19.8), (84.8, 16.6), (82.5, 12.5), (81.2, 9.2)]
SEA_SEA = [(86.0, 19.8), (89.5, 17.5), (93.5, 14.5), (97.5, 12.5)]
EDICT_W = ["कंधार", "शाहबाज़गढ़ी", "गिरनार"]
EDICT_E = ["धौली", "जौगड़", "मास्की", "सारनाथ", "लुंबिनी"]
MODERN = ["पटना", "सारनाथ", "साँची", "धौली", "गिरनार", "लौरिया नंदनगढ़"]

# ---------------- camera / drawing ----------------
OVW, OVH = 2400, 1350   # flat working canvas (then tilted to 1920x1080)

class Cam:
    def __init__(self, lon, lat, width, tilt):
        self.lon, self.lat, self.width, self.tilt = lon, lat, width, tilt
    def setup(self):
        cx, cy = P(self.lon, self.lat)
        sw = self.width * S                              # texture px across the working canvas
        self.k = OVW / sw                                # texture->canvas scale
        self.x0, self.y0 = cx - sw / 2, cy - (OVH / self.k) * 0.62   # camera looks slightly 'up' the map
        tilt = self.tilt
        src = np.float32([[0, 0], [OVW, 0], [OVW, OVH], [0, OVH]])
        top_in = 0.5 * W * (1 - tilt * 0.55)
        hor = H * (0.02 + tilt * 0.10)
        dst = np.float32([[W / 2 - top_in - W * 0.25, hor], [W / 2 + top_in + W * 0.25, hor], [W * 1.08, H * 1.04], [-W * 0.08, H * 1.04]])
        self.M = cv2.getPerspectiveTransform(src, dst)
        self.hor = hor
    def tex2c(self, x, y): return ((x - self.x0) * self.k, (y - self.y0) * self.k)
    def ll2c(self, lon, lat): return self.tex2c(*P(lon, lat))
    def ll2s(self, lon, lat):
        x, y = self.ll2c(lon, lat)
        v = self.M @ np.array([x, y, 1.0]); return v[0] / v[2], v[1] / v[2]

def cam_interp(a, b, t):
    t = ease_io(t)
    return Cam(*(lerp(a[i], b[i], t) for i in range(4)))

def crop_base(cam, layer=BASE):
    """Sample the texture into the flat working canvas."""
    A = np.float32([[cam.k, 0, -cam.x0 * cam.k], [0, cam.k, -cam.y0 * cam.k]])
    return cv2.warpAffine(layer, A, (OVW, OVH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

class Frame:
    def __init__(self, cam, modern=False):
        cam.setup(); self.cam = cam
        b = crop_base(cam).astype(np.float32) / 255
        self.land = crop_base(cam, LAND).astype(np.float32)[..., None] / 255
        if modern:
            bd = crop_base(cam, BORD).astype(np.float32)[..., None] / 255
            b = b * (1 - bd * .5) + np.array([0.85, 0.8, 0.65], np.float32) * bd * .5
        self.img = b * 0.82
        self.glow = np.zeros_like(self.img)
        self.labels = []
    def pts(self, ll):
        return np.array([self.cam.ll2c(*p) for p in ll], np.float32)
    def region(self, ll, color, amount=1.0, reveal_from=None, reveal=1.0, outline=True, pulse=0.0):
        if amount <= 0: return
        m = np.zeros((OVH, OVW), np.float32)
        cv2.fillPoly(m, [self.pts(ll).astype(np.int32)], 1.0, cv2.LINE_AA)
        if reveal_from is not None and reveal < 1:
            cx, cy = self.cam.ll2c(*reveal_from)
            yy, xx = np.ogrid[0:OVH, 0:OVW]
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            R = reveal * np.max(np.ptp(self.pts(ll), axis=0)) * 1.6
            m *= np.clip((R - d) / 60 + 1, 0, 1)
        m = cv2.GaussianBlur(m, (0, 0), 2.0)[..., None] * self.land
        c = np.array(color, np.float32) / 255
        a = (0.42 + 0.18 * pulse) * amount
        self.img = self.img * (1 - m * a) + c * m * a
        if outline:
            e = cv2.morphologyEx(m[..., 0], cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))[..., None]
            self.img = self.img + e * c * 0.9 * amount
            self.glow += cv2.GaussianBlur(e, (0, 0), 9)[..., None] * c * 1.4 * amount if e.ndim == 2 else cv2.GaussianBlur(e[..., 0], (0, 0), 9)[..., None] * c * 1.4 * amount
    def line(self, ll, color, progress=1.0, width=7, dashed=False, head=True, glow=True):
        if progress <= 0: return
        pts = self.pts(ll)
        seg = np.sqrt((np.diff(pts, axis=0) ** 2).sum(1)); L = seg.sum(); want = L * min(progress, 1)
        out = [pts[0]]; acc = 0
        for i, s in enumerate(seg):
            if acc + s >= want:
                out.append(pts[i] + (pts[i + 1] - pts[i]) * ((want - acc) / max(s, 1e-6))); break
            acc += s; out.append(pts[i + 1])
        out = np.array(out, np.float32)
        # smooth with chaikin
        for _ in range(3):
            if len(out) < 3: break
            q = 0.75 * out[:-1] + 0.25 * out[1:]; r = 0.25 * out[:-1] + 0.75 * out[1:]
            out = np.vstack([out[:1], np.column_stack([q, r]).reshape(-1, 2), out[-1:]])
        c = tuple(float(v) / 255 for v in color)
        lay = np.zeros((OVH, OVW, 3), np.float32)
        if dashed:
            d = np.sqrt((np.diff(out, axis=0) ** 2).sum(1)); cum = np.concatenate([[0], np.cumsum(d)])
            for i in range(len(out) - 1):
                if int(cum[i] / 26) % 2 == 0:
                    cv2.line(lay, tuple(out[i].astype(int)), tuple(out[i + 1].astype(int)), c, width, cv2.LINE_AA)
        else:
            cv2.polylines(lay, [out.astype(np.int32)], False, c, width, cv2.LINE_AA)
        if head and len(out) >= 2 and progress > 0.02:
            p1, p0 = out[-1], out[-2] if len(out) > 1 else out[-1]
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]); s = width * 4
            tri = np.array([[p1[0] + math.cos(ang) * s, p1[1] + math.sin(ang) * s],
                            [p1[0] + math.cos(ang + 2.5) * s, p1[1] + math.sin(ang + 2.5) * s],
                            [p1[0] + math.cos(ang - 2.5) * s, p1[1] + math.sin(ang - 2.5) * s]], np.int32)
            cv2.fillPoly(lay, [tri], c, cv2.LINE_AA)
        self.img = np.maximum(self.img, lay) if not glow else np.clip(self.img * (1 - (lay.max(2, keepdims=True) > 0) * .0) + 0, 0, 1)
        self.img = np.where(lay.max(2, keepdims=True) > 0.01, lay * 1.0 + self.img * 0.0, self.img)
        if glow: self.glow += cv2.GaussianBlur(lay, (0, 0), 10) * 1.3
    def pin(self, name, t_in, t, color=GOLD, label=True, big=False, sub=None, ring=True):
        if t < t_in: return
        a = ease_out((t - t_in) / 0.45)
        lon, lat = PL[name] if isinstance(name, str) and name in PL else name
        x, y = self.cam.ll2c(lon, lat)
        c = tuple(float(v) / 255 for v in color)
        r = int((10 if big else 7) * (0.4 + 0.6 * a) * 1.6)
        cv2.circle(self.img, (int(x), int(y)), r + 3, (0.05, 0.04, 0.03), -1, cv2.LINE_AA)
        cv2.circle(self.img, (int(x), int(y)), r, c, -1, cv2.LINE_AA)
        if ring:
            ph = ((t - t_in) % 1.6) / 1.6
            rr = int(r + 70 * ph)
            lay = np.zeros((OVH, OVW, 3), np.float32)
            cv2.circle(lay, (int(x), int(y)), rr, tuple(v * (1 - ph) for v in c), 3, cv2.LINE_AA)
            self.glow += lay * 1.5
        g = np.zeros((OVH, OVW, 3), np.float32)
        cv2.circle(g, (int(x), int(y)), r * 3, c, -1, cv2.LINE_AA)
        self.glow += cv2.GaussianBlur(g, (0, 0), 14) * 0.9 * a
        if label:
            self.labels.append((lon, lat, name if isinstance(name, str) else "", a, big, sub, color))
    def text_at(self, lon, lat, txt, a=1.0, big=False, color=BONE, sub=None):
        self.labels.append((lon, lat, txt, a, big, sub, color, True))
    def finish(self, t, title=None, title_a=1.0, date=None, date_a=1.0):
        cam = self.cam
        img = np.clip(self.img + self.glow * 0.6, 0, 1.4)
        out = cv2.warpPerspective(img, cam.M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        # sky / haze above horizon & fog toward far edge
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        hz = cam.hor / H
        fog = np.clip(1 - (yy - hz) / 0.45, 0, 1) ** 2 * 0.65
        skyc = np.array([0.10, 0.12, 0.16], np.float32)
        mask = (out.sum(2, keepdims=True) > 0.001).astype(np.float32)
        out = out * (1 - fog * mask) + skyc * fog * mask
        out = out * mask + (skyc * (0.6 + 0.6 * yy)) * (1 - mask)
        out = out * vignette(0.6)
        for L in self.labels:
            lon, lat, txt, a, big, sub, col = L[:7]
            if not txt or a <= 0.01: continue
            x, y = cam.ll2s(lon, lat)
            is_text = len(L) > 7
            sz = 64 if big else 46
            r = text_rgba(txt, "bold", sz, fill=col if is_text else BONE, stroke=3, glow=(0, 0, 0))
            out = over(out, r, x, y - (0 if is_text else sz * 0.95), alpha=a)
            if sub:
                r2 = text_rgba(sub, "body", int(sz * 0.6), fill=(220, 210, 190), stroke=2)
                out = over(out, r2, x, y - (0 if is_text else sz * 0.95) + sz * 0.85, alpha=a)
        if title:
            r = text_rgba(title, "title", 92, fill=GOLD, stroke=0, glow=(80, 40, 0))
            out = over(out, r, W / 2, 120, alpha=title_a)
        if date:
            r = text_rgba(date, "semi", 54, fill=BONE, glow=(0, 0, 0))
            out = over(out, r, W - 260, H - 110, alpha=date_a)
        out = out + grain(amt=0.025, seed=int(t * 24))
        return np.clip(out, 0, 1)

GREEN = (120, 205, 110); ORANGE = (235, 140, 50); REDC = (235, 70, 55); BLUE = (90, 160, 235)
WIDE = (78, 24, 42, 0.55); NORTH = (80, 27, 26, 0.6)

def shot(mid, dur):
    """Return a frame function f(t)->image for each map shot."""
    def S_(a, b): return lambda t: cam_interp(a, b, t / dur)
    if mid == "m001":
        cam = S_((79, 22, 50, .35), (79, 25, 36, .55))
        def f(t):
            fr = Frame(cam(t))
            for i, (n, lo, la) in enumerate(JANAPADA):
                ti = 0.5 + i * (dur - 1.6) / 16
                if t >= ti:
                    a = ease_out((t - ti) / .4)
                    fr.pin((lo, la), ti, t, color=GOLD, label=False, ring=False)
                    fr.text_at(lo, la + 0.9, n, a=a * 0.95, color=BONE)
            return fr.finish(t, title="16 महाजनपद", title_a=ease((t - .2) / .6), date="~400 ईसा पूर्व", date_a=ease((t - .5) / .6))
    elif mid == "m002":
        cam = S_((80, 25, 34, .55), (85, 25, 14, .7))
        def f(t):
            fr = Frame(cam(t)); fr.region(MAGADHA, GOLD, amount=ease((t - .8) / 1.2), pulse=math.sin(t * 3) * .5 + .5)
            fr.text_at(85.6, 24.6, "मगध", a=ease((t - 1.6) / .6), big=True, color=GOLD)
            fr.text_at(82.8, 26.1, "गंगा", a=ease((t - 1.0) / .6), color=(150, 200, 230))
            fr.text_at(83.8, 24.0, "सोन", a=ease((t - 1.3) / .6), color=(150, 200, 230))
            fr.text_at(84.6, 26.9, "गंडक", a=ease((t - 1.5) / .6), color=(150, 200, 230))
            return fr.finish(t)
    elif mid == "m003":
        cam = S_((85, 25, 14, .7), (85.2, 25.4, 8, .75))
        def f(t):
            fr = Frame(cam(t)); fr.region(MAGADHA, GOLD, amount=0.8)
            fr.pin("पाटलिपुत्र", 0.5, t, big=True, sub="(आज का पटना)")
            return fr.finish(t)
    elif mid == "m004":
        cam = S_((85.2, 25.2, 9, .72), (85.4, 25.0, 8, .74))
        def f(t):
            fr = Frame(cam(t)); fr.region(MAGADHA, GOLD, amount=0.6)
            fr.region([(84.0, 26.0), (87.5, 25.8), (87.5, 25.2), (84.0, 25.3)], (120, 210, 90), reveal_from=(84.0, 25.6), reveal=ease(t / (dur * .8)))
            fr.text_at(85.6, 25.85, "उपजाऊ ज़मीन", a=ease((t - .6) / .5), color=(170, 230, 140), big=True)
            return fr.finish(t)
    elif mid == "m005":
        cam = S_((85.4, 25.0, 8, .74), (85.6, 24.6, 9, .7))
        def f(t):
            fr = Frame(cam(t)); fr.region(MAGADHA, GOLD, amount=0.6)
            for i, (lo, la) in enumerate([(84.4, 24.4), (86.2, 24.5), (87.0, 24.2)]):
                fr.pin((lo, la), .2 + i * .25, t, color=(140, 200, 120), label=False, ring=False)
            fr.text_at(85.3, 24.25, "हाथी वाले जंगल", a=ease((t - .5) / .5), color=(170, 230, 140))
            for i, (lo, la) in enumerate([(85.0, 23.8), (86.5, 23.9)]):
                fr.pin((lo, la), 1.4 + i * .25, t, color=(200, 200, 210), label=False, ring=False)
            fr.text_at(85.8, 23.55, "लोहे की पहाड़ियाँ", a=ease((t - 1.6) / .5), color=(210, 210, 220))
            return fr.finish(t)
    elif mid == "m006":
        cam = S_((62, 31, 34, .5), (70, 31, 24, .6))
        def f(t):
            fr = Frame(cam(t)); fr.line(ALEX, REDC, progress=ease_io(t / (dur * .85)), width=8)
            fr.text_at(57, 37.5, "सिकंदर", a=ease((t - .3) / .5), big=True, color=REDC)
            return fr.finish(t, date="326 ईसा पूर्व", date_a=ease((t - .4) / .6))
    elif mid == "m007":
        cam = S_((70, 30, 24, .6), (66, 29, 28, .55))
        def f(t):
            fr = Frame(cam(t)); fr.line(ALEX, REDC, 1, width=6, head=False, glow=False)
            fr.line(ALEX_BACK, REDC, progress=ease_io(t / (dur * .8)), width=8)
            fl = 0.5 + 0.5 * math.sin(t * 9)
            fr.region(PUNJAB, REDC, amount=0.6 * fl)
            fr.text_at(72.5, 31.5, "अफ़रा-तफ़री", a=ease((t - 1.5) / .5), color=REDC, big=True)
            return fr.finish(t)
    elif mid == "m008":
        cam = S_((76, 27, 26, .55), (72.8, 32.8, 12, .7))
        def f(t):
            fr = Frame(cam(t)); fr.pin("तक्षशिला", 1.4, t, big=True)
            return fr.finish(t)
    elif mid == "m009":
        cam = S_((72.83, 33.0, 10, .66), (72.83, 33.2, 7, .7))
        def f(t):
            fr = Frame(cam(t)); fr.pin("तक्षशिला", 0, t, big=True, sub="प्राचीन विश्वविद्यालय")
            return fr.finish(t)
    elif mid == "m010":
        cam = S_((73, 31.5, 16, .62), (74, 31, 18, .6))
        def f(t):
            fr = Frame(cam(t)); fr.region(PUNJAB, GREEN, reveal_from=PL["तक्षशिला"], reveal=ease(t / (dur * .8)))
            fr.pin("तक्षशिला", 0, t, label=True)
            fr.text_at(73.5, 30.0, "पंजाब", a=ease((t - 2) / .6), big=True, color=GREEN)
            return fr.finish(t)
    elif mid == "m011":
        cam = S_((74, 31, 18, .6), (73.5, 31.2, 15, .64))
        outposts = [(71.8, 33.0), (73.5, 32.0), (72.2, 30.3), (74.6, 31.2), (70.8, 30.6)]
        def f(t):
            fr = Frame(cam(t)); fr.region(PUNJAB, GREEN, amount=1)
            for i, p in enumerate(outposts):
                off = 0.6 + i * 0.8
                if t < off: fr.pin(p, 0, t, color=BLUE, label=False, ring=False)
                elif t < off + 0.35 and int(t * 16) % 2: fr.pin(p, 0, t, color=BLUE, label=False, ring=False)
            fr.text_at(73.3, 33.6, "यूनानी चौकियाँ ख़त्म", a=ease((t - 1.5) / .5), color=BLUE)
            fr.text_at(73.5, 29.6, "स्थानीय योद्धा", a=ease((t - .3) / .5), color=GREEN, big=True)
            return fr.finish(t)
    elif mid == "m012":
        cam = S_((76, 30, 24, .55), (82, 27, 22, .6))
        def f(t):
            fr = Frame(cam(t)); fr.region(PUNJAB, GREEN, amount=.8)
            fr.line(CG_MARCH, GREEN, progress=ease_io(t / (dur * .8)), width=10)
            fr.region(MAGADHA, REDC if t > dur * .8 else GOLD, amount=.7, pulse=1 if t > dur * .8 else 0)
            fr.text_at(85.6, 24.4, "मगध", a=1, big=True, color=GOLD)
            return fr.finish(t)
    elif mid == "m013":
        cam = S_((62, 31, 40, .5), (60, 31, 44, .48))
        def f(t):
            fr = Frame(cam(t)); fr.region(SELEUCID, ORANGE, reveal_from=(40, 33), reveal=ease(t / (dur * .8)))
            fr.region(EMPIRE_CG[7:], GREEN, amount=.5)
            fr.text_at(50, 33, "सेल्यूकस", a=ease((t - 1.0) / .6), big=True, color=ORANGE)
            return fr.finish(t)
    elif mid == "m014":
        cam = S_((62, 31, 40, .5), (68, 30, 28, .56))
        def f(t):
            fr = Frame(cam(t)); fr.region(SELEUCID, ORANGE, amount=1)
            fr.region(EMPIRE_CG[7:], GREEN, amount=.6, pulse=.5 + .5 * math.sin(t * 5))
            fr.line(SEL_PUSH, ORANGE, progress=ease_io(t / (dur * .8)), width=10)
            return fr.finish(t)
    elif mid == "m015":
        cam = S_((66, 30, 22, .58), (67, 30, 20, .6))
        def f(t):
            fr = Frame(cam(t)); fr.region(SELEUCID, ORANGE, amount=.7)
            k = ease((t - 0.8) / (dur * .6))
            fr.region(CEDED, ORANGE, amount=1 - k)
            fr.region(CEDED, GREEN, amount=k, pulse=k)
            fr.text_at(64.5, 32.5, "अराकोसिया", a=ease((t - .4) / .5), color=BONE)
            fr.text_at(64.0, 27.0, "गेड्रोसिया", a=ease((t - .6) / .5), color=BONE)
            fr.text_at(67.5, 35.2, "परोपनिसदै", a=ease((t - .8) / .5), color=BONE)
            return fr.finish(t, title="मौर्यों को मिला" if k > .5 else None, title_a=ease((k - .5) * 4))
    elif mid == "m016":
        cam = S_((60, 33, 44, .5), (45, 35, 44, .5))
        def f(t):
            fr = Frame(cam(t)); fr.region(SELEUCID, ORANGE, amount=.5)
            p = ease_io(t / (dur * .85))
            fr.line(ELE_WEST, (240, 220, 170), progress=p, width=7, dashed=True)
            fr.pin("इप्सस", dur * .85, t, color=REDC, label=False)
            fr.text_at(31, 40.3, "इप्सस का युद्ध", a=ease((t - dur * .85) / .4), big=True, color=REDC, sub="301 ईसा पूर्व")
            fr.text_at(60, 30.0, "500 हाथी", a=ease((t - .3) / .5), color=(240, 220, 170), big=True)
            return fr.finish(t)
    elif mid == "m017":
        cam = S_((78, 26, 26, .62), (77, 25, 44, .5))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=1, pulse=.5 + .5 * math.sin(t * 2.5))
            fr.pin("पाटलिपुत्र", 0, t, label=False)
            return fr.finish(t, title="मौर्य साम्राज्य", title_a=ease((t - .8) / .7), date="हिंदुकुश से बंगाल तक", date_a=ease((t - 1.4) / .6))
    elif mid == "m018":
        cam = S_((85.19, 25.3, 4.5, .6), (85.19, 25.4, 3.6, .65))
        def f(t):
            fr = Frame(cam(t), modern=True)
            fr.pin((85.18, 25.60), .4, t, color=GOLD, label=False); fr.text_at(84.95, 25.85, "कुम्हरार", a=ease((t - .6) / .4), big=True)
            fr.pin((85.215, 25.612), 1.0, t, color=GOLD, label=False); fr.text_at(85.45, 25.85, "बुलंदीबाग़", a=ease((t - 1.2) / .4), big=True)
            return fr.finish(t, date="आधुनिक पटना", date_a=ease((t - .2) / .5))
    elif mid == "m019":
        cam = S_((82, 21, 22, .55), (80, 18, 24, .55))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=.45)
            fr.line(TO_SHRAVANA, (245, 240, 230), progress=ease_io(t / (dur * .85)), width=7, dashed=True)
            fr.pin("पाटलिपुत्र", 0, t, label=False)
            return fr.finish(t)
    elif mid == "m020":
        cam = S_((77.5, 14.5, 11, .62), (76.6, 13.3, 6.5, .7))
        def f(t):
            fr = Frame(cam(t)); fr.line(TO_SHRAVANA, (245, 240, 230), 1, width=6, dashed=True, head=False)
            fr.pin("श्रवणबेलगोला", .5, t, big=True, sub="चंद्रगिरि पहाड़ी")
            return fr.finish(t)
    elif mid == "m021":
        cam = S_((84, 23, 18, .55), (85.6, 20.4, 8, .72))
        def f(t):
            fr = Frame(cam(t)); fr.region(KALINGA, REDC, amount=ease((t - .8) / 1), pulse=.5 + .5 * math.sin(t * 4))
            fr.text_at(84.6, 20.6, "कलिंग", a=ease((t - 1.2) / .5), big=True, color=REDC)
            fr.text_at(85.85, 20.55, "दया नदी", a=ease((t - 2.0) / .5), color=(150, 200, 230))
            return fr.finish(t, date="261 ईसा पूर्व", date_a=ease((t - .4) / .6))
    elif mid == "m022":
        cam = S_((84, 25, 14, .65), (80, 25, 34, .55))
        def f(t):
            fr = Frame(cam(t)); fr.region(MAGADHA, GOLD, amount=1)
            fr.region(EMPIRE_CG, GREEN, reveal_from=PL["पाटलिपुत्र"], reveal=ease((t - 1.0) / (dur - 1.5)))
            return fr.finish(t, title="पिछले भाग में", title_a=ease((t - .2) / .5) * (1 - ease((t - dur + .8) / .6)))
    elif mid == "m023":
        cam = S_((77, 26, 40, .52), (77, 25, 44, .5))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=1, pulse=.5 + .5 * math.sin(t * 2))
            return fr.finish(t, title="चंद्रगुप्त मौर्य का साम्राज्य", title_a=ease((t - .3) / .6))
    elif mid == "m024":
        cam = S_((78, 22, 34, .55), (78, 19, 34, .55))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=1)
            fr.region(SOUTH_BIND, GREEN, reveal_from=(77, 21.3), reveal=ease(t / (dur * .8)))
            fr.text_at(76.5, 15.5, "बिंदुसार", a=ease((t - 1.5) / .5), big=True, color=GREEN, sub="कर्नाटक तक")
            return fr.finish(t)
    elif mid == "m025":
        cam = S_((80, 19, 30, .55), (84, 20, 18, .62))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=.9); fr.region(SOUTH_BIND, GREEN, amount=.9)
            fr.region(KALINGA, REDC, amount=1, pulse=.5 + .5 * math.sin(t * 6))
            fr.text_at(84.4, 20.3, "कलिंग", a=ease((t - .6) / .5), big=True, color=REDC)
            fr.text_at(78.5, 9.8, "तमिल दक्षिण", a=ease((t - .4) / .5), color=BONE)
            return fr.finish(t)
    elif mid == "m026":
        cam = S_((79, 24, 20, .55), (75.8, 23.4, 9, .7))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=.4)
            fr.pin("उज्जैन", 1.0, t, big=True, sub="राज्यपाल: अशोक")
            return fr.finish(t)
    elif mid == "m027":
        cam = S_((75.8, 24, 12, .62), (74, 29, 18, .55))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=.4)
            fr.pin("उज्जैन", 0, t, label=False)
            fr.line(UJ_TAX, (245, 240, 230), progress=ease_io(t / (dur * .75)), width=6, dashed=True)
            fr.pin("तक्षशिला", dur * .7, t, color=REDC, big=True, sub="विद्रोह")
            return fr.finish(t)
    elif mid == "m028":
        cam = S_((84, 24, 16, .6), (85.4, 22, 12, .64))
        def f(t):
            fr = Frame(cam(t)); fr.region(KALINGA, REDC, amount=.8, pulse=.5 + .5 * math.sin(t * 5))
            fr.line(TO_KALINGA, GREEN, progress=ease_io(t / (dur * .85)), width=11)
            fr.pin("पाटलिपुत्र", 0, t, label=True)
            return fr.finish(t, date="अशोक की सेना", date_a=ease((t - .3) / .5))
    elif mid == "m029":
        cam = S_((85.6, 20.4, 8, .66), (85.8, 20.2, 5.5, .7))
        def f(t):
            fr = Frame(cam(t)); fr.region(KALINGA, REDC, amount=.5)
            fr.pin("धौली", .6, t, big=True, sub="धौली पहाड़ी")
            fr.text_at(86.6, 21.0, "दया नदी", a=ease((t - 1.2) / .5), color=(150, 200, 230))
            return fr.finish(t)
    elif mid == "m030":
        cam = S_((85.5, 20.2, 9, .66), (86.5, 19.4, 12, .6))
        ports = [(86.4, 20.3), (85.1, 19.4), (84.2, 18.3)]
        def f(t):
            fr = Frame(cam(t)); fr.region(KALINGA, REDC, amount=.5)
            for i, p in enumerate(ports): fr.pin(p, .3 + i * .3, t, color=(120, 200, 230), label=False)
            fr.text_at(87.5, 18.6, "बंदरगाह", a=ease((t - 1.0) / .5), big=True, color=(150, 210, 235))
            return fr.finish(t)
    elif mid == "m031":
        cam = S_((88, 16, 22, .55), (89, 14, 26, .52))
        def f(t):
            fr = Frame(cam(t)); fr.region(KALINGA, REDC, amount=.5)
            fr.line(SEA_LANKA, (140, 210, 240), progress=ease_io(t / (dur * .7)), width=7, dashed=True)
            fr.line(SEA_SEA, (140, 210, 240), progress=ease_io((t - .4) / (dur * .7)), width=7, dashed=True)
            fr.text_at(81.5, 8.0, "श्रीलंका", a=ease((t - 2.2) / .5), color=BONE)
            fr.text_at(97.0, 14.2, "दक्षिण-पूर्व एशिया", a=ease((t - 2.6) / .5), color=BONE)
            return fr.finish(t)
    elif mid in ("m032", "m033"):
        names = EDICT_W if mid == "m032" else EDICT_E
        cam = S_((70, 28, 26, .55), (72, 27, 30, .52)) if mid == "m032" else S_((82, 22, 26, .55), (79, 24, 40, .5))
        def f(t):
            fr = Frame(cam(t)); fr.region(EMPIRE_CG, GREEN, amount=.35); fr.region(SOUTH_BIND, GREEN, amount=.35); fr.region(KALINGA, GREEN, amount=.35)
            if mid == "m033":
                for n in EDICT_W: fr.pin(n, 0, t, label=False, ring=False)
            for i, n in enumerate(names): fr.pin(n, .4 + i * (dur - 1.4) / len(names), t)
            return fr.finish(t, title="अशोक के शिलालेख", title_a=ease((t - .2) / .6))
    elif mid == "m034":
        cam = S_((84, 19, 26, .55), (82, 15, 26, .55))
        def f(t):
            fr = Frame(cam(t)); fr.line(TO_LANKA, GOLD, progress=ease_io(t / (dur * .85)), width=9)
            fr.text_at(81.0, 6.8, "श्रीलंका", a=ease((t - dur * .7) / .4), big=True, color=GOLD)
            return fr.finish(t, date="धम्म-दूत", date_a=ease((t - .2) / .5))
    elif mid == "m035":
        cam = S_((70, 30, 40, .5), (55, 33, 48, .48))
        def f(t):
            fr = Frame(cam(t)); fr.line(TO_WEST, GOLD, progress=ease_io(t / (dur * .85)), width=9)
            fr.text_at(36, 31.5, "यूनानी राज्य", a=ease((t - dur * .7) / .4), big=True, color=GOLD)
            return fr.finish(t)
    elif mid == "m036":
        cam = S_((78, 23, 40, .5), (78, 24, 36, .52))
        def f(t):
            fr = Frame(cam(t)); k = ease((t - .5) / (dur - 1.2))
            allr = [EMPIRE_CG, SOUTH_BIND, KALINGA]
            fr.region(MAGADHA, GREEN, amount=1)
            for i, rg in enumerate(allr):
                fr.region(rg, GREEN, amount=max(0, 1 - k * (1.2 + i * .5)))
            for i, rg in enumerate(allr):
                if 0.15 < k < .9: fr.region(rg, REDC, amount=.25 * math.sin(k * 30 + i) ** 2, outline=True)
            return fr.finish(t, title="साम्राज्य बिखरने लगा", title_a=ease((t - 1.0) / .6))
    elif mid == "m037":
        cam = S_((80, 23, 30, .55), (80, 23, 26, .58))
        def f(t):
            fr = Frame(cam(t), modern=True)
            for i, n in enumerate(MODERN): fr.pin(n, .3 + i * .55, t)
            return fr.finish(t, title="आज भी मौजूद निशान", title_a=ease((t - .2) / .6))
    return f

def render(mid, dur, out):
    f = shot(mid, dur); w = Writer(out)
    n = int(round(dur * FPS))
    for i in range(n): w.write(f(i / FPS))
    w.close()

if __name__ == "__main__":
    R = {r["id"]: r for r in json.load(open("/home/user/video-skill/mauryan/shots_v2.json"))}
    ids = [k for k in R if k.startswith("m")] if sys.argv[1] == "all" else sys.argv[1:]
    still = os.environ.get("STILL")
    for mid in ids:
        dur = R[mid]["dur"] + 0.5   # handle for transitions
        if still:
            f = shot(mid, dur); img = f(float(still) * dur)
            cv2.imwrite(f"{ROOT}/out/still_{mid}.jpg", (img[..., ::-1] * 255).astype(np.uint8)); continue
        render(mid, dur, f"{ROOT}/out/maps/{mid}.mp4"); print("done", mid, flush=True)
