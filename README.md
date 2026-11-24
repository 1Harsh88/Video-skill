# Video skills for Claude

Three Claude Code skills for making videos in code:

| Skill | What it does |
|---|---|
| `claude-motion-graphics` | 83 motion-graphics prompts (showreels, launch films, ads, explainers, experiments) with creator credits, plus a render pipeline |
| `text-to-animated-video` | Idea / script / URL / PDF → code-drawn animated video with style presets, voice alignment, captions and SFX |
| `ai-video-generator` | Shot lists and per-shot prompts for Veo / Kling / Seedance, plus an assembler that finishes clips with voiceover, music, captions and aspect exports |

Install: copy `.claude/skills/<name>` into a project's `.claude/skills/` or `~/.claude/skills/`, or upload each folder as a zip in claude.ai → Settings → Skills.

Prompts in `claude-motion-graphics/references/` were written by the creators credited next to each one (collected from fliki.ai/features/claude-motion-graphics); credit them when you reuse one.

## More video skills (118)

`.claude/skills/` also holds 118 open-source video skills collected from public GitHub repos: HyperFrames, ghost-editor, claude-shorts, FFmpeg skills, Three.js skill packs, Barty-Bart motion-graphics, LottieFiles motion-design, and the 19 iart.ai packs (kinetic typography, map animation, lower thirds, Manim, captions, explainers, charts and more). Each skill folder keeps its original `LICENSE`. Sources and licenses are listed in [CREDITS.md](CREDITS.md).

Install them all into Claude Code:

```bash
cp -r .claude/skills/* ~/.claude/skills/
```
