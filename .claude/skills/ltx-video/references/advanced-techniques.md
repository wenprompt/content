# Advanced Techniques — LTX-2.3

Community knowledge, RuneXX workflow techniques, and features not yet in our backend.

---

## KJnodes Bypass Guide

RuneXX workflows use KJnodes for convenience. Every one has a standard ComfyUI replacement:

| KJnode | Standard Replacement | Notes |
|--------|---------------------|-------|
| `SimpleCalculatorKJ` | Pre-calculate in code, use `PrimitiveInt` | Math convenience only |
| `INTConstant` | `PrimitiveInt` (built-in) | Direct drop-in |
| `ImageResizeKJv2` | `ImageScale` + `crop: center` | Standard node |
| `LTXVImgToVideoInplaceKJ` | `LTXVAddGuide` chain (frame 0 + frame -1) | **Our code already does this** via `guide_frames` |
| `ImageConcatMulti` | Chain `ImageConcat` nodes | Preview-only, not pipeline-critical |
| `LTXVChunkFeedForward` | Skip (VRAM opt) or use GGUF models | Not needed on 32GB VRAM |
| `LTX2_NAG` | `DualCFGGuider` + step-gating | See NAG section below |
| `VAELoaderKJ` | Standard `VAELoader` | Direct drop-in |
| `ImageBatchExtendWithOverlap` | Custom blend: filmic crossfade, gamma 2.2, 25-frame overlap | See V2V Extend section |
| `LTX2SamplingPreviewOverride` | Skip | Preview convenience only |
| `GetImageRangeFromBatch` | Tensor slicing in code | Simple replacement |

---

## Negative Anchor Guidance (NAG) — Full Implementation

NAG separates negative guidance for video and audio channels. The `LTX2_NAG` KJnode is
just a wrapper — here's how to build it from scratch:

### The Problem
Standard `CFGGuider` applies one CFG scale to the entire output. Audio and video have
different optimal negative strengths — video needs gentle correction (over-correction
causes artifacts), audio needs aggressive correction (cleans up noise/artifacts).

### Implementation with Standard Nodes

1. **Replace `CFGGuider` with `DualCFGGuider`**
   - `cfg1` (video negative strength): **0.25** — very light
   - `cfg2` (audio negative strength): **2.5** — aggressive
   - Both positive and negative conditionings connect as usual

2. **Step gating** (start NAG at step 11, not from beginning):
   - Use `SamplerCustomAdvanced` with a `SigmaSchedule` that splits at step 11
   - First 10 steps: standard `CFGGuider` (cfg=1.0)
   - Steps 11+: `DualCFGGuider` with split strengths
   - Alternative: use `ModelSamplingDiscreteScheduler` to adjust at specific steps

3. **In our codebase**: swap `CFGGuider` (nodes 231/213) for `DualCFGGuider`, add a
   step-conditional switch. Requires adding `nag_video_strength`, `nag_audio_strength`,
   and `nag_start_step` parameters to `_build_workflow()`.

### When NAG Helps
- Talking head / dialogue content — clearer speech, less audio artifacts
- Music videos — cleaner audio without washing out visuals
- Any generation where audio quality is the priority

### RuneXX NAG Values
- Video negative strength: **0.25**
- Audio negative strength: **2.5**
- Start step: **11**

---

## V2V Extend Any Video — Full Technique

Extend any existing video (not just LTX-generated) with seamless blending:

### Workflow
1. **Load source video** → extract frames
2. **Take final N frames** as overlap region (N = 25 frames recommended)
3. **Generate extension** conditioned on the overlap frames (use `LTXVExtendSampler` or
   guide_frames with the last frame)
4. **Blend overlap region** using filmic crossfade:
   - Apply **gamma 2.2** to linearize both sequences
   - Cross-fade over 25 frames with linear alpha ramp
   - Apply **inverse gamma (1/2.2)** to return to sRGB
   - This produces perceptually uniform blending (no brightness dip in the middle)
5. **Concatenate**: source (minus overlap) + blended region + extension

### KJnodes Bypass
`ImageBatchExtendWithOverlap` does steps 2-5 automatically. Without it:
- Chain `ImageConcat` nodes for the concatenation
- Implement gamma-correct crossfade in a custom node or preprocessing script
- Or use ffmpeg: `ffmpeg -i a.mp4 -i b.mp4 -filter_complex "xfade=transition=fade:duration=1"`
  (simpler but not gamma-correct)

### Iteration
Run repeatedly to build arbitrarily long videos. Change the prompt between iterations
to steer the narrative in new directions.

---

## Single-Pass Pipeline

Skip the two-stage upscale for faster iteration:

- Generate at **full target resolution** in one pass
- Same sampler/sigma config as Stage 1
- No `LTXVLatentUpsampler`, no Stage 2 refinement
- **~2-3x faster**, significantly less VRAM
- Quality trade-off: softer details, no refinement pass
- Best for: prompt testing, drafts, social media where 720p is acceptable

### Implementation
Remove nodes 253, 212, 229, 213, 246, 211, 216, 219, 218 from the workflow. Route Stage 1
output directly to `VAEDecodeTiled`. Change `EmptyLTXVLatentVideo` to full resolution.

---

## TextGenerateLTX2Prompt

**NOT a KJnode** — this is from the official `ComfyUI-LTXVideo` extension.

- Auto-rewrites simple descriptions into structured LTX-2.3 prompts via Gemma-3-12B
- "Tweaking wording yields bigger gains than sampler tweaks" (community consensus)
- Controls: `disable_TextGenerate` (bool), `enhancer_seed` for variations
- For manually crafted prompts using the 6-element formula, bypass it
- Alternative: **LTX2EasyPrompt-LD** — local uncensored LLM, zero internet dependency

---

## Temporal Upscaler (x2)

`ltx-2.3-temporal-upscaler-x2-1.0` — converts 25fps to 50fps.

- Improves smoothness for teeth, hair, fabric edges
- Apply **after** spatial upscaling in the pipeline
- For slow-motion: generate at 25fps → temporal upscale to 50fps → conform to 25fps = 2x slow-mo
- Optional — 24-25fps is more cinematic for most content

---

## x1.5 Spatial Upscaler

`ltx-2.3-spatial-upscaler-x1.5-1.0` — alternative to the x2 upscaler.

- Community reports **fewer bright flash artifacts** than x2
- Use when x2 upscaler causes flashing or brightness spikes
- Lower VRAM requirements
- Good middle ground: 720p → 1080p instead of 540p → 1080p

---

## img_compression (CRF) Tuning

Controls how much MPEG compression is applied to reference images in I2V.

| CRF Value | Effect | Use Case |
|-----------|--------|----------|
| 15-20 | Heavy compression, maximum motion | Dynamic action, RuneXX default (18) |
| 25-30 | Moderate compression, balanced | General I2V (our default: 28) |
| 30-40 | Light compression, stable/static | Identity preservation, slow pans |

**Why it works**: LTX was trained on video frames with MPEG artifacts. Clean images confuse
the model into treating them as stills. Adding compression artifacts signals "this came from
video, generate video-like motion."

---

## ffn_chunks — VRAM Management

For longer video durations, increase `ffn_chunks` to trade speed for VRAM:

| Duration | Recommended ffn_chunks |
|----------|----------------------|
| 10s | 1-2 |
| 15s | 2-4 |
| 20s | 4-6 |
| 25s | 8-10 |
| 33s | 12-16 |

Set via `LTXVChunkFeedForward` (KJnodes) or model config patching.

---

## FPS Selection Guide

| FPS | Best For |
|-----|----------|
| 48-50 | Action content, fast motion, sports |
| 24-25 | Standard cinematic, most content |
| 15 | Static scenes, timelapse feel, VRAM saving |

For true slow-motion: generate at 48fps, conform to 24fps in post.

---

## Motion Tracking IC-LoRA (NEW)

`ltx-2.3-22b-ic-lora-motion-track-control-ref0.5`

- **LTX-2.3 specific** — uses the 22B model naming
- Motion tracking control — guide video generation by tracking specific elements
- Same IC-LoRA workflow: `LTXICLoRALoaderModelOnly` → `LTXAddVideoICLoRAGuide` → `LTXVInContextSampler`
- `ref0.5` = reference at 0.5x output resolution (same as union control)
- **Cannot combine with camera LoRAs** (different sampler requirement)

---

## Gemma Abliterated LoRA

`gemma-3-12b-it-abliterated_lora_rank64_bf16`

- Uncensored text encoder LoRA for the Gemma 3 12B text encoder
- Removes content refusal behavior from text encoding
- Load via `LoraLoaderModelOnly` on the text encoder model
- Use for unrestricted prompt content that Gemma would otherwise refuse to encode

---

## Long Video Loop Technique

For videos longer than the 20s single-generation limit:

1. Generate initial clip (up to 20s)
2. Extract last frame(s) as conditioning for next clip
3. Use `LTXVExtendSampler` or guide_frames to continue
4. Blend clips using 25-frame filmic crossfade (gamma 2.2)
5. Repeat with prompt steering for narrative progression

**Audio sync**: Each clip generates its own audio. At blend boundaries, crossfade audio
separately from video for smooth transitions.

RuneXX workflows use Set/Get node state management to persist latents between iterations
within a single ComfyUI execution graph.
