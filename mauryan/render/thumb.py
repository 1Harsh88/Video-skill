import numpy as np, cv2, subprocess, json
from common import *
CMAP = json.load(open("/home/user/video-skill/mauryan/media/clip_map.json"))
def grab(cid, sec):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(sec), "-i", f"/home/user/video-skill/mauryan/media/zip_dl/x/{CMAP[cid]}", "-frames:v", "1", "-vf", "scale=2112:1188,crop=1920:1080:0:20", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).astype(np.float32) / 255
img = grab("v003", 4.0)
img = img * np.array([1.08, .95, .85], np.float32)
g = np.linspace(1, 0, 1920, dtype=np.float32)[None, :, None]
img = img * (0.35 + 0.65 * (1 - np.clip(g * 1.4 - .4, 0, 1))) if False else img
shade = np.clip(np.linspace(1.0, -0.2, 1920, dtype=np.float32), 0, 1)[None, :, None] * 0.0
img = img * vignette(.6)
left = np.zeros_like(img); left[:, :900] = 1
img = img * (1 - 0.55 * cv2.GaussianBlur(left, (0, 0), 120))
img = over(img, text_rgba("एक ब्राह्मण की", "title", 128, fill=BONE, glow=(0, 0, 0), stroke=4), 470, 300)
img = over(img, text_rgba("प्रतिज्ञा", "title", 230, fill=(255, 160, 60), glow=(170, 40, 0), stroke=5), 470, 500)
img = over(img, text_rgba("मौर्य साम्राज्य", "bold", 92, fill=GOLD, glow=(0, 0, 0), stroke=4), 470, 720)
cv2.imwrite("/home/user/mproj/out/thumbnail.jpg", (np.clip(img, 0, 1)[..., ::-1] * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
print("ok")
