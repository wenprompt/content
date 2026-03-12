---
name: veo-video
description: |
  Expert prompting skill for Google Veo 3.1 video generation. Use this skill whenever the user
  wants to generate video using Veo, Veo 3, Veo 3.1, Google video generation, or mentions using
  Gemini for video creation. Also trigger when the user needs cloud-based video generation with
  native audio, character consistency across scenes, image-to-video with reference images,
  scene extension for longer narratives, or product videos with synchronized sound. If the user
  mentions "ingredients to video" or reference image guided video, this is the skill. Covers
  prompting best practices, scene extension strategies, pricing awareness, and multi-shot
  consistency techniques.
---

# Veo 3.1 Video Generation — Prompting & Workflow Guide

## What is Veo 3.1?

Veo 3.1 is Google DeepMind's flagship AI video generation model (released October 2025,
updated January 2026). Unlike local models like LTX-2.3, Veo 3.1 runs in the cloud via
Google's APIs.

**Key differentiator**: Native synchronized audio generation — dialogue, SFX, ambient sound,
and music are generated alongside the video in a single pass.

**Access methods**: Gemini App, Google AI Studio, Vertex AI, Google Flow, YouTube Create.

**Model variants**:
- `veo-3.1-generate-001` (Standard) — Highest quality, supports reference images
- `veo-3.1-fast-generate-001` (Fast) — Faster generation, lower cost, no reference image support

### Specifications

| Spec | Value |
|------|-------|
| Resolution | 720p, 1080p, 4K (via upscaling) |
| Duration per clip | 4, 6, or 8 seconds |
| Extended duration | Up to ~148s via scene extension |
| Aspect ratios | 16:9 (landscape), 9:16 (portrait/vertical) |
| Frame rate | 24 FPS |
| Audio | Native synchronized (dialogue, SFX, music, ambient); 48kHz sampling rate, lip-sync under 120ms |
| Output | MP4 |
| GCS bucket | Optional — if provided, outputs go to GCS; if omitted, video bytes returned in API response |

### Tier Comparison

| Tier | Speed | Cost/second | Best For |
|------|-------|-------------|----------|
| Veo 3.1 Fast | Fastest | ~$0.15/s (~$0.10/s without audio) | Rapid iteration, drafts |
| Veo 3.1 Standard | Medium | ~$0.40/s | Production with reference images |
| Veo 3.1 Full | Slowest | ~$0.75/s | Highest quality final output |

**Important**: Reference image guidance (Ingredients to Video) is only available in Standard
and Full tiers, not Fast.

---

## The 5-Element Prompt Formula

Every effective Veo 3.1 prompt includes these five components:

### 1. Camera Work
Shot type and movement — use professional cinematography language.

Examples:
- "Wide establishing shot with slow pan right"
- "Close-up with shallow depth of field, 85mm lens"
- "Handheld tracking shot following subject from behind"
- "Low-angle dolly-in with 35mm lens, f/2.8 aperture"

### 2. Subject
Who or what is in the video — be specific about appearance.

Examples:
- "A 30-year-old woman with auburn bob, wearing a denim jacket and silver locket"
- "A matte black luxury watch with rose gold accents on a brushed steel band"
- "A golden retriever with a red bandana, muscular build, alert expression"

### 3. Action
What happens — use specific, concrete verbs.

Examples:
- "She turns toward camera with a curious expression, tilting her head slightly"
- "The watch face catches light as it rotates slowly on the display stand"
- "He jogs through puddles, splashing water that catches backlight"

### 4. Setting
Location, time, weather, environmental details.

Examples:
- "In a sun-drenched Brooklyn brownstone kitchen, morning light through sheer curtains"
- "On a rain-slicked Tokyo street at midnight, neon reflections on wet pavement"
- "Inside a minimalist white studio with diffused overhead lighting"

### 5. Style & Audio
Visual aesthetic + sound design.

Examples:
- "Cinematic, teal-and-orange color grade, anamorphic lens flare. SFX: rain pattering on glass"
- "Documentary style, natural lighting, handheld urgency. A woman says, 'We need to leave now.'"
- "High-key product photography, clean and bright. Subtle ambient electronic music"

---

## Prompt Template

```
[Camera: shot type, movement, lens]. [Subject: detailed appearance]. [Action: specific verbs].
[Setting: location, time, atmosphere]. [Style: aesthetic, color grade]. [Audio: dialogue in
quotes, SFX descriptions, ambient sound].
```

### Example — Product Advertisement
```
Slow dolly-in, macro lens with extreme shallow depth of field. A luxury ceramic coffee mug,
hand-thrown with visible texture lines and a teal glaze, sits on a weathered oak table.
Steam rises in delicate wisps from fresh espresso inside. Morning sunlight from the left
creates warm side-lighting, casting a long shadow across the grain of the wood. Minimalist,
warm-toned product photography. SFX: gentle ceramic clink as the mug settles, distant
morning birdsong.
```

### Example — TikTok Short
```
Handheld close-up, 50mm lens, slight camera shake for energy. A young chef in a black apron
rapidly chops vegetables on a wooden cutting board, knife moving in precise, rhythmic motions.
Commercial kitchen background with stainless steel and warm overhead lighting. Fast-paced,
high-energy edit feel with saturated colors. SFX: rhythmic chopping on wood, sizzle of a
nearby pan, kitchen ambiance.
```

### Example — B-Roll
```
Aerial tracking shot descending gradually toward a coastal highway. Cars weave along a
cliffside road with the Pacific Ocean stretching to the horizon. Late afternoon golden hour
bathes everything in warm amber light, long shadows from cliff edges. Cinematic, 35mm film
grain, desaturated teal shadows with golden highlights. SFX: ocean waves far below, wind
rushing past.
```

---

## Audio Direction

Veo 3.1's native audio is a major advantage. Direct it explicitly:

### Dialogue
Use quotation marks for specific speech:
```
A man in a suit turns to camera and says, "The future starts today."
```

### Sound Effects
Be descriptive and specific:
```
SFX: glass shattering on marble floor, followed by stunned silence
SFX: mechanical whirr of gears engaging, then a satisfying click
SFX: sneakers squeaking on gymnasium floor, crowd cheering distantly
```

### Ambient Sound
Set the atmosphere:
```
Ambient: gentle rain on a tin roof, occasional distant thunder
Ambient: busy café — espresso machine, murmured conversation, clinking cups
Ambient: forest — birdsong, rustling leaves, a stream bubbling nearby
```

### Music
Guide the score:
```
Soft piano melody, contemplative and warm
Upbeat electronic beat, energetic and modern
No music — environmental sounds only
```

---

## Scene Extension — Building Longer Content

Veo 3.1 generates 4-8 second clips natively. For longer content, use **Scene Extension**.

### How It Works

1. Generate your base clip (4-8 seconds)
2. Extension analyzes the final 24 frames (1 second)
3. Generates a new 7-second continuation maintaining:
   - Motion dynamics and momentum
   - Camera trajectory
   - Lighting conditions
   - Scene composition
   - Character appearance
4. Each extension adds ~7 seconds
5. Maximum: 20 extensions = ~148 seconds total
6. Scene extension is limited to 720p in 9:16 or 16:9

### Extension Prompting Strategy

Each extension gets its own prompt describing how the scene continues:

**Base clip prompt:**
```
Wide shot of a woman walking through a sunlit garden path. She wears a white
linen dress, long dark hair flowing. Camera follows from behind at walking pace.
Warm golden hour light filters through overhead trees.
```

**Extension 1 prompt:**
```
She pauses at a bench, turning to look at a bed of blooming lavender. Camera
drifts to her side, revealing her peaceful expression. Bees hover over the
flowers in soft focus. A gentle breeze moves her hair.
```

**Extension 2 prompt:**
```
She reaches down to touch a lavender stem, bringing it to her nose. Close-up
framing tightens on her hand and the purple blooms. Sunlight catches her
silver ring. She smiles softly.
```

---

## Ingredients to Video — Reference Image Guidance

This feature lets you provide up to 3-4 reference images to guide generation
(API baseline is 3; platform dependent). Available in Standard and Full tiers only.

### Best Practice for Reference Images

**Character references** (for consistent identity across scenes):
- Provide 2-3 images: front-facing portrait, three-quarter angle, profile
- Neutral lighting, clear face visibility
- For varied expressions: prepare 6-8 reference images

**Product references**:
- Clean product photography on neutral background
- Multiple angles if available
- Consistent lighting across reference images

**Scene/style references**:
- Establish the visual mood you want
- Color palette, lighting style, composition
- The model matches color palette, lighting, and visual style automatically

### Workflow for Multi-Scene Content with Consistent Characters

1. Create 2-3 reference images of your character
2. Use these same references for every clip in the sequence
3. Repeat IDENTICAL character descriptions across all prompts:
   "Same 30-year-old woman with auburn bob, denim jacket, silver locket"
4. Combine with scene extension for seamless longer narratives

---

## Continuity Table for Multi-Shot Projects

Maintain this table across all prompts in a project to keep consistency:

```
| Element | Description (COPY EXACTLY to each prompt) |
|---------|------------------------------------------|
| Character | 30-year-old woman, auburn bob, denim jacket, silver locket |
| Wardrobe | Dark blue denim jacket, white t-shirt underneath, silver locket on thin chain |
| Props | Leather-bound journal, black pen |
| Lens | 50mm f/1.8 |
| Color grade | Warm, teal-and-orange, slightly desaturated |
| Lighting | Warm tungsten key light from upper-left, soft fill |
| Time | Late afternoon, golden hour |
| Weather | Clear, warm |
| Setting | Brooklyn brownstone interior |
```

Copy the relevant descriptors verbatim into each prompt. Changing even small words
(e.g., "blue jacket" vs "denim jacket") can break character consistency.

---

## Content-Type Prompt Strategies

### Product Advertisements
- Lead with camera specification (macro, overhead, product reveal)
- Use "timestamp prompting" for second-by-second control in complex scenes
- Specify exact lighting setup (key, fill, rim, background)
- Include audio that reinforces product quality (satisfying clicks, premium sounds)

### B-Roll
- Vary shot types across clips: wide, medium, close-up, POV, aerial
- Generate 8-second clips for maximum editing flexibility
- Include natural ambient audio — b-roll without sound feels incomplete
- Plan 3-5 different angles/compositions per subject

### Short-Form Social (TikTok/Reels)
- Use 9:16 portrait aspect ratio
- Front-load the hook — most dramatic visual in the first second
- Faster camera movements than traditional video
- Include trendy audio cues or energetic music direction
- 4-6 second clips chain together well for 15-30 second final pieces

### Animated Shorts
- Specify animation style explicitly: "2D cel animation", "3D Pixar style", "anime"
- Camera work should complement, not compete with animation
- Audio is critical — voice acting direction, foley, score
- Use scene extension for narrative flow between beats

---

## Negative Prompt Techniques for Veo 3.1

Unlike LTX-2.3, Veo 3.1 doesn't use a separate negative prompt field.
Instead, phrase exclusions positively:

**Instead of**: "no buildings"
**Say**: "desolate landscape with only natural elements, no man-made structures visible"

**Instead of**: "no blur"
**Say**: "sharp focus throughout, crisp details on all elements"

**Instead of**: "no text"
**Say**: "clean visual without any overlaid text, watermarks, or graphics"

---

## When to Choose Veo 3.1 vs LTX-2.3

| Scenario | Choose Veo 3.1 | Choose LTX-2.3 |
|----------|----------------|----------------|
| Need synchronized audio | Yes | No (audio separate) |
| Need character consistency | Yes (with references) | Limited |
| Want local/free generation | No (cloud, paid) | Yes (local, free) |
| Need 4K output | Yes (upscaling) | Yes (latent upscaler) |
| Need LoRA customization | No | Yes (camera + custom LoRAs) |
| Rapid iteration | LTX faster locally | Cloud has queue times |
| Product video with sound | Veo 3.1 excels | Need separate audio |
| Privacy-sensitive content | No (cloud processing) | Yes (fully local) |
