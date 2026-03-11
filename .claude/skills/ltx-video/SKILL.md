---
name: ltx-video
description: |
  Expert prompting skill for LTX-2.3 (LTX-Video 2.3 by Lightricks) video generation in ComfyUI.
  Use this skill whenever the user wants to generate video using LTX, LTX-2, LTX-2.3, or mentions
  ComfyUI video generation, text-to-video, image-to-video workflows, camera LoRAs for video,
  video extend/concatenation, or creating short-form video content with AI. Also trigger when user
  mentions product videos, b-roll, TikTok clips, animated shorts, or any video generation that
  could use a local ComfyUI pipeline. Even if the user just says "make me a video" or "generate
  a clip", consider this skill. Covers prompting best practices, camera LoRA selection, resolution/
  duration planning, negative prompts, and multi-clip concatenation strategies.
---

# LTX-2.3 Video Generation — Prompting & Workflow Guide

## What is LTX-2.3?

LTX-2.3 is a 22-billion parameter Diffusion Transformer (DiT) video generation model by Lightricks,
released March 2026. It runs locally via ComfyUI and is open-source (Apache 2.0). Your RTX 5090
with 32GB VRAM meets the minimum requirement.

**Capabilities**: text-to-video, image-to-video, audio-to-video, video extend, retake (partial re-gen).
**Max duration**: 20 seconds per clip (extendable via video extend).
**Resolutions**: 480p to 1440p native, 4K via latent upscaler.
**Frame rates**: 24, 25, 48, or 50 FPS (videos >10s limited to 24-25 FPS at 1080p).

---

## Prompting Philosophy

LTX-2.3 uses a Gemma 3 12B text encoder, which means it understands natural language well.
Write prompts as flowing paragraphs — not lists, not tags. Think of yourself as a cinematographer
describing a scene to a camera operator.

### The 6-Element Prompt Formula

Every effective LTX-2.3 prompt covers these elements in 4-8 sentences:

1. **Scene Anchor** — Where and when: location, time of day, atmosphere
2. **Subject** — Who/what is in frame, with visual detail (clothing, texture, material)
3. **Action** — What happens, using present-tense verbs ("walks", "pours", "rotates")
4. **Camera** — Shot type and movement using cinematography terms
5. **Lighting & Mood** — Backlighting, rim light, color palette, warmth/coolness
6. **Audio** — Sound descriptions for synchronized audio (LTX-2.3 generates audio natively in a single pass; include audio descriptions in prompts for best results)

### Prompt Template

```
[Scene anchor: location + time + atmosphere]. [Subject description with visual details].
[Action in present tense]. [Camera movement using cinematography terms]. [Lighting setup
and color palette]. [Audio/sound if desired].
```

### Example — Product Shot
```
A luxury watch rests on dark brushed marble in a minimalist studio. Warm amber side-lighting
catches the polished bezel, casting soft highlights across the sapphire crystal. The camera
performs a slow dolly-in, revealing the intricate dial texture and the brushed steel links of
the band. Shallow depth of field blurs the background to creamy bokeh. A subtle mechanical
tick punctuates the silence.
```

### Example — TikTok Short Clip
```
A young barista in a cozy coffee shop pours steaming oat milk into a ceramic latte cup,
creating a rosetta pattern in the foam. Morning sunlight streams through the window,
backlighting the steam with golden warmth. The camera tracks the pour from a low angle,
then tilts up to catch her satisfied smile. Ambient café sounds mix with the gentle hiss
of the espresso machine.
```

### Example — B-Roll
```
Golden hour light floods a coastal boardwalk as joggers and cyclists move through frame.
The camera glides laterally on a parallel tracking shot, capturing the rhythm of movement
against the ocean backdrop. Lens flare dances across the frame as the sun dips toward the
horizon. Waves crash softly in the background, seagulls call overhead.
```

---

## What Makes a BAD Prompt

Avoid these patterns — they confuse the model or produce poor results:

- **Emotional labels without visuals**: Say "shoulders tensed, jaw clenched" not "she looks sad"
- **Text/signage requests**: LTX-2.3 cannot render readable text consistently
- **Too many simultaneous actions**: More instructions = more things that won't render
- **Vague mood words alone**: "cozy minimalist" is weak — describe what makes it cozy
- **Lists or bullet points**: Use flowing paragraph form
- **Conflicting camera directions**: Don't say "static" and "dolly-in" in the same prompt

---

## Negative Prompts

Use these to prevent common artifacts:

```
subtitle, caption, text, watermark, logo, timestamp, extra hands, blurry,
out of focus, distorted proportions, artifacts, glitch, freeze frame,
awkward transitions, poor motion flow, low quality, pixelated
```

---

## Key Parameters

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| guidance_scale (CFG) | 3.0–3.5 | Default 4.0; above 4.0 causes contrast burn, ringing, flicker |
| num_inference_steps | 40 | Standard quality-speed balance |
| num_frames | Divisible by 8 + 1 | e.g., 33, 41, 49, 57, 65, 73, 81, 121 |
| width/height | Divisible by 32 | Match target aspect ratio |
| frame_rate | 24 or 25 | Use 48/50 only for short clips ≤10s |

### Resolution & Duration Planning

| Content Type | Aspect Ratio | Resolution | Duration | FPS |
|-------------|-------------|------------|----------|-----|
| TikTok/Reels | 9:16 | 1080×1920 | 5-10s | 24 |
| YouTube Short | 9:16 | 1080×1920 | 10-20s | 24 |
| Landscape B-roll | 16:9 | 1920×1080 | 5-20s | 24 |
| Landscape B-roll (1440p) | 16:9 | 2560×1440 | 5-15s | 24 |
| Product hero | 16:9 or 1:1 | 1080p | 5-10s | 24 |
| Instagram | 1:1 or 4:5 | 1080×1080 | 5-15s | 24 |

---

## Camera LoRAs — When to Use What

LTX-2.3 has official camera control LoRAs from Lightricks. The key principle: **let the LoRA
handle camera motion, and use your text prompt to describe what the camera reveals** (not the
movement itself).

For a detailed reference on all available camera LoRAs, trigger words, weights, and content-type
recommendations, read: `references/camera-loras.md`

### Quick Reference

| LoRA | Best For | Strength |
|------|----------|----------|
| Dolly-In | Product reveals, dramatic emphasis | 0.8-1.0 |
| Dolly-Out | Scene reveals, pulling back to context | 0.8-1.0 |
| Dolly-Left/Right | Lateral reveals, tracking | 0.8-1.0 |
| Jib-Up | Scale reveals, dramatic height | 0.8-1.0 |
| Jib-Down | Descending reveals, approaching | 0.8-1.0 |
| Static | Product focus, no camera distraction | 0.7-1.0 |

### Content-Type Camera Recommendations

**Product Shots**: Dolly-In (hero reveal) → Static (detail hold) → Dolly-Out (context reveal)
**B-Roll**: Dolly-Left/Right (parallel tracking) or Jib-Up (environmental reveal)
**TikTok/Short-form**: Dolly-In (fast, aggressive) for scroll-stopping energy
**Animated Content**: Static or gentle Dolly-In to keep focus on the animation

### Important: Prompting WITH LoRAs

When using a camera LoRA, your prompt should describe **what the camera will reveal** as it moves,
not the movement itself. The LoRA handles the motion.

**Good** (with Dolly-In LoRA):
```
A ceramic teapot sits on a rustic wooden table. Behind it, steam curls upward
from the spout, catching warm afternoon light. The intricate hand-painted floral
pattern becomes visible as fine brushstroke details emerge.
```

**Bad** (redundant/conflicting with Dolly-In LoRA):
```
The camera slowly dollies in toward a teapot on a table, moving forward,
pushing closer and closer to the teapot.
```

---

## Multi-Clip Strategy: Going Beyond 20 Seconds

Since LTX-2.3 maxes at 20 seconds per clip, longer content requires the **Video Extend** feature.

### How Video Extend Works

1. Generate your first clip (the "base" clip)
2. The extend feature analyzes the last frames — motion patterns, lighting, composition, style
3. It generates genuinely new frames that continue the visual narrative
4. You can extend by 1-20 seconds each time
5. Optional: provide a new prompt describing how the scene continues

### ComfyUI Workflow for Extend

1. Generate first clip → decode to frames
2. Feed last frame + continuation prompt to LTX sampler
3. Use the latent upsampler between stages for quality
4. Mux audio separately or regenerate synchronized audio
5. Concatenate clips in output

### Last-Frame Image-to-Video Technique

For maximum control over transitions:

1. Generate Clip A (e.g., 10 seconds)
2. Extract the last frame as a PNG
3. Use that PNG as the input image for Image-to-Video generation
4. Write a new prompt describing the next scene/action
5. The model generates Clip B that naturally flows from where A ended
6. Repeat as needed

### Shot Planning for Multi-Clip Content

For a 30-60 second piece, plan your shots:

```
Shot 1 (5-10s): Wide establishing shot — sets the scene
Shot 2 (5-10s): Medium shot — introduces subject/product
Shot 3 (3-5s): Close-up — highlights key detail
Shot 4 (5-10s): Action shot — demonstrates product/tells story
Shot 5 (3-5s): Final shot — call to action or brand moment
```

Each shot gets its own prompt. Use the last-frame technique between shots for smooth transitions.

---

## ComfyUI Node Setup

Key nodes for LTX-2.3 workflows:

- **TextGenerateLTX2Prompt** — Converts simple descriptions into structured prompts. Useful for
  quick generation, but hand-crafted prompts give more control.
- **LTXVScheduler** — LTX-specific scheduler for temporal stability
- **LTXVLatentUpsamplerModelLoader** — Loads the 2x spatial upscaler
- **LTXVLatentUpsampler** — 2x latent-space upscale preserving motion continuity
- **Standard LoRA Loader** — For camera control LoRAs

### Typical Workflow Pipeline

```
Text Prompt → LTX Sampler (generate latent video)
→ Latent Upsampler (2x quality boost)
→ Video2Video Refinement (optional polish)
→ VAE Decode (latent → frames + audio)
→ Mux to MP4
```

---

## Model Files Reference

| File | Purpose |
|------|---------|
| LTX-2.3 base model | Core diffusion model (HuggingFace: Lightricks/LTX-2.3) |
| ltx-2.3-spatial-upscaler-x2-1.0.safetensors | Latent upscaler for quality |
| ltx-2.3-22b-distilled-lora-384.safetensors | Speed-optimized LoRA |
| Camera LoRAs (Dolly, Jib, Static) | Camera motion control |

---

## Prompt Generation Workflow

When generating prompts for the user, follow this process:

1. **Understand the content type** — product shot, b-roll, short clip, animation?
2. **Determine technical specs** — aspect ratio, duration, resolution
3. **Select camera approach** — which LoRA (if any) and why
4. **Write the prompt** using the 6-element formula
5. **Add negative prompt** for artifact prevention
6. **If multi-clip** — plan the shot sequence and transition strategy
7. **Output the complete ComfyUI configuration** — prompt, negative prompt, parameters, LoRA choice

Always explain your camera and prompting choices to the user so they can learn and iterate.
