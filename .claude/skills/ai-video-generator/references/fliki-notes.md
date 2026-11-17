# Fliki "AI Video Generator": what it offers (reference)

Source: https://fliki.ai/features/ai-video-generator, read on 2026-11-17. These are Fliki's own claims; models and prices change often.

## Stack
- **Models**, switchable per scene on paid plans: Veo 3.1 (Fast), Kling 3.0 Pro/Standard, MiniMax H3 / H3 Max, Seedance 2.5 / 2.0, LTX-2.5 Fast, PixVerse v5 Fast, P-Video 2. The model gallery also lists Gemini Omni Flash, FLUX 3 Video, GPT Image 2.5, Nano Banana 2 (Lite), Meta Muse and Qwen Image 3.
- **What Fliki says each model is good at:**
  - Veo 3.1: cinematic realism
  - Kling 3.0 Pro: character motion
  - MiniMax H3 Max: synced native audio
  - Seedance 2.5: fluid sequences
  - LTX-2.5: narrative speed
  - PixVerse v5: vivid scenes
- **Image-to-video:** clips up to 20 s, chained into videos up to 15 min, 1080p, any aspect ratio.
- **Finishing layer:**
  - 2,000+ voices in 80+ languages; voice cloning from a 30 s sample
  - AI avatars and talking photos
  - auto captions
  - royalty-free music ducked under the voice
  - stock library, timeline editor, brand kit
  - one-click resize to 9:16, 1:1 and 16:9
- **Workflow:** prompt/script/URL/PPT → model choice → voice/avatar/captions → export, then publish to YouTube, TikTok, Reels, Shorts or LinkedIn.

## Free plan (as stated)
- 3 minutes of video/month, 720p, watermark
- 300+ voices
- stock footage, photos, music and AI images included
- no commercial use
- watermark removed from $28/month; paid plans from $8/month (FAQ)

## Example categories shown on the page
SaaS launch, Brand film, Data story, Cinematic, Creator ad, Food, Fitness, Culture.

## How this skill maps to Fliki

| Fliki | Here |
|---|---|
| model clips | the user generates them from our per-shot prompts (Flow/Veo, Kling, Fliki …) |
| script / scene split | Claude (Mode A) |
| voice | user MP3 or ElevenLabs (user's key) |
| captions, music ducking, resize, export | `scripts/assemble.py` (Mode B) |
