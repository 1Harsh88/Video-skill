---
name: text-to-animated-video
description: Turn an idea, script, blog URL, PDF or PPT into a finished animated video — scene-by-scene script, a consistent style (2D cartoon, anime-style, comic book, storybook/fantasy, whiteboard, kinetic type), voiceover, word-synced captions, SFX/music — drawn in code and rendered to MP4 in 9:16, 16:9 or 1:1. Use when the user asks for "text to animation", "idea se animated video", an animated explainer, lesson, story, kids video, faceless YouTube episode or animated ad without supplying footage. For video made with generative models (Veo, Kling, Seedance) use ai-video-generator instead; for kinetic motion-graphics showreels/launch films use claude-motion-graphics.
---

# Text → animated video

This is a Fliki-style "text to animation" pipeline (see `references/fliki-notes.md`), but the visuals are drawn in code and rendered in this container, so there are no Fliki or model credits, no watermark and no 3-minute limit.

**Input:** one of
- a one-line idea
- a script
- a blog URL
- a PDF or PPT
- an existing voiceover MP3

**Output:** a finished MP4, plus a WhatsApp copy, in the aspect ratio the user picked.

## Steps

1. **Brief.** Collect these, using the defaults when the user doesn't say:
   - language (default: the user's language; Hinglish/Hindi is fine)
   - tone (neutral)
   - duration (60 s)
   - aspect (9:16 for reels/shorts, 16:9 for YouTube, 1:1 for feed)
   - style preset (see below)
   - voice: the user's MP3, ElevenLabs, or none

   Ask only about what you can't default.
2. **Source → script.**
   - **Idea:** write it yourself.
   - **URL / PDF / PPT:** read the source, keep only facts it supports, and cite it on the end card.
   - **Length:** write a scene-segmented script at about 140 words/min for English, 120 for Hindi.
   - **Structure:** a hook in the first 3 s, one idea per scene, a CTA at the end.
   - **Check:** show the script and wait for OK, unless the user supplied the script.
3. **Scene plan.** Write `plan.json` (shape below) with 1 scene per 4–8 s, and show it as a short table.
   ```json
   {"W":1080,"H":1920,"fps":30,"style":"2d-cartoon","scenes":[
     {"id":1,"t0":0,"t1":5.2,"text":"<voice line>","visual":"<what is drawn>","motion":"<camera/animation>","sfx":["whoosh:0.1"]}]}
   ```
4. **Voice.** Pick one:
   - **User MP3:** use it as is. If music is under the voice, separate the vocals first (demucs) before aligning.
   - **ElevenLabs:** the user needs a key. Ask with `request_credential` for host `api.elevenlabs.io`, header `xi-api-key`. Never ask them to paste the key into the chat. Then call `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` with `model_id` `eleven_multilingual_v2` (or the newest multilingual model the API lists), one request per scene or for the whole script.
   - **No voice:** use captions and SFX only, timing each scene at its planned length.
5. **Align.**
   - `python scripts/align.py voice.wav script.txt words.json 30` gives word times, plus `words_mouth.json` for lip-sync.
   - It needs `pip install --break-system-packages torch torchaudio uroman librosa soundfile` and downloads its model from `download.pytorch.org`, which this environment allows.
   - Re-time `plan.json` scenes to the aligned words. Never guess timings when a voice exists.
6. **Character sheet first** (if the video has characters). Draw each character once as a function with a few poses (idle, talk, point, surprised) and save a PNG sheet. Reuse the same functions in every scene so the characters look identical throughout. Characters must be original; never copy an existing cartoon or anime character.
7. **Build `scene.html`.**
   - One canvas of size W×H.
   - `window.renderAt(t)` must be deterministic: seeded random, no `Date.now()`, no CSS animation.
   - `window.ready` resolves after fonts load. Use local woff2 files: Baloo 2 or Noto Sans Devanagari for Hindi, Inter/Anton/Bangers/Caveat as the style needs.
   - **Captions** are drawn in the canvas:
     - 2–5 words per chunk, breaking at punctuation or at pauses over 0.35 s
     - the active word is highlighted the moment it starts
     - text stays inside the safe zone; for 9:16, nothing in the top 250 px or bottom 420 px
   - **Motion:** eased moves, blinks every 2–5 s, idle sway, a slow push-in per scene, and one transition move between scenes.
8. **Stills check.** Run `node scripts/render.cjs stills scene.html <8–12 times> stills/ W H`, then tile the stills into a contact sheet with ffmpeg `tile`. Look at the sheet yourself, fix problems, then show it to the user and wait for OK before the full render.
9. **Render and mix.**
   - Video: `node scripts/render.cjs video scene.html 0 DUR v.mp4 30 W H`
   - SFX: `python scripts/sfx.py DUR sfx.wav whoosh:3.2 pop:8.1 chime:10.5`
   - Mix the voice at 0 dB and the SFX about −12 dB. Use music only if the user supplies it; duck it under the voice with `sidechaincompress`.
   - Mux, then `loudnorm=I=-14:TP=-1.5`.
10. **Deliver.**
    - Check for black frames with `blackdetect`.
    - Make a WhatsApp/720p copy under 20 MB.
    - Send both files with `SendUserFile`.
    - For other aspect ratios, write the layout as a function of (W,H) and re-render.

## Style presets

| preset | look | motion |
|---|---|---|
| `2d-cartoon` | rounded shapes, flat colour with one shade, dark 4–6 px outline, bright backgrounds | bouncy (back/elastic easing), squash on landings |
| `anime-style` | big eyes, thick clean lines, flat colour + hard shadow, sky gradients | speed lines, impact frames, small screen shake on hits |
| `comic-book` | heavy black ink, halftone shading, panels, burst stickers (POW, WAAH!) | panel slams, zoom-punch, page-flip transitions |
| `storybook` (fantasy) | soft painterly gradients, paper grain, warm light, rounded serif type | slow parallax, drifting particles, gentle fades |
| `whiteboard` | white board, black marker strokes drawn with stroke-dashoffset, one accent colour | a hand/pen follows the stroke being drawn; erase wipes |
| `kinetic-type` | bold type (Anton/Inter Black), 2–3 colours, shapes as accents | words slam, slide and scale on the beat; masks and match cuts |
| `cinematic-2d` | semi-realistic flat illustration, single-source dramatic light, muted palette | slow push-ins and pans only; documentary pacing |

## Rules

- **Draw in code.** Everything is drawn in code: no stock footage and no image or video generators, unless the user supplies media or asks for generated clips (then use `ai-video-generator`).
- **Real people.** Don't make realistic AI likenesses of real, living public figures. Use symbolic imagery, silhouettes, or the user's own caricature drawn from their photos.
- **Facts.** Facts on screen must come from the user's source or verified search. Never invent stats, quotes or testimonials.
- **Overwrites.** Ask before overwriting an existing output file.
