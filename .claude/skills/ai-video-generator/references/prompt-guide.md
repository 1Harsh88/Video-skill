# Per-shot prompt template (text-to-video / image-to-video)

Write each prompt as one paragraph in this order. Leave out a line only if it doesn't apply.

```
[Shot type + lens], [subject with full bible description] [doing ONE clear action] in [setting with era/place details].
Camera: [static | slow push-in | dolly left | orbit 30° | handheld | crane up], [speed].
Light: [source + direction + colour temperature], [time of day], [mood].
Style: [cinematic photoreal | anime cel-shaded | 3D Pixar-like soft render | UGC vertical phone footage | studio product shot], [colour grade].
Audio: [ambience + SFX only, if the model makes audio].
Avoid: text, logos, subtitles, extra limbs, distorted faces.
Aspect ratio [9:16 | 16:9 | 1:1], [duration] seconds.
```

## Image-to-video

1. Give the start image.
2. Describe only the **motion** and the camera, not the whole scene again.
3. Keep the motion small for faces and hands.
4. Add "keep the subject's face and clothing unchanged".

## Character / product bible (paste verbatim into every shot)

```
MAYA: Indian woman, late 20s, shoulder-length wavy black hair, small gold nose stud, mustard kurta with white embroidery, blue jeans, brown leather sling bag.
```

## Example (9:16, 3 shots)

```
Medium close-up, 35mm lens, MAYA (Indian woman, late 20s, shoulder-length wavy black hair, small gold nose stud, mustard kurta with white embroidery) looks up from her phone and smiles, on a busy Mumbai local-train platform at golden hour. Camera: slow push-in. Light: warm low sun from the left, soft haze. Style: cinematic photoreal, teal-orange grade. Audio: train announcement echo, crowd murmur. Avoid: text, logos, subtitles. Aspect ratio 9:16, 6 seconds.
```

```
Close-up product shot, 100mm macro, a matte black wireless earbud case opening on a wet slate surface, water droplets on the lid. Camera: static, shallow depth of field. Light: single cool rim light from behind, dark background. Style: premium studio product film. Audio: soft click, low synth swell. Avoid: text, logos. Aspect ratio 9:16, 4 seconds.
```

```
Wide establishing shot, 24mm, a quiet hill village in Uttarakhand at dawn, mist between pine trees, smoke rising from one chimney. Camera: slow crane up. Light: pale blue dawn turning gold on the peaks. Style: cinematic photoreal, soft film grain. Audio: birdsong, distant temple bell. Avoid: text. Aspect ratio 16:9, 8 seconds.
```

## Fixes for common failures

| problem | fix |
|---|---|
| character changes between shots | paste the full bible every time; use image-to-video from one reference still |
| mushy hands or faces | fewer actions; closer framing; shorter clip; image-to-video |
| unwanted text or logos | add an `Avoid:` line; add your own text in assembly |
| too much camera motion | write "camera static" or "very slow", and one move only |
| clip starts or ends with a wobble | trim 0.3 s at both ends in `edit.json` |
