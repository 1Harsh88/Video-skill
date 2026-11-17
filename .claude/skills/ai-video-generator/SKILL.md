---
name: ai-video-generator
description: Plan and finish videos made with generative video models (Google Veo 3.1 / Flow, Kling, Seedance, MiniMax, LTX, PixVerse, Gemini Omni Flash) — turn an idea or script into a shot list with ready-to-paste per-shot prompts (text-to-video and image-to-video), then assemble the clips the user generated into a finished video with voiceover, ducked music, word-highlight captions and 9:16/1:1/16:9 exports. Use when the user asks for "AI video generator", Veo/Kling/Flow prompts, image-to-video, a faceless channel episode or ad made from AI clips, or gives you AI-generated clips to edit together. For code-drawn animation with no model clips use text-to-animated-video.
---

# AI video generator (prompt → clips → finished video)

This mirrors Fliki's "AI video generator" stack (see `references/fliki-notes.md`): generative video models do the shots, and a finishing layer adds voice, captions, music and resizing.

**Model access:** this container has no access to the models. The user generates clips in their own Flow / Kling / Fliki account (or another tool) from the prompts written here. This skill does the planning and the finishing.

## Mode A — plan + prompts

1. **Brief.** Collect these, defaulting when the user doesn't say:
   - topic or script
   - length (default 30–60 s)
   - aspect (9:16 reels, 16:9 YouTube, 1:1 feed)
   - look (cinematic, anime, 3D, UGC phone footage, product studio …)
   - which model(s) they have
   - language for voiceover and captions
2. **Script.** Write a script with a hook in the first 3 s, one idea per shot and a CTA. For facts, use only the user's source or verified search. Show it and wait for OK.
3. **Shot list.** One shot per 3–8 s (most models make 4–10 s clips), as a table: `# | time | VO line | shot | model | t2v or i2v`.
4. **Per-shot prompts.** Use the template in `references/prompt-guide.md`, with one fenced block per shot so the user can copy each one.
   - Every prompt must stand alone: repeat the subject's full description, setting, light, lens, motion, style and aspect ratio. Models don't remember earlier shots.
   - **Consistency:** define each character and product once in a "bible" (face, hair, clothes, colours, props) and paste the same words into every shot. For hard cases, write an image prompt for a reference still first and make the shot image-to-video from it.
   - **Native audio:** if the model generates audio, add an `Audio:` line (ambience and SFX only). Put dialogue in quotes only if the user wants on-camera speech.
   - **What models handle well:** one action per shot. A camera move plus a subject move is fine; three simultaneous events usually fail.
   - **Text:** don't ask models for readable text, logos or UI. Add those in assembly or as code-drawn overlays.
5. **Hand-off.** Give the user:
   - the shot list
   - the prompts
   - a naming rule for the downloads (`s01.mp4`, `s02.mp4` …)
   - "send the clips back here and I'll finish the video"

## Mode B — assemble the clips

1. Get the clips (chat upload, Drive link, or files in the workspace). Contact-sheet them (`ffmpeg … tile`) and check each one against its shot: wrong subject, warped hands or faces, unwanted text. Suggest a re-roll for bad ones instead of using them.
2. **Voice.** Pick one:
   - the user's MP3
   - ElevenLabs via `request_credential` (host `api.elevenlabs.io`, header `xi-api-key`) — never ask for the key in chat
   - none (captions only)
3. If there's a voice, align it to get `words.json`: use `scripts/align.py`.
4. **Write `edit.json`** (format at the top of `scripts/assemble.py`):
   - trim points per clip: cut the first and last 0.3 s, where models often wobble
   - `fit` cover/contain, `fade`
   - voice, music + `music_db`, words, caption style
   - `fontsdir` with local woff2/ttf files, needed for Hindi
5. **Render.** Run `python scripts/assemble.py edit.json final.mp4`. The script normalises every clip to W×H and fps, crossfades, mixes the clip audio, the voice and the music (ducked under the voice), burns word-highlight captions and applies loudnorm −14 LUFS.
6. **Other ratios.** Change W/H and render again. Use `cover` for full-bleed footage and `contain` for wide shots you can't crop.
7. **Deliver.**
   - Check for black frames with `blackdetect`.
   - Make a 720p copy under 20 MB for WhatsApp.
   - Send both with `SendUserFile`.

## Rules

- **Real people:** no realistic AI likeness of real, living people (politicians, celebrities, private people) unless it's the user themself with consent. Use silhouettes or symbolic shots instead. Remind the user that YouTube and Meta require labelling realistic AI-generated content.
- **No made-up claims:** no fake testimonials, invented stats, or UGC that pretends to be a real customer review. A UGC style is fine when the ad doesn't claim to be a real person's experience.
- **Model specs change fast:** clip lengths, prices and model names are dated notes in `references/`. Check the user's tool when it matters, and don't promise exact credits or prices.
