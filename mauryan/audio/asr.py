import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
import numpy as np
audio = np.frombuffer(open("audio/vo16k.raw","rb").read(), np.int16).astype(np.float32) / 32768
segs, info = m.transcribe(audio, language="hi", word_timestamps=True, vad_filter=False, beam_size=1)
words = []
for s in segs:
    for w in s.words:
        words.append([round(w.start, 2), round(w.end, 2), w.word.strip()])
json.dump(words, open("audio/asr_words.json", "w"), ensure_ascii=False)
print(len(words), words[-1])
