# LTX-2.3 Reference Workflow JSONs

Exported from real ComfyUI runs — every JSON here has been validated against a running instance.

All workflows use: 768x512, 121 frames (~5s at 24fps), seed 42, distilled two-stage pipeline (unless noted).

## T2V (Text-to-Video)

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `t2v_basic.json` | T2V basic | No image, no LoRA | PASS |

## I2V (Image-to-Video)

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `i2v_basic.json` | I2V basic | coca.png, CRF 28 | PASS |
| `i2v_low_crf.json` | I2V low CRF (RuneXX) | coca.png, CRF 18 (more motion) | PASS |
| `i2v_dolly_in.json` | I2V + dolly-in | coca.png + dolly-in LoRA 0.9 | PASS |
| `i2v_static.json` | I2V + static | coca.png + static LoRA 0.8 | PASS |
| `i2v_jib_up.json` | I2V + jib-up | coca.png + jib-up LoRA 0.9 | PASS |

## T2V + Camera LoRAs (all 7 directions)

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `t2v_dolly_in.json` | dolly-in | Push toward subject, 0.9 | PASS |
| `t2v_dolly_out.json` | dolly-out | Pull away from subject, 0.9 | PASS |
| `t2v_dolly_left.json` | dolly-left | Translate left, 0.9 | PASS |
| `t2v_dolly_right.json` | dolly-right | Translate right, 0.9 | PASS |
| `t2v_jib_up.json` | jib-up | Rise vertically, 0.9 | PASS |
| `t2v_jib_down.json` | jib-down | Descend vertically, 0.9 | PASS |
| `t2v_static.json` | static | Locked-off, no movement, 0.8 | PASS |
| `t2v_lora_low_strength.json` | dolly-in low | dolly-in at 0.6 (LoRA chain test) | PASS |

## Guide Frames (FL2V / FML2V)

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `fl2v_first_last.json` | First + last frame | coca.png frame 0, coca2.png frame -1 | PASS |
| `fml2v_three_guides.json` | First + mid + last | 3 guides, mid at 0.5 strength | PASS |
| `fl2v_dolly_in.json` | Guides + camera LoRA | FL2V + dolly-in 0.9 | PASS |

## NAG (Negative Anchor Guidance)

Uses `DualCFGGuider` instead of `CFGGuider` for split video/audio negative strengths.

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `t2v_nag.json` | T2V + NAG | video_cfg=0.25, audio_cfg=2.5 | PASS |
| `i2v_nag.json` | I2V + NAG | coca.png + NAG split guidance | PASS |

## Single-Pass (skip stage 2)

Generates at full resolution in one pass — no latent upscale, no refinement. ~2x faster.

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `t2v_single_pass.json` | T2V single-pass | 8 steps only (no stage 2) | PASS |
| `i2v_single_pass.json` | I2V single-pass | coca.png, 8 steps only | PASS |

## IA2V (Image+Audio to Video)

Encodes real audio via `LTXVAudioVAEEncode` + `SetLatentNoiseMask` instead of empty audio latent.

| File | Variant | Key Params | Status |
|------|---------|------------|--------|
| `ia2v_basic.json` | IA2V | coca.png + test_audio.wav | PASS |
| `t2v_with_audio.json` | T2V + audio | test_audio.wav (no image) | PASS |

## Regenerating

```bash
uv run pytest tests/test_workflow_variants.py -v -s
```
