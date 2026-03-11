---
name: sora-video
description: |
  Expert prompting skill for OpenAI Sora 2 video generation and ChatGPT image generation (GPT-4o).
  Use this skill whenever the user wants to generate video using Sora, OpenAI video generation,
  or mentions ChatGPT for image generation. Also trigger when the user needs storyboard-style
  video prompts, cinematic text-to-video with audio, or wants to use OpenAI's platform for
  visual content creation. Covers Sora 2 video prompting, ChatGPT/GPT-4o image generation
  techniques, resolution/credit planning, and multi-shot workflows.
---

# Sora 2 Video & ChatGPT Image Generation — Prompting Guide

## Overview

This skill covers two OpenAI tools:

1. **Sora 2** — Video generation model (text-to-video, image-to-video)
2. **ChatGPT Image Generation (GPT-4o)** — Static image generation within ChatGPT

Both are cloud-based and require OpenAI subscriptions.

---

## Sora 2 — Video Generation

### Specifications

| Spec | Value |
|------|-------|
| Duration | 4-12s (sora-2), 10-25s (sora-2-pro) |
| Resolution | 720p (sora-2), 720p/1080p (sora-2-pro) |
| Audio | Native synchronized audio |
| Access | ChatGPT Plus ($20/mo) or Pro ($200/mo) |
| Credits | 1,000 (Plus) or 10,000 (Pro) per month |

### Credit Costs

| Resolution | Credits/Second | 10s Video Cost |
|-----------|---------------|----------------|
| 720p | 16 credits/s | 160 credits |
| 1080p | 40 credits/s | 400 credits |

**Strategy**: Draft with sora-2 at 720p (cheaper credits), finalize with sora-2-pro at 1080p.
A Plus subscriber gets ~25 ten-second 1080p videos per month, or ~62 at 720p.

> **SDK requirement**: Requires `openai>=1.51.0`. Use `client.videos.create()` or
> `client.videos.create_and_poll()` for generation.

### Known Limitations

Be aware of these before prompting — they affect what you should and shouldn't attempt:

- **Text rendering fails consistently** — never rely on readable text in video
- **Small object physics** — liquid pouring, cloth draping, intricate interactions are unreliable
- **Complex anatomy** — unusual poses or complex physical configurations struggle
- **No character memory** — each generation is independent, no persistence across prompts
- **No narrative sequencing** — can't define Scene 1 → Scene 2 in one prompt
- **Copyrighted characters blocked** — Disney, Marvel, etc. are rejected immediately

---

## Sora 2 Prompting: The Director Approach

Write prompts as if you're creating a storyboard. Think like a director giving instructions
to a cinematographer.

### The Core Four

Every Sora 2 prompt should specify:

1. **Style** — Overall visual aesthetic
2. **Subject** — What/who is in the video
3. **Action** — What happens (described in beats)
4. **Environment** — Setting and context

### Prompt Structure Template

```
[VISUAL DESCRIPTION]
[Shot type] of [subject with detailed appearance]. [Action described in sequence beats].
[Camera movement and lens]. [Environment with time/weather/atmosphere].
[Lighting and color palette]. [Visual style reference].

[AUDIO]
[Dialogue in quotes if any]. [Sound effects]. [Ambient audio]. [Music direction].
```

### Example — Product Video
```
[VISUAL DESCRIPTION]
Close-up product shot of a luxury watch against a dark marble background. Camera slowly
rotates around the watch, revealing the brushed steel case and sapphire dial. Professional
studio lighting with key light from upper left creates elegant highlights on the polished
surfaces. Warm, sophisticated color palette with deep blacks and golden accents. Shallow
depth of field keeps focus on watch details while background falls to smooth bokeh.

[AUDIO]
Subtle mechanical ticking, soft ambient music with warm synth pads.
```

### Example — TikTok Content
```
[VISUAL DESCRIPTION]
Vertical format, POV shot of hands opening a beautifully wrapped package on a clean white
desk. The wrapping paper peels back to reveal a glossy product box. Overhead camera angle
looking straight down. Bright, even lighting with soft shadows. Clean, modern aesthetic
with pastel accent colors.

[AUDIO]
Satisfying paper crinkling, box sliding open with a soft thud, excited gasp.
```

### Example — B-Roll
```
[VISUAL DESCRIPTION]
Wide shot of a modern café interior during morning rush. Baristas move behind the counter
in choreographed efficiency. Camera slowly pans left to right, capturing the full scene.
Natural window light mixes with warm pendant lamps overhead. Film-like quality with subtle
grain, slightly desaturated earth tones. Depth of field keeps foreground espresso machine
sharp while background patrons soften.

[AUDIO]
Espresso machine hissing, cups clinking, murmured conversations, ambient café bustle.
```

---

## Sora 2 Prompting Best Practices

### Be Specific About Motion
Instead of "the ball bounces," say "the ball drops from waist height, strikes the hardwood
floor, and rebounds to knee height with a slight spin."

### Resolution Affects Quality
Higher resolution doesn't just mean more pixels — the model uses the additional resolution
to render more detailed textures, more nuanced lighting transitions, and finer details.
Draft with sora-2 at 720p, finalize with sora-2-pro at 1080p.

### Balance Detail vs. Creativity
- **Detailed prompt** = maximum control, consistent output
- **Light prompt** = more creative freedom, surprising results
- Choose based on whether you need precision (product shots) or serendipity (artistic b-roll)

### Keep Prompts Under 200 Words
Overly long prompts dilute focus. For maximum clarity, aim for under 25 words for the
core subject description, with supporting details around it.

### One Dominant Action Per Clip
If you need walking + speaking + gesturing, generate them as separate clips and cut together.
Cramming too many actions into one generation reduces quality of all of them.

---

## Multi-Shot Video Workflow with Sora 2

Since Sora 2 has no memory between generations, maintaining visual consistency across
a multi-shot project requires discipline:

### The Consistency Checklist

For every prompt in a multi-shot project, copy these descriptors verbatim:

```
Character: [exact description — age, hair, clothing, accessories]
Environment: [exact location description]
Lighting: [exact setup — direction, color temp, quality]
Color grade: [exact palette description]
Lens: [exact focal length and aperture]
Style: [exact aesthetic reference]
```

### Shot-by-Shot Planning

For a 30-60 second piece, plan individual shots:

```
Shot 1 (5s, wide): Establishing — introduce setting and mood
Shot 2 (5s, medium): Subject introduction — first clear view
Shot 3 (3s, close-up): Detail — key feature or emotion
Shot 4 (5s, medium-wide): Action — main story beat
Shot 5 (3s, close-up): Reaction/detail — emotional or visual payoff
Shot 6 (5s, wide): Resolution — final scene or brand moment
```

Each shot is a separate Sora generation. Edit together in video software afterward.

### Image-to-Video for Consistency

For better character consistency:
1. Generate a reference image (via ChatGPT or other tools)
2. Use that image as the starting point for Sora's image-to-video mode
3. Write prompts that animate from that exact starting frame
4. Repeat with the same reference image for multiple shots

---

## ChatGPT Image Generation (GPT-4o)

### What It Is

GPT-4o within ChatGPT can generate static images. This is useful for:
- Creating reference images for video generation
- Product photography mockups
- Social media graphics
- Storyboard frames before video generation

### Prompting for ChatGPT Images

GPT-4o understands conversational prompts naturally. You can be direct:

```
Create a product photo of a matte black wireless earbud case sitting on a
white marble surface. Studio lighting, clean and minimal. Shot on Canon EOS R5
with 85mm lens, f/2.0. Slight shadow to the right. Premium, luxurious feel.
```

### Key Differences from Dedicated Image Models

- Excels at following complex, multi-layered instructions
- Good at text rendering within images (better than most video models)
- Conversational editing: "make the shadow softer" or "change background to grey"
- No explicit negative prompts — describe exclusions positively
- Limited style control compared to Stable Diffusion / Nano Banana 2

### Best Uses in the Content Pipeline

1. **Storyboard creation** — Generate frame-by-frame storyboards before video gen
2. **Reference images** — Create character/product references for Sora image-to-video
3. **Social graphics** — Thumbnails, cover images, promotional stills
4. **Concept validation** — Quick visual mockup before committing to video generation

---

## Content-Type Strategy

### Product Advertisements

**Sora 2 for video**:
- Focus on one hero action per clip (rotation, unboxing, feature demo)
- Use close-up + shallow depth of field for luxury feel
- Include satisfying audio (clicks, slides, premium sounds)
- Generate at 1080p for final output

**ChatGPT for supporting images**:
- Product hero shots for reference
- Lifestyle context images
- Clean product-on-white for e-commerce

### B-Roll

- Generate variety: 5+ different angles and compositions
- Use 720p drafts to test compositions, upgrade winners to 1080p
- Include natural ambient audio in every clip
- Pan and tracking shots work best for Sora b-roll
- Hold compositions for at least 3 seconds

### Short-Form Social

- Vertical format (9:16) for TikTok/Reels
- Hook in the first second — most dramatic visual up front
- 5-10 second clips chain well for 15-30 second final pieces
- Energetic camera work (quick pans, crash zooms in prompt description)
- Trendy audio: specify music style or trending sound direction

### Animated Shorts

- Specify animation style explicitly in prompt: "Pixar-style 3D", "2D anime", "watercolor"
- Sora handles stylized content well when style is clear
- Generate character reference images first via ChatGPT
- Use image-to-video with those references for each scene

---

## When to Choose Sora 2 vs Other Models

| Scenario | Sora 2 / Sora 2 Pro | LTX-2.3 | Veo 3.1 |
|----------|---------------------|---------|---------|
| Local, free generation | No | Yes | No |
| Native audio | Yes | Limited | Best |
| Max clip duration | 4-12s / 10-25s | 20s | 4-8s (extendable to ~148s) |
| Resolution | 720p / 720p+1080p | Up to 1440p native, 4K upscaled | 720p, 1080p, 4K |
| Character consistency | Poor (no memory) | Limited | Good (references) |
| Custom LoRAs | No | Yes | No |
| Quick iteration | Cloud queue | Fastest (local) | Cloud queue |
| Text in video | Fails | Fails | Fails |
| Photorealism | Excellent | Good | Excellent |
| Narrative storytelling | Very good | Good | Very good |
| Cost control | Credit-based | Free (local GPU) | Per-second |
