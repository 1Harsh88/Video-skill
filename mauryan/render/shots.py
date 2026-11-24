"""Footage / image / replacement shots with heavy motion-graphics overlays.
python shots.py v001 i002 ... | all-footage"""
import json, sys, os, math, subprocess, hashlib, numpy as np, cv2
from common import *

MA = "/home/user/video-skill/mauryan"
CLIPS = f"{MA}/media/zip_dl/x"
CMAP = json.load(open(f"{MA}/media/clip_map.json"))
ROWS = json.load(open(f"{MA}/shots_v2.json"))
BYID = {r["id"]: r for r in ROWS}
OUT = f"{ROOT}/out/shots"; os.makedirs(OUT, exist_ok=True)

# ---- frame budget for every row (exact, cumulative, no drift) ----
TOTAL = 784.67
def frame_bounds():
    b = {}
    for i, r in enumerate(ROWS):
        s = round(r["start"] * FPS)
        e = round(ROWS[i + 1]["start"] * FPS) if i + 1 < len(ROWS) else round(TOTAL * FPS)
        b[r["id"]] = (s, e)
    return b
FB = frame_bounds()

# ---- replacements for the 10 clips that could not be generated ----
REPL = {  # id: (source shot id, start sec in that clip, extra effect)
    "v004": ("v003", 3.2, "face"), "v011": ("v001", 3.6, "gold"), "v012": ("v013", 0.2, "freeze_red"),
    "v015": ("v096", 1.0, "lightning"), "v018": ("v017", 3.6, "fire"), "v023": ("v024", 0.1, "warm"),
    "v033": ("v034", 3.5, "seal"), "v044": ("v042", 3.8, "ledger"), "v070": ("v065", 3.6, "glowtext"), "v083": ("v082", 3.6, "fewer"),
}

# ---- motion-graphics overlay specs ----
KW = {  # kinetic words: id: [(text, t_rel, style)]   style: big | word | date | quote
 "v001": [("राजदरबार", .5, "word")], "v002": [("अपमान", .6, "big")], "v003": [("चोटी खोल दी", .8, "word")],
 "v004": [("प्रतिज्ञा", .3, "big")], "v005": [("भारत का सबसे बड़ा साम्राज्य", 1.0, "word")],
 "v006": [("पाटलिपुत्र", .3, "word")], "v007": [("धनानंद का ख़ज़ाना", .4, "word")], "v008": [("भारी कर", .4, "big")],
 "v009": [("326 ईसा पूर्व", .3, "date")], "v010": [("सेना ने मना कर दिया", .6, "word")],
 "v011": [("सबसे ऊँचा आसन", .4, "word")], "v012": [("अपमान!", .2, "big")], "v014": [("दरबार से बाहर", .5, "word")],
 "v015": [("“यह चोटी नहीं बाँधूँगा”", .4, "quote")], "v016": [("न सेना · न धन", .4, "big")], "v017": [("योजना", .5, "big")],
 "v018": [("तलवार चाहिए थी", .6, "word")], "v019": [("राजा-दरबार का खेल", .6, "word")], "v020": [("चंद्रगुप्त", 1.0, "big")],
 "v021": [("कोई राजकुमार नहीं", .6, "word")], "v022": [("शास्त्र · शस्त्र · धैर्य", 1.0, "word")], "v023": [("गरम रोटी — बीच से!", .5, "word")],
 "v024": [("“किनारे से शुरू कर!”", .8, "quote")], "v025": [("पहले सीमाएँ", .6, "big")], "v026": [("321 ईसा पूर्व", .3, "date"), ("नंद वंश का अंत", 1.0, "word")],
 "v027": [("सम्राट चंद्रगुप्त मौर्य", .6, "big")], "v028": [("कसम पूरी", 1.2, "big")], "v029": [("305 ईसा पूर्व", .3, "date")],
 "v030": [("500 युद्ध-हाथी", .5, "big")], "v031": [("वैवाहिक रिश्ता", .6, "word")], "v032": [("?", 1.4, "big")],
 "v033": [("संधि", .5, "big")], "v034": [("हाथ मिलाया", .5, "word")], "v035": [("मेगस्थनीज़", .5, "word")],
 "v036": [("कई मील लंबा शहर", .6, "word")], "v037": [("लकड़ी की दीवार · सैकड़ों बुर्ज", .4, "word")],
 "v038": [("चोरी कम", .4, "big")], "v039": [("युद्ध में भी खेती", .5, "word")], "v040": [("ईमानदार व्यापार", .4, "word")], "v041": [("घरों पर ताले कम", .4, "word")],
 "v042": [("अर्थशास्त्र", .5, "big")], "v043": [("गुप्तचर", .4, "big")], "v044": [("कर · न्याय · व्यापार · युद्ध", .4, "word")],
 "v045": [("जैन परंपरा", .4, "word")], "v046": [("सब कुछ छोड़ दिया", .8, "word")], "v047": [("“क्रूर” राजकुमार", 1.2, "word")],
 "v048": [("चार शेर", .8, "big")], "v049": [("261 ईसा पूर्व", .3, "date"), ("दया नदी", 1.2, "word")], "v050": [("जीत… पर ख़ुशी नहीं", 1.4, "word")],
 "v051": [("पत्थर पर लिखी गलती", .6, "word")], "v053": [("अशोक", .8, "big")], "v054": [("पिता की नापसंदगी", .5, "word")],
 "v056": [("गद्दी के लिए संघर्ष", .4, "word")], "v057": [("चंडाशोक", .5, "big")], "v059": [("बौद्ध ग्रंथ", .4, "word")],
 "v060": [("बढ़ा-चढ़ाकर?", .6, "big")], "v061": [("शुरुआत शांति से नहीं", .6, "word")], "v062": [("हाथी · रथ · घुड़सवार · पैदल", .5, "word")],
 "v063": [("ख़ून से लाल पानी", .8, "word")], "v064": [("13वाँ शिलालेख", .4, "word")], "v066": [("“देवताओं के प्रिय को पछतावा हुआ”", .5, "quote")],
 "v067": [("हत्या · मृत्यु · बिछड़ना", .6, "word")], "v069": [("तलवार रख दी", .8, "big")], "v070": [("अपनी ही जीत पर पछतावा", .5, "word")],
 "v073": [("“सभी मनुष्य मेरी संतान हैं”", .5, "quote")], "v075": [("अब धम्म से विजय", .6, "big")], "v076": [("बड़ों का आदर", .4, "word")],
 "v077": [("जीवों पर दया", .4, "word")], "v078": [("बौद्ध धर्म", .5, "word")], "v079": [("हर पंथ का सम्मान", .5, "word")],
 "v080": [("पेड़ · कुएँ · सड़कें", .4, "word")], "v081": [("धम्म महामात्र", .5, "big")], "v082": [("रोज़ हज़ारों जानवर", .5, "word")],
 "v083": [("अब सिर्फ़ गिने-चुने", .4, "big")], "v084": [("…और जल्द ही वे भी नहीं", .6, "word")], "v085": [("देवानंपिय पियदसी", .5, "big")],
 "v086": [("“सबको प्रेम से देखता है”", .6, "quote")], "v087": [("सारनाथ", .6, "word")], "v089": [("महिंद · संघमित्रा", .8, "word")],
 "v090": [("232 ईसा पूर्व", .3, "date")], "v091": [("185 ईसा पूर्व", .3, "date"), ("अंतिम राजा बृहद्रथ", 1.0, "word")],
 "v093": [("विश्वासघात", .6, "big")], "v094": [("राष्ट्रीय प्रतीक", .6, "word")], "v095": [("असली जीत — दिल में", .8, "big")],
 "v096": [("एक अपमानित ब्राह्मण", .4, "word")], "v097": [("एक गाँव का लड़का", .4, "word")], "v098": [("एक पछताता सम्राट", .4, "word")],
 "i001": [("दरबार हँस पड़ा", .3, "word")], "i002": [("उसका नाम था…", .1, "word")], "i003": [("चंद्रगुप्त", .1, "big")],
 "i007": [("आँखों में जीत नहीं", .2, "word")], "i010": [("कलिंग झुका नहीं", .2, "word")], "i011": [("युद्ध भयानक था", .1, "big")], "i012": [("शिकार छोड़ा", .1, "big")],
}
LT = {"v001": ("चाणक्य", "कौटिल्य · विष्णुगुप्त"), "v007": ("धनानंद", "नंद वंश का अंतिम राजा"), "v027": ("चंद्रगुप्त मौर्य", "मौर्य साम्राज्य के संस्थापक"),
      "v032": ("सेल्यूकस निकेटर", "सिकंदर का सेनापति"), "v035": ("मेगस्थनीज़", "यूनानी राजदूत · इंडिका"), "v053": ("बिंदुसार", "चंद्रगुप्त के पुत्र"),
      "v047": ("अशोक", "बिंदुसार का पुत्र"), "v058": ("सम्राट अशोक", "लगभग 268–232 ईसा पूर्व"), "v091": ("बृहद्रथ", "अंतिम मौर्य राजा"),
      "v092": ("पुष्यमित्र शुंग", "सेनापति"), "v089": ("महिंद और संघमित्रा", "अशोक के पुत्र-पुत्री")}
MM = {"v006": "पाटलिपुत्र", "v009": (73.6, 32.9), "v026": "पाटलिपुत्र", "v029": (71.0, 30.0), "v035": "पाटलिपुत्र", "v045": "श्रवणबेलगोला",
      "v049": "धौली", "v062": "धौली", "v063": "धौली", "v064": "धौली", "v072": "धौली", "v087": "सारनाथ", "v089": "श्रीलंका", "v036": "पाटलिपुत्र"}
SECTION_START = {"v001", "i001", "v047", "v049", "v090"}

def H_(s): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

# ---- source readers ----
def read_clip(path, start, n, src_dur=7.9):
    """Yield n frames (float RGB 1.2x oversize) from path starting at start; slow slightly if needed."""
    need = n / FPS
    if start + need > src_dur: start = max(0.0, src_dur - need)
    speed = min(1.0, (src_dur - start) / need)
    vf = f"fps={FPS * speed:.4f},scale=2304:1296:flags=lanczos" if speed < 1 else "fps=24,scale=2304:1296:flags=lanczos"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fs = 2304 * 1296 * 3; last = None
    for _ in range(n):
        b = p.stdout.read(fs)
        if len(b) == fs: last = np.frombuffer(b, np.uint8).reshape(1296, 2304, 3)
        yield last
    p.stdout.close(); p.wait()

def read_image(path):
    im = cv2.imread(path)[..., ::-1]
    return cv2.resize(im, (2304, 1296), interpolation=cv2.INTER_LANCZOS4)

# ---- look ----
LUT = None
def grade(img):
    img = np.clip(img, 0, 1)
    lum = img.mean(2, keepdims=True)
    img = img + (0.5 - lum) * 0 + (img - lum) * -0.08          # slight desat
    sh = np.clip(1 - lum * 2.2, 0, 1); hi = np.clip(lum * 1.6 - .6, 0, 1)
    img = img + sh * np.array([-0.01, 0.012, 0.03], np.float32) + hi * np.array([0.04, 0.015, -0.03], np.float32)
    img = np.clip(img, 0, 1); img = img * img * (3 - 2 * img) * .35 + img * .65   # gentle S-curve
    return img

def leak(t, seed, strength=.35):
    r = np.random.default_rng(seed); cx = (r.uniform(-.2, .2) + t * .12) % 1.4 - .2; cy = r.uniform(.1, .9)
    yy, xx = np.ogrid[0:H // 4, 0:W // 4]
    g = np.exp(-(((xx / (W / 4) - cx) / .35) ** 2 + ((yy / (H / 4) - cy) / .6) ** 2)).astype(np.float32)
    g = cv2.resize(g, (W, H))[..., None]
    return g * np.array([1.0, 0.55, 0.2], np.float32) * strength

# ---- overlays ----
def pick_side(img):
    """Choose the emptier side of the frame (less detail) for text, so text never sits on the character."""
    g = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    y0, y1 = int(H * .08), int(H * .8)
    L = e[y0:y1, :int(W * .36)].mean() + g[y0:y1, :int(W * .36)].std() * .5
    R = e[y0:y1, int(W * .64):].mean() + g[y0:y1, int(W * .64):].std() * .5
    return "left" if L <= R else "right"

def _place(img, r, side, y, alpha, slide):
    w = r.shape[1]
    x = (90 + w / 2 - slide) if side == "left" else (W - 90 - w / 2 + slide)
    return over(img, r, x, y, alpha=alpha)

def kw_draw(img, items, t, dur, side="left", y0=300):
    y = y0
    for txt, t0, style in items:
        if t < t0: y += 150; continue
        k = ease_out((t - t0) / .45); out = 1 - ease((t - (dur - .35)) / .3); a = k * out
        if style == "big":
            r = text_rgba(txt, "title", 118, fill=GOLD, glow=(140, 50, 0), stroke=2)
            if r.shape[1] > W * .42: r = cv2.resize(r, None, fx=W * .42 / r.shape[1], fy=W * .42 / r.shape[1])
            img = _place(img, r, side, y, a, 50 * (1 - k)); y += r.shape[0] * .8
        elif style == "date":
            r = text_rgba(txt, "semi", 56, fill=BONE, glow=(0, 0, 0))
            img = _place(img, r, side, y - 40, a, 40 * (1 - k))
            xs = 100 if side == "left" else W - 100 - int((r.shape[1] - 60) * k)
            cv2.line(img, (xs, int(y)), (xs + int((r.shape[1] - 60) * k), int(y)), (0.9, 0.72, 0.4), 3, cv2.LINE_AA); y += 110
        elif style == "quote":
            r = text_rgba(txt, "serif", 66, fill=BONE, glow=(0, 0, 0), stroke=2)
            if r.shape[1] > W * .44: r = cv2.resize(r, None, fx=W * .44 / r.shape[1], fy=W * .44 / r.shape[1])
            img = _place(img, r, side, y, a, 60 * (1 - k)); y += r.shape[0] * .9
        else:
            r = text_rgba(txt, "bold", 68, fill=BONE, glow=(0, 0, 0), stroke=3)
            if r.shape[1] > W * .42: r = cv2.resize(r, None, fx=W * .42 / r.shape[1], fy=W * .42 / r.shape[1])
            bw = int((r.shape[1] - 40) * k)
            if bw > 4:
                ov = img.copy()
                xa = 100 if side == "left" else W - 100 - bw
                cv2.rectangle(ov, (xa, int(y - 52)), (xa + bw, int(y + 52)), (0.05, 0.04, 0.03), -1)
                img = img * (1 - .5 * a) + ov * .5 * a
                xb = 92 if side == "left" else W - 100
                cv2.rectangle(img, (xb, int(y - 52)), (xb + 8, int(y + 52)), (0.9, 0.7, 0.35), -1)
            img = _place(img, r, side, y, a, 40 * (1 - k)); y += 140
    return img

def lt_draw(img, name, sub, t, dur, side="left"):
    k = ease_out((t - .3) / .5) * (1 - ease((t - (dur - .4)) / .35))
    if k <= 0: return img
    y0 = H - 290; w = int(600 * k)
    x0 = 90 if side == "left" else W - 90 - w
    ov = img.copy(); cv2.rectangle(ov, (x0, y0), (x0 + w, y0 + 150), (0.04, 0.035, 0.03), -1); img = img * .45 + ov * .55
    xb = x0 if side == "left" else x0 + w - 8
    cv2.rectangle(img, (xb, y0), (xb + 8, y0 + 150), (0.92, 0.72, 0.36), -1)
    r1 = text_rgba(name, "title", 68, fill=GOLD); r2 = text_rgba(sub, "body", 38, fill=(225, 215, 200))
    img = _place(img, r1, side, y0 + 50, k, 0); img = _place(img, r2, side, y0 + 115, k, 0)
    return img

_INSET = {}
def inset(place):
    if place not in _INSET:
        import maps
        lon, lat = maps.PL[place] if isinstance(place, str) else place
        cam = maps.Cam(lon, lat - 1.5, 18, .45); fr = maps.Frame(cam); fr.region(maps.EMPIRE_CG, maps.GREEN, amount=.35)
        fr.pin((lon, lat), 0, 0.3, color=GOLD, label=False)
        img = fr.finish(0)
        sm = cv2.resize(img, (440, 248), interpolation=cv2.INTER_AREA)
        a = np.ones((248, 440, 1), np.float32)
        rgba = np.concatenate([sm, a], 2)
        cv2.rectangle(rgba, (0, 0), (439, 247), (0.9, 0.72, 0.38, 1), 3)
        if isinstance(place, str):
            lab = text_rgba(place, "bold", 34, fill=BONE, stroke=2)
            rgba = over_rgba(rgba, lab, 220, 214)
        _INSET[place] = rgba
    return _INSET[place]

def over_rgba(dst, src, x, y):
    h, w = src.shape[:2]; x0, y0 = int(x - w / 2), int(y - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(dst.shape[1], x0 + w), min(dst.shape[0], y0 + h)
    s = src[ya - y0:yb - y0, xa - x0:xb - x0]; a = s[..., 3:4]
    dst[ya:yb, xa:xb, :3] = dst[ya:yb, xa:xb, :3] * (1 - a) + s[..., :3] * a
    return dst

def mm_draw(img, place, t, dur):
    k = ease_out((t - .5) / .5) * (1 - ease((t - (dur - .4)) / .35))
    if k <= 0: return img
    r = inset(place)
    return over(img, r, W - 90 - 220, 90 + 124 + (1 - k) * -40, alpha=k)

def intro_fx(img, kind, t, prev_dark=False):
    n = 6 / FPS
    if t >= n * 1.6 or kind == "cut": return img
    k = t / n
    if kind == "flash":
        return np.clip(img + (1 - min(1, k)) * np.array([1.0, 0.85, 0.6], np.float32) * .9, 0, 1)
    if kind == "dip":
        return img * min(1, k / 1.6)
    if kind == "burn":
        g = leak(t * 4, 9, strength=1.2 * (1 - min(1, k / 1.6)))
        return np.clip(img + g, 0, 1)
    return img

# ---- the shot renderer ----
def render_shot(sid):
    r = BYID[sid]; s, e = FB[sid]; n = e - s; dur = n / FPS
    h = H_(sid)
    prompt = r["prompt"].lower()
    ember = any(w in prompt for w in ("night", "fire", "torch", "lamp", "battle", "smoke", "storm", "sunset", "burning"))
    parts = Particles(55 if ember else 40, "ember" if ember else "dust", seed=h % 1000)
    zin = (h >> 3) % 2 == 0
    pan = ((h >> 5) % 3 - 1) * 0.02
    trans = ["cut", "flash", "punch", "whip", "burn", "cut", "punch", "whip"][(h >> 7) % 8]
    if sid in SECTION_START: trans = "dip"
    has_leak = (h >> 9) % 3 == 0
    is_img = r["type"] == "IMAGE" and sid != "i001"
    eff = None
    if sid in REPL:
        src_id, off, eff = REPL[sid]; path = os.path.join(CLIPS, CMAP[src_id])
    elif is_img:
        path = os.path.join(CLIPS, CMAP[sid])
    else:
        path = os.path.join(CLIPS, CMAP[sid]); off = 0.35
    w = Writer(f"{OUT}/{sid}.mp4")
    if is_img:
        still = read_image(path); frames = (still for _ in range(n))
    else:
        frames = read_clip(path, off, n)
    for i, fr in enumerate(frames):
        t = i / FPS; p = i / max(1, n - 1)
        src = fr.astype(np.float32) / 255
        if is_img:      # crop away the ✦ watermark: zoom >=1.22 anchored up-left, gentle parallax drift
            z = lerp(1.16, 1.24, ease_io(p)) if zin else lerp(1.24, 1.16, ease_io(p))
            cx, cy = 0.47 + pan * p * .5, 0.47
        else:           # crop away the Veo mark: zoom >=1.09 centred
            z = lerp(1.09, 1.17, ease_io(p)) if zin else lerp(1.17, 1.09, ease_io(p))
            cx, cy = 0.5 + pan * (p - .5), 0.5
        if eff == "face": z = lerp(1.6, 1.85, p); cx, cy = 0.5, 0.36
        if eff == "freeze_red": z = lerp(1.12, 1.4, ease_out(p)); cx, cy = 0.5, 0.5
        if trans == "punch" and t < .3: z *= 1 + .18 * (1 - ease_out(t / .3))
        sw, sh = 2304 / z / 1.2, 1296 / z / 1.2
        x0 = cx * 2304 - sw / 2 * 1.2 * 0 - (2304 / z / 1.2) * 0
        # affine: map output (W,H) to source crop centred at (cx,cy) of size (W/z*1.2?)
        scale = z / 1.2 * (W / 1920)
        M = np.float32([[scale * 1.2 / 1.2, 0, W / 2 - cx * 2304 * scale], [0, scale, H / 2 - cy * 1296 * scale]])
        if trans == "whip" and t < .25:
            sh_px = (1 - ease_out(t / .25)) * W * .5
            M[0, 2] += sh_px
        img = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if trans == "whip" and t < .25:
            k = int(60 * (1 - t / .25)) * 2 + 1
            img = cv2.blur(img, (k, 1))
        # replacement effects
        if eff == "freeze_red":
            img = img * np.array([1.15, .8, .75], np.float32); img = np.clip(img + (0.25 * (math.sin(t * 9) > .6)) * np.array([.5, 0, 0], np.float32), 0, 1)
        if eff == "lightning" and (int(t * 24) in (6, 7, 30, 52, 53)):
            img = np.clip(img * 1.9 + .25, 0, 1)
        if eff == "fire":
            img = np.clip(img + leak(t * .5, 3, .45) * (0.8 + .2 * math.sin(t * 13)), 0, 1)
        if eff == "warm": img = img * np.array([1.08, 1.0, .9], np.float32)
        if eff == "gold":
            g = np.zeros((H, W, 3), np.float32); cv2.ellipse(g, (W // 2, int(H * .55)), (260, 380), 0, 0, 360, (1, .75, .35), -1); img = np.clip(img + cv2.GaussianBlur(g, (0, 0), 60) * .35 * ease(t / 1), 0, 1)
        img = grade(img)
        if has_leak: img = np.clip(img + leak(t, h % 97, .22), 0, 1)
        img = parts.draw(img, t)
        img = img * vignette(0.5)
        # graphics
        if i == 0: side = pick_side(img)
        y0 = 470 if (sid in MM and side == "right") else 300
        if sid in KW: img = kw_draw(img, KW[sid], t, dur, side, y0)
        if sid in LT: img = lt_draw(img, *LT[sid], t, dur, side)
        if sid in MM: img = mm_draw(img, MM[sid], t, dur)
        if eff == "seal" and t > .6:
            sk = ease_out((t - .6) / .25); rr = int(110 * (1.7 - .7 * sk))
            cv2.circle(img, (W - 380, H - 330), rr, (0.62, 0.08, 0.06), -1, cv2.LINE_AA)
            img = over(img, text_rgba("संधि", "title", 64, fill=(245, 205, 175), shadow=False), W - 380, H - 330, alpha=sk)
        if eff == "ledger":
            for j, (lab, val) in enumerate([("कर", 40), ("न्याय", 25), ("व्यापार", 60), ("युद्ध", 35)]):
                k = ease_out((t - .3 - j * .25) / .5)
                y = 380 + j * 120; bw = int(val * 9 * k)
                cv2.rectangle(img, (W - 760, y), (W - 760 + bw, y + 60), (0.88, 0.68, 0.33), -1)
                img = over(img, text_rgba(lab, "bold", 50, fill=BONE, stroke=2), W - 860, y + 30, alpha=k)
        if eff == "glowtext":
            m = np.zeros((H, W, 3), np.float32)
            for j in range(6): cv2.line(m, (560, 330 + j * 70), (int(560 + 800 * ease((t - j * .25) / .8)), 330 + j * 70), (1, .8, .4), 6)
            img = np.clip(img + cv2.GaussianBlur(m, (0, 0), 6) * .9, 0, 1)
        if eff == "fewer":
            k = ease_io((t - .2) / 2.0); val = int(lerp(1000, 2, k))
            img = over(img, text_rgba(f"{val}", "title", 150, fill=(255, 140, 90), glow=(120, 30, 0)), W - 380, 520)
            img = over(img, text_rgba("जानवर / रोज़", "body", 48, fill=BONE), W - 380, 640)
        img = intro_fx(img, trans, t)
        img = img + grain(amt=0.028, seed=(h + i) % 211)
        w.write(np.clip(img, 0, 1))
    w.close()
    return sid

if __name__ == "__main__":
    ids = sys.argv[1:]
    if ids == ["all-footage"]:
        ids = [r["id"] for r in ROWS if r["type"] in ("VIDEO", "IMAGE") and r["id"] not in REPL]
    for sid in ids:
        if os.environ.get("SKIP_DONE") and os.path.exists(f"{OUT}/{sid}.mp4"): continue
        render_shot(sid); print("done", sid, flush=True)
