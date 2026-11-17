"""Word-level forced alignment (torchaudio MMS_FA) for any language incl. Hindi.
usage: python align.py voice.wav script.txt words.json [fps]
writes words.json = [[start,end,word],...] and mouth.json (per-frame 0..1 loudness curve)
setup: pip install --break-system-packages torch torchaudio uroman librosa soundfile numpy
"""
import sys, json, torch, torchaudio, uroman, numpy as np, librosa
from torchaudio.pipelines import MMS_FA as B
wav, txt, out = sys.argv[1:4]; fps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
words = open(txt, encoding='utf-8').read().split()
ur = uroman.Uroman()
norm = lambda s: ''.join(c for c in ur.romanize_string(s).lower() if c in "abcdefghijklmnopqrstuvwxyz'") or 'a'
m, tok, al = B.get_model(), B.get_tokenizer(), B.get_aligner()
w, sr = torchaudio.load(wav); w = torchaudio.functional.resample(w.mean(0, keepdim=True), sr, B.sample_rate)
with torch.inference_mode(): em, _ = m(w)
spans = al(em[0], tok([norm(x) for x in words])); r = w.shape[1] / em.shape[1] / B.sample_rate
wj = [[round(s[0].start * r, 3), round(min(s[-1].end * r, s[0].start * r + 0.8), 3), words[i]] for i, s in enumerate(spans)]
json.dump(wj, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
y, s2 = librosa.load(wav, sr=16000); rms = librosa.feature.rms(y=y, hop_length=16000 // fps)[0]
mouth = np.clip((rms - np.percentile(rms, 20)) / (np.percentile(rms, 95) + 1e-9), 0, 1)
json.dump(np.convolve(mouth, np.ones(3) / 3, 'same').round(3).tolist(), open(out.replace('.json', '') + '_mouth.json', 'w'))
print(len(wj), 'words aligned; last ends at', wj[-1][1] if wj else 0)
