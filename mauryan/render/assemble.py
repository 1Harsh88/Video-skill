"""Concatenate segments in timeline order with exact frame counts, burn captions, mux mixed audio (single encode)."""
import os, subprocess, sys
from shots import ROWS, FB, FPS
R = "/home/user/mproj/out"; X = {"v004", "v011", "v012", "v015", "v018", "v023", "v033", "v044", "v070", "v083"}
with open(f"{R}/concat.txt", "w") as f:
    for r in ROWS:
        sid = r["id"]; s, e = FB[sid]; n = e - s
        d = {"VIDEO": "shots", "IMAGE": "shots", "3D MAP": "maps", "MOTION GFX": "gfx"}[r["type"]]
        if sid in X: d = "gfx"
        p = f"{R}/{d}/{sid}.mp4"
        if not os.path.exists(p): sys.exit("missing " + p)
        f.write(f"file '{p}'\noutpoint {n / FPS:.6f}\n")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{R}/concat.txt", "-i", f"{R}/audio/mix_raw.wav",
                "-vf", f"fps=24,subtitles={R}/audio/captions.ass:fontsdir=/root/.fonts,format=yuv420p", "-map", "0:v", "-map", "1:a",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "784.67", f"{R}/mauryan_final.mp4"], check=True)
print("final written")
