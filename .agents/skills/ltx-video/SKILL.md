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

LTX-2.3 uses a **Gemma 3 12B** text encoder with a **gated attention text connector** that is 4x larger
than LTX-2's. This means it follows complex instructions much better than previous versions.
Write prompts as flowing paragraphs — not lists, not tags. **Longer, more descriptive prompts
consistently outperform short ones.**

### The 6-Element Prompt Formula

Every effective LTX-2.3 prompt covers these elements in 4-8 sentences:

1. **Scene Anchor** — Where and when: location, time of day, atmosphere. Use cinematography terms matching your genre.
2. **Subject** — Who/what is in frame, with visual detail (age, hairstyle, clothing, texture, material). Express emotion through physical cues ("shoulders tensed, jaw clenched") NOT abstract labels ("she looks sad").
3. **Action** — What happens, using present-tense verbs ("walks", "pours", "rotates"). Write as a natural flowing sequence.
4. **Camera** — Shot type and movement using cinematography terms. Describe how subjects appear AFTER the movement. **Skip this element when using camera LoRAs** — the LoRA handles motion.
5. **Lighting & Mood** — Backlighting, rim light, color palette, warmth/coolness, surface textures.
6. **Audio** — Sound descriptions for synchronized audio. LTX-2.3 generates audio natively in a single pass. Describe ambience, SFX, dialogue (in quotes), music. Avoid overlapping speech between multiple voices.

### Prompt Template

```
[Scene anchor: location + time + atmosphere]. [Subject description with visual details].
[Action in present tense]. [Camera movement using cinematography terms — skip if using LoRA].
[Lighting setup and color palette]. [Audio/sound description].
```

### Example — Product Shot
```
A luxury watch rests on dark brushed marble in a minimalist studio. Warm amber side-lighting
catches the polished bezel, casting soft highlights across the sapphire crystal. The camera
performs a slow dolly-in, revealing the intricate dial texture and the brushed steel links of
the band. Shallow depth of field blurs the background to creamy bokeh. A subtle mechanical
tick punctuates the silence.
```

### Example — Product Shot WITH Dolly-In LoRA (no camera description)
```
A luxury watch rests on dark brushed marble in a minimalist studio. Warm amber side-lighting
catches the polished bezel, casting soft highlights across the sapphire crystal. The intricate
dial texture becomes visible — brushed indices, slim dauphine hands sweeping smoothly, the date
window magnified by a cyclops lens. Fine brushstroke patterns in the steel links emerge in sharp
detail. A subtle mechanical tick punctuates the silence.
```

### Example — TikTok Short Clip
```
A young barista in a cozy coffee shop pours steaming oat milk into a ceramic latte cup,
creating a rosetta pattern in the foam. Morning sunlight streams through the window,
backlighting the steam with golden warmth. The camera tracks the pour from a low angle,
then tilts up to catch her satisfied smile. Ambient cafe sounds mix with the gentle hiss
of the espresso machine.
```

### Example — B-Roll
```
Golden hour light floods a coastal boardwalk as joggers and cyclists move through frame.
The camera glides laterally on a parallel tracking shot, capturing the rhythm of movement
against the ocean backdrop. Lens flare dances across the frame as the sun dips toward the
horizon. Waves crash softly in the background, seagulls call overhead.
```

### Example — Speaking Character
```
A confident tech CEO in a navy blazer stands at a podium in a modern conference hall.
She looks directly into the camera and says "We're not just building another product."
She pauses, glancing down at her notes. "We're building the future of how people connect."
The audience erupts in applause. Overhead stage lighting casts a warm spotlight, while the
background displays a soft blue gradient. Microphone feedback hums faintly.
```

---

## What Makes a BAD Prompt

- **Emotional labels without visuals**: Say "shoulders tensed, jaw clenched" not "she looks sad"
- **Text/signage requests**: LTX-2.3 cannot render readable text consistently
- **Too many simultaneous actions**: More instructions = more things that won't render
- **Vague mood words alone**: "cozy minimalist" is weak — describe what makes it cozy
- **Lists or bullet points**: Use flowing paragraph form
- **Conflicting camera directions**: Don't say "static" and "dolly-in" in the same prompt
- **Short prompts for long videos**: A short prompt for an 8-10s video causes the model to rush. Match prompt detail to duration.
- **Camera movement words WITH camera LoRA**: Let the LoRA handle motion, describe the destination

---

## Negative Prompts

Comprehensive negative prompt for artifact prevention:

```
worst quality, low quality, blurry, pixelated, low resolution, grainy, distorted,
watermark, text, logo, signature, copyright, subtitle, caption, timestamp,
shaky, glitchy, deformed, disfigured, motion smear, motion artifacts,
fused fingers, bad anatomy, ugly, morphing, warping, flicker, jitter, stutter,
temporal artifacts, frame blending, extra hands, freeze frame, awkward transitions,
poor motion flow
```

---

## Key Parameters

### Dev Pipeline (Full Quality — No Distilled LoRA)

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| CFG (guidance_scale) | **3.0** | Official recommendation. Above 4.0 causes contrast burn, ringing, flicker |
| num_inference_steps | **20** (Stage 1), **10** (Stage 2) | Official dev pipeline values |
| num_frames | Divisible by 8 + 1 | e.g., 33, 41, 49, 57, 65, 73, 81, 121 |
| width/height | Divisible by 32 | Range: 128-2048 pixels |
| frame_rate | 24 or 25 | Use 48/50 only for short clips ≤10s |
| audio_guidance_scale | **7.0** | Separate parameter for audio quality |

### Distilled Pipeline (Fast — With Distilled LoRA)

| Parameter | Value | Notes |
|-----------|-------|-------|
| CFG | **1.0** | Must use 1.0 with distilled LoRA |
| Stage 1 steps | **8** | Base generation |
| Stage 2 steps | **4** | Refinement/upscale |
| Speed | ~3-4x faster | Slightly less creative/varied output |

### Resolution & Duration Planning

| Content Type | Aspect Ratio | Resolution | Duration | FPS |
|-------------|-------------|------------|----------|-----|
| TikTok/Reels | 9:16 | 1080x1920 | 5-10s | 24 |
| YouTube Short | 9:16 | 1080x1920 | 10-20s | 24 |
| Landscape B-roll | 16:9 | 1920x1080 | 5-20s | 24 |
| Landscape B-roll (1440p) | 16:9 | 2560x1440 | 5-15s | 24 |
| Product hero | 16:9 or 1:1 | 1080p | 5-10s | 24 |
| Instagram | 1:1 or 4:5 | 1080x1080 | 5-15s | 24 |

---

## Camera LoRAs — When to Use What

LTX-2.3 has official camera control LoRAs from Lightricks. The key principle: **let the LoRA
handle camera motion, and use your text prompt to describe what the camera reveals** (not the
movement itself). Apply camera LoRAs **only during base generation (Stage 1)** — the upsampler
preserves established motion.

For a detailed reference on all installed LoRAs (camera, IC-LoRA, distilled), compatibility
matrix, ComfyUI node setup, and content-type recommendations, read: `references/camera-loras.md`

### Quick Reference — Camera LoRAs (Actual Installed Filenames)

| Filename | Best For | Strength |
|----------|----------|----------|
| `ltx-2-19b-lora-camera-control-dolly-in` | Product reveals, dramatic emphasis | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-out` | Scene reveals, pulling back to context | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-left` | Lateral reveals, tracking | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-right` | Lateral reveals, tracking | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-jib-up` | Scale reveals, dramatic height | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-jib-down` | Descending reveals, approaching | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-static` | Product focus, no camera distraction | 0.7-1.0 |

### IC-LoRAs (Structural Control — see `references/camera-loras.md` for full details)

| Filename | Purpose | Strength |
|----------|---------|----------|
| `ltx-2-19b-ic-lora-canny-control` | Edge-guided generation (needs Canny preprocessing) | 1.0 |
| `ltx-2-19b-ic-lora-depth-control` | Depth-map guided generation (needs depth estimation) | 1.0 |
| `ltx-2-19b-ic-lora-detailer` | Detail enhancement (**Stage 2 only**) | 0.5-0.8 |
| `ltx-2-19b-ic-lora-pose-control` | Pose-guided generation (needs skeleton extraction) | 1.0 |
| `ltx-2-19b-ic-lora-union-control-ref0.5` | Combined depth+canny+pose in one LoRA | 1.0 |

**Critical**: Camera LoRAs and IC-LoRAs CANNOT be combined in the same generation pass.

### Distilled LoRAs (Speed)

| Filename | Purpose |
|----------|---------|
| `ltx-2-19b-distilled-lora-384` | Fast inference for 19b model (8 steps, CFG 1.0) |
| `ltx-2.3-22b-distilled-lora-384` | Fast inference for 22b model — **use this for LTX-2.3** |

### Content-Type Camera Recommendations

**Product Shots**: Dolly-In (hero reveal) → Static (detail hold) → Dolly-Out (context reveal)
**B-Roll**: Dolly-Left/Right (parallel tracking) or Jib-Up (environmental reveal)
**TikTok/Short-form**: Dolly-In (fast, aggressive) for scroll-stopping energy
**Animated Content**: Static or gentle Dolly-In to keep focus on the animation

### Prompting WITH LoRAs

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

**Minimum overlap**: 73 frames recommended (3 seconds at 25fps). Works with as few as 25 frames
but 73 is the official recommendation.

**ComfyUI node**: `LTXVExtendSampler` — generates continuation frames based on overlap.

**Gotcha**: Retaking/inpainting in the MIDDLE of a video has not yielded consistently good results.
Frame injection strength needs careful tuning — too high causes brightness flashes, too low causes
visible discontinuities.

### Last-Frame Image-to-Video Technique

For maximum control over transitions between different scenes:

1. Generate Clip A (e.g., 10 seconds)
2. Extract the last frame as a PNG
3. Use that PNG as the input image for Image-to-Video generation
4. Write a new prompt describing the next scene/action
5. The model generates Clip B that naturally flows from where A ended
6. Repeat as needed

### Shot Planning for Multi-Clip Content

For a 30-60 second piece:

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

### Key Nodes

| Node | Purpose |
|------|---------|
| `DualClipLoader` | Loads Gemma 3 12B text encoder (`gemma_3_12B_it_fp8_e4m3fn.safetensors`) |
| `LTXVScheduler` | LTX-specific scheduler for temporal stability |
| `LTXVBaseSampler` | Standard sampler for T2V/I2V with camera LoRAs |
| `LTXVInContextSampler` | IC-LoRA specific sampler (requires `guiding_latents` input) |
| `LTXVExtendSampler` | Video continuation/extension |
| `LTXVLatentUpsamplerModelLoader` | Loads the 2x spatial upscaler |
| `LTXVLatentUpsampler` | 2x latent-space upscale preserving motion continuity |
| `LoraLoaderModelOnly` | Loads camera LoRAs and distilled LoRA |
| `LTXICLoRALoaderModelOnly` | Loads IC-LoRAs, extracts downscale factor |
| `LTXAddVideoICLoRAGuide` | Adds downscaled reference latent for IC-LoRA |
| `TextGenerateLTX2Prompt` | Auto-converts simple descriptions to structured prompts |

### Typical Workflow Pipeline

```
Text Prompt → LTX Sampler (generate latent video)
→ Latent Upsampler (2x quality boost)
→ Video2Video Refinement (optional polish)
→ VAE Decode (latent → frames + audio)
→ Mux to MP4
```

### Example Workflow Files

| Workflow | Use Case |
|----------|----------|
| `LTX-2_T2V_Full_wLora.json` | Text-to-video with camera LoRA (dev pipeline) |
| `LTX-2_I2V_Full_wLora.json` | Image-to-video with camera LoRA |
| `LTX-2_T2V_Distilled_wLora.json` | Fast distilled + camera LoRA |
| `LTX-2_ICLoRA_All_Distilled.json` | IC-LoRA with distilled pipeline |

---

## Model Files Reference

| File | Purpose |
|------|---------|
| LTX-2.3 base model | Core 22B diffusion model (HuggingFace: Lightricks/LTX-2.3) |
| gemma_3_12B_it_fp8_e4m3fn.safetensors | Text encoder (FP8 quantized) |
| ltx-2.3-spatial-upscaler-x2-1.0.safetensors | Latent upscaler for quality |
| ltx-2.3-22b-distilled-lora-384.safetensors | Speed-optimized LoRA (8 steps) |
| 7 Camera LoRAs | Camera motion control (see table above) |
| 5 IC-LoRAs | Structural control (canny, depth, pose, detailer, union) |

---

## Prompt Generation Workflow

When generating prompts for the user, follow this process:

1. **Understand the content type** — product shot, b-roll, short clip, animation?
2. **Determine technical specs** — aspect ratio, duration, resolution
3. **Select camera approach** — which LoRA (if any) and why
4. **Choose pipeline** — dev (20 steps, CFG 3.0) or distilled (8 steps, CFG 1.0)
5. **Write the prompt** using the 6-element formula (skip camera element if using LoRA)
6. **Add negative prompt** for artifact prevention
7. **If multi-clip** — plan the shot sequence and transition strategy
8. **Output the complete ComfyUI configuration** — prompt, negative prompt, parameters, LoRA choice

Always explain your camera and prompting choices to the user so they can learn and iterate.
