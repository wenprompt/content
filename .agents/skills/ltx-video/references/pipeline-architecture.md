# Pipeline Architecture — LTX-2.3 Two-Stage Distilled

Source of truth: `backend/clients/comfyui_client.py`
Reference workflows: `docs/video_ltx2_3_t2v.json`, `docs/video_ltx2_3_i2v.json`

---

## Node Graph (ASCII)

```
                    ┌─────────────────────────────────┐
                    │  CheckpointLoaderSimple (236)    │
                    │  ltx-2.3-22b-dev-fp8             │
                    └─┬──────────┬──────────┬──────────┘
                      │model     │vae       │(clip unused)
                      ▼          │          │
              ┌───────────────┐  │          │
              │LoraLoader(232)│  │  ┌───────────────────┐
              │distilled 0.5  │  │  │LTXAVTextEncoder   │
              └───┬───────────┘  │  │Loader (243)       │
                  │model         │  │gemma_3_12B_fp4    │
                  ▼              │  └──┬────────────────┘
          ┌───────────────┐     │     │clip
          │LoraLoader(234)│     │     ▼
          │camera (opt)   │     │  CLIPTextEncode (240/247)
          └───┬───────────┘     │  positive + negative
              │model            │     │
              ▼                 │     ▼
     ┌─ STAGE 1 ───────────────┤  LTXVConditioning (239)
     │                          │  frame_rate → pos/neg
     │  EmptyLTXVLatentVideo   │     │
     │  (228) w/2, h/2         │     │
     │        │                 │     │
     │  [I2V: LTXVImgToVideo  │     │
     │   Inplace (249)]        │     │
     │  [Guides: LTXVAddGuide  │     │
     │   chain → pos/neg/lat]  │     │
     │        │                 │     │
     │        ▼                 │     │
     │  LTXVEmptyLatentAudio   │     │
     │  (214) ──► ConcatAV(222)│     │
     │               │         │     │
     │               ▼         │     ▼
     │        SamplerCustomAdvanced (215)
     │        ├─ noise: RandomNoise (237) seed
     │        ├─ guider: CFGGuider (231) cfg=1
     │        ├─ sampler: euler_ancestral_cfg_pp (209)
     │        └─ sigmas: ManualSigmas (252)
     │           "1.0, 0.99375, 0.9875, 0.98125,
     │            0.975, 0.909375, 0.725, 0.421875, 0.0"
     │                    │
     └────────────────────┘
                          │
                          ▼
              LTXVSeparateAVLatent (217)
              ├─ video latent ──► LTXVLatentUpsampler (253) 2x
              │                   upscale_model: spatial-upscaler-x2
              └─ audio latent ──────────────────────────┐
                          │                              │
     ┌─ STAGE 2 ──────── │ ─────────────────────────────┤
     │                    ▼                              │
     │  [I2V: LTXVImgToVideoInplace (230) str=1.0]     │
     │                    │                              │
     │  LTXVCropGuides (212) ──► pos/neg                │
     │                    │                              │
     │  ConcatAV (229) ◄─┼──────────────────────────────┘
     │        │           │
     │        ▼           │
     │  SamplerCustomAdvanced (219)
     │  ├─ noise: RandomNoise (216) seed+1
     │  ├─ guider: CFGGuider (213) cfg=1
     │  ├─ sampler: euler_cfg_pp (246)
     │  └─ sigmas: ManualSigmas (211)
     │     "0.85, 0.7250, 0.4219, 0.0"
     │                    │
     └────────────────────┘
                          │
                          ▼
              LTXVSeparateAVLatent (218)
              ├─ video ──► VAEDecodeTiled (251)
              │            tile=768, overlap=64, temporal=4096
              └─ audio ──► LTXVAudioVAEDecode (220)
                          │
                          ▼
                   CreateVideo (242) → SaveVideo (75)
```

---

## Stage 1: Half-Resolution Generation

- **Resolution**: target_width/2 × target_height/2 (e.g., 640×360 for 1280×720)
- **Sampler**: `euler_ancestral_cfg_pp` — 1st-order solver with post-process CFG
- **Steps**: 8 (encoded in ManualSigmas as 9 values = 8 intervals)
- **CFG**: 1.0 (required for distilled LoRA)
- **Sigmas**: `1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0`

## Latent Upscale

- `LTXVLatentUpsampler` with `ltx-2.3-spatial-upscaler-x2-1.0` model
- Operates in latent space — doubles both spatial dimensions
- `LTXVSeparateAVLatent` splits audio/video before upscale, recombines after

## Stage 2: Full-Resolution Refinement

- **Resolution**: full target (e.g., 1280×720)
- **Sampler**: `euler_cfg_pp` — deterministic 1st-order (no ancestral noise injection)
- **Steps**: 4 (encoded in ManualSigmas as 4 values = 3 intervals)
- **CFG**: 1.0
- **Sigmas**: `0.85, 0.7250, 0.4219, 0.0`
- I2V re-injects reference image at strength 1.0 (locks to reference)

## I2V Path

When `image_filename` is provided:
1. `LoadImage` (269) → `ResizeImageMaskNode` (238) to target dims
2. `ResizeImagesByLongerEdge` (235) to 1536px max
3. `LTXVPreprocess` (248) with `img_compression` CRF (default 28)
4. `LTXVImgToVideoInplace` (249) at Stage 1 with configurable `i2v_strength` (default 0.7)
5. `LTXVImgToVideoInplace` (230) at Stage 2 with strength 1.0

## Guide Frames Path

When `guide_frames` is provided (mutually exclusive with I2V):
1. For each (filename, frame_idx, strength):
   - `LoadImage` → `ResizeImageMaskNode` to half-res
   - `LTXVAddGuide` — modifies positive, negative, AND latent conditioning
2. Guides chain sequentially: each takes the previous guide's outputs
3. Final guide outputs feed into Stage 1's `CFGGuider` and `ConcatAV`
4. `LTXVCropGuides` (212) adjusts conditioning for Stage 2 after upscale

## LoRA Chain

```
CheckpointLoaderSimple → LoraLoaderModelOnly (distilled, 0.5)
                         → LoraLoaderModelOnly (camera, optional)
                           → CFGGuider (both stages share the same model)
```

---

## What Our Code Does NOT Implement

| Feature | Description | How to Add |
|---------|-------------|------------|
| TextGenerateLTX2Prompt | Auto-rewrite prompts via Gemma | Add node before CLIPTextEncode |
| Temporal upscaler | 25fps → 50fps via `ltx-2.3-temporal-upscaler-x2-1.0` | Add after VAEDecode |
| x1.5 spatial upscaler | `ltx-2.3-spatial-upscaler-x1.5-1.0` — fewer flash artifacts | Swap upscaler model |
| NAG (Neg Anchor Guidance) | Separate video/audio negative strength | Swap CFGGuider → DualCFGGuider |
| Video extend | Continue from last frames of existing clip | Add LTXVExtendSampler path |
| Single-pass mode | No upscale — generate at target res directly | Skip Stage 2 + upscaler |
| IC-LoRA workflows | Structural control (canny/depth/pose) | Add LTXVInContextSampler path |
| GGUF models | Quantized for low-VRAM | Swap checkpoint loader |
| Dev pipeline | Non-distilled, 20+10 steps, CFG 3.0 | Remove distilled LoRA, change sigmas |
| ffn_chunks VRAM mgmt | Chunk size tuning for long videos | Add to model loader config |

---

## RuneXX vs Our Pipeline — Parameter Comparison

| Parameter | Our Code | RuneXX | Notes |
|-----------|----------|--------|-------|
| Distilled LoRA strength | **0.5** | **0.6** | RuneXX slightly more aggressive |
| Stage 1 sampler | `euler_ancestral_cfg_pp` | Same | Matches |
| Stage 2 sampler | `euler_cfg_pp` | Same | Matches |
| Stage 1 sigmas | `1.0...0.0` (8 steps) | Same | Matches |
| Stage 2 sigmas | `0.85...0.0` (3 steps) | Same | Matches |
| CFG | 1.0 | 1.0 | Matches |
| img_compression (CRF) | **28** | **18** | Lower = more motion in I2V |
| I2V strength (stage 1) | 0.7 | 0.7 | Matches |
| I2V strength (stage 2) | 1.0 | 1.0 | Matches |
| VAEDecode tile size | 768 | 768 | Matches |
| VAEDecode overlap | 64 | 64 | Matches |
