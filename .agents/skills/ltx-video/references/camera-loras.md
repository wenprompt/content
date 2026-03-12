# LoRA Reference — LTX-2.3 & ComfyUI (Complete Guide)

## Table of Contents
1. Official Camera LoRAs — Usage, Prompting, Strength
2. IC-LoRAs — Structural Control (Canny, Depth, Pose, Detailer, Union)
3. Distilled LoRAs — Fast Inference
4. LoRA Stacking & Compatibility Matrix
5. Content-Type Camera Selection Guide
6. ComfyUI Node Reference
7. Troubleshooting

---

## 1. Official LTX-2 Camera LoRAs

No trigger words needed — controlled entirely via LoRA strength.
Apply **only during base generation (Stage 1)**, NOT during upsampling/refinement.
The upsampler preserves camera motion established in Stage 1.

**Critical prompting rule**: When using a camera LoRA, describe **what the camera reveals** as it moves — NOT the movement itself. The LoRA handles motion; your prompt describes the destination/result.

| Filename | Movement | Strength | Prompting Focus |
|----------|----------|----------|-----------------|
| `ltx-2-19b-lora-camera-control-static` | No movement (locked-off) | 0.7-1.0 | Load ALL interest into subject motion and lighting |
| `ltx-2-19b-lora-camera-control-dolly-in` | Pushes toward subject | 0.8-1.0 | Describe fine details that become visible as camera approaches — textures, materials, small features |
| `ltx-2-19b-lora-camera-control-dolly-out` | Pulls away from subject | 0.8-1.0 | Describe what exists behind/around the subject — the environment being revealed |
| `ltx-2-19b-lora-camera-control-dolly-left` | Translates left | 0.8-1.0 | Describe what comes into view on the left side — objects, background structures |
| `ltx-2-19b-lora-camera-control-dolly-right` | Translates right | 0.8-1.0 | Describe what comes into view on the right side |
| `ltx-2-19b-lora-camera-control-jib-up` | Rises vertically | 0.8-1.0 | Describe what is above — skyline, ceiling detail, overhead perspective |
| `ltx-2-19b-lora-camera-control-jib-down` | Descends vertically | 0.8-1.0 | Describe what is below — table surface, ground-level details |

### Example Prompts WITH Camera LoRAs

**Good (with Dolly-In LoRA):**
```
A ceramic teapot sits on a rustic wooden table. Behind it, steam curls upward
from the spout, catching warm afternoon light. The intricate hand-painted floral
pattern becomes visible as fine brushstroke details emerge. Shallow depth of field
softens the background into warm bokeh.
```

**Bad (redundant/conflicting with Dolly-In LoRA):**
```
The camera slowly dollies in toward a teapot on a table, moving forward,
pushing closer and closer to the teapot.
```

**Good (with Dolly-Out LoRA):**
```
A pair of wireless earbuds rests on a dark slate surface. Behind them, a modern
desk setup reveals itself — a curved ultrawide monitor glowing with ambient light,
a mechanical keyboard, and a potted monstera plant in the corner. Floor-to-ceiling
windows show a twilight cityscape.
```

**Good (with Jib-Up LoRA):**
```
A barista pours steaming oat milk into a ceramic latte cup on the counter. Above,
exposed brick walls rise to industrial ceiling beams strung with Edison bulbs.
Wooden shelving displays rows of single-origin coffee bags. Morning light streams
through skylights, casting warm geometric patterns.
```

**Good (with Static LoRA):**
```
A luxury watch rests on dark brushed marble in a minimalist studio. Warm amber
side-lighting catches the polished bezel. The second hand sweeps smoothly around
the dial. Subtle reflections dance across the sapphire crystal as light shifts.
A faint mechanical tick marks each second.
```

### ComfyUI Nodes for Camera LoRAs
- Load via `LoraLoaderModelOnly` or `LTXVQ8LoraModelLoader`
- Connect to the model pipeline before the sampler (`LTXVBaseSampler`)
- Example workflows: `LTX-2_T2V_Full_wLora.json`, `LTX-2_I2V_Full_wLora.json`

---

## 2. IC-LoRAs (In-Context LoRAs) — Structural Control

IC-LoRAs separate motion/structure from visual styling. They extract structure from reference videos/frames and apply them to new generations while allowing completely new visual styles through text prompts. Similar to ControlNet for images, but across video frames.

### Critical Constraints
- **Run only ONE IC-LoRA control type at a time** (Canny OR Depth OR Pose — not multiple)
- **Camera LoRAs CANNOT be combined with IC-LoRAs** in the same generation (different sampler requirements)
- **Keyframe index restrictions**: Conditioning frame indices CANNOT be multiples of 8+1 (avoid indices 1, 9, 17, 25...). Safe indices: 0, 2-8, 10-16, 18-24
- **Default frame index**: 0 (guidance starts from the beginning)
- **Default strength**: 1.0 — values below 1.0 can cause reference to "pop" or bleed through

### ComfyUI Node Chain (All IC-LoRAs)
1. `LTXICLoRALoaderModelOnly` — Loads IC-LoRA, extracts `latent_downscale_factor` from safetensors metadata
2. `LTXAddVideoICLoRAGuide` — Adds downscaled reference latent as guide at specific frame index
3. `LTXVInContextSampler` — Specialized sampler (replaces `LTXVBaseSampler` for IC-LoRA workflows)

Example workflow: `LTX-2_ICLoRA_All_Distilled.json`

### 2.1 Canny Control — `ltx-2-19b-ic-lora-canny-control`

**Purpose**: Structure-preserving generation guided by Canny edge maps. Maintains compositional structure while changing visual style.

**Preprocessing**: Run Canny edge detection on reference video frames.
**ComfyUI node**: `CannyEdgePreprocessor` from `comfyui_controlnet_aux` (by Fannovel16). Adjustable low/high thresholds.

**Use cases**:
- Keep compositional structure while changing everything else (animation, illustration styles)
- Style transfer while preserving edges and outlines
- Converting live action to stylized/animated look

### 2.2 Depth Control — `ltx-2-19b-ic-lora-depth-control`

**Purpose**: Geometry-aware generation guided by depth maps. Preserves spatial layout and depth relationships.

**Preprocessing**: Run depth estimation on reference frames.
**ComfyUI node**: Official workflow uses **Lotus Depth D v1.1**. Alternatives: `MiDaS-DepthMapPreprocessor` or DepthAnything from `comfyui_controlnet_aux`.

**Use cases**:
- Cinematic shots where spatial coherence is critical
- Tracking shots and establishing shots needing precise depth
- Maintaining parallax relationships across style changes

### 2.3 Pose Control — `ltx-2-19b-ic-lora-pose-control`

**Purpose**: Character motion/body-structure control guided by skeleton pose maps. Transfers human motion to different characters while preserving exact timing.

**Preprocessing**: Extract pose skeleton from reference video.
**ComfyUI node**: `DWPose Estimator` (recommended) or `OpenPose Pose` from `comfyui_controlnet_aux`. Both extract hand, body, and facial pose.

**Use cases**:
- Stylized character animation from live-action reference
- Motion retargeting to different characters
- Consistent character movement across visual style changes

### 2.4 Detailer — `ltx-2-19b-ic-lora-detailer`

**Purpose**: Enhances fine visual details, textures, edges WITHOUT altering composition or motion. Forces the model to resolve fine textures (skin, fabric) that often get smoothed out.

**Preprocessing**: None needed — uses the generated video itself as reference input.

**CRITICAL**: Add this LoRA in the **Second Pass (Refinement/Upscale stage)**, NOT in base generation.

**Strength**: **0.5-0.8** (NOT 1.0 — over-sharpening artifacts occur at high strength). Start at 0.5 and increase.

**Use cases**:
- Enhancing texture quality in upscaled video
- Resolving fabric, skin, and material details
- Hi-Res Fix / quality refinement pass

### 2.5 Union Control — `ltx-2-19b-ic-lora-union-control-ref0.5`

**Purpose**: A single unified LoRA combining multiple control conditions (depth AND canny AND pose) into one model. Replaces needing separate IC-LoRAs.

**What "ref0.5" means**: Reference resolution is 0.5x the output resolution (downscale factor of 2). Reduces memory usage while maintaining control quality. The ComfyUI nodes handle downscaling automatically via the extracted `latent_downscale_factor`.

**Advantage**: Use multiple control signals simultaneously without VRAM issues (single model instead of stacked LoRAs).

**Gotcha**: Do NOT manually resize reference — let the ComfyUI `LTXAddVideoICLoRAGuide` node handle downscaling using the extracted factor.

---

## 3. Distilled LoRAs — Fast Inference

| Filename | For Model | Steps | CFG | Notes |
|----------|-----------|-------|-----|-------|
| `ltx-2-19b-distilled-lora-384` | LTX-2 (19B) | **8** | **1.0** | For older 19B model |
| `ltx-2.3-22b-distilled-lora-384` | LTX-2.3 (22B) | **8** | **1.0** | **Use this one** for LTX-2.3 |

**Comparison with dev (non-distilled) pipeline:**

| Setting | Dev (no distilled) | Distilled |
|---------|-------------------|-----------|
| Stage 1 (base) steps | 20 | 8 |
| Stage 1 CFG | 3.0 | 1.0 |
| Stage 2 (refine) steps | 10 | 4 |
| Stage 2 CFG | 3.0 | 1.0 |
| Quality | Maximum | Slightly less varied/creative |
| Speed | Baseline | ~3-4x faster |

**ComfyUI setup**: Place in `ComfyUI/models/loras/`. Load via `LoraLoaderModelOnly`.

**Compatibility**: Can be combined with both camera LoRAs and IC-LoRAs. The IC-LoRA pipeline is specifically designed around the distilled setup.

Example workflows:
- `LTX-2_T2V_Distilled_wLora.json` — Distilled + camera LoRA
- `LTX-2_ICLoRA_All_Distilled.json` — Distilled + IC-LoRA

---

## 4. LoRA Stacking & Compatibility Matrix

| Combination | Allowed? | Notes |
|-------------|----------|-------|
| Camera + Camera | YES | Reduce strengths to 0.5-0.7 each; complementary directions only |
| Camera + Distilled | YES | Standard stacking |
| Camera + IC-LoRA | **NO** | Different sampler requirements (BaseSampler vs InContextSampler) |
| IC-LoRA + IC-LoRA | **NO** | Only one IC-LoRA control type at a time |
| IC-LoRA + Distilled | YES | IC-LoRA pipeline designed for distilled |
| Detailer + other IC-LoRA | SEPARATE PASSES | Detailer in Stage 2; control IC-LoRA in Stage 1 |
| Union Control | REPLACES multiple IC-LoRAs | Single LoRA handles depth+canny+pose together |

**LoRA overhead**: Each LoRA adds less than 5% compute overhead.

### Camera LoRA Stacking Examples

**Diagonal approach** (Dolly-Right 0.7 + Dolly-In 0.5):
Camera moves right while pushing forward simultaneously.

**Helicopter reveal** (360 Orbit 0.7 + Jib-Up 0.5):
Camera rises while rotating around product.

**Rules**:
1. Reduce each LoRA to 0.5-0.7 when stacking
2. Don't combine opposing directions (Dolly-In + Dolly-Out)
3. Test with shorter clips first
4. Complementary movements work best (lateral + vertical, lateral + zoom)

---

## 5. Content-Type Camera Selection Guide

### Product Shots / Advertisements

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Hero reveal | Dolly-In | Draws viewer toward product, builds importance |
| Detail showcase | Static | No camera distraction, pure focus on textures |
| 360 showcase | 360 Orbit (CivitAI) | Shows all angles of product |
| Unboxing feel | Jib-Down | Descending toward product creates anticipation |
| Scale context | Dolly-Out | Pulls back to show product in environment |
| Luxury feel | Slow Dolly-In + Static | Gentle approach then hold on beauty |

**30s product ad shot sequence:**
1. Dolly-Out: Wide establishing (5s)
2. Dolly-In: Medium approach (5s)
3. Static: Close-up hold (3s)
4. 360 Orbit: Product showcase (5s)
5. Dolly-In: Detail macro (3s)
6. Static: Brand moment (3s)

### B-Roll Footage

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Environment sweep | Dolly-Left/Right | Lateral exploration of space |
| Scale reveal | Jib-Up | Rising to show scope of location |
| Detail capture | Dolly-In | Approaching interesting textures/objects |
| Movement tracking | Dolly-Left/Right | Parallel tracking of moving subjects |
| Establishing shot | Dolly-Out + Jib-Up | Pulling back and rising for grand reveal |

Generate 10-15 second clips. Hold each composition for at least 3 seconds.

### TikTok / Short-Form Social Media

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Scroll-stopper open | Crash Zoom In (CivitAI) | Aggressive, attention-grabbing |
| Product reveal | Dolly-In (fast) | Quick approach builds excitement |
| Transition | Dolly-Left/Right (fast) | Energetic lateral movement |
| Drama beat | Jib-Up | Rising moment for emotional peaks |
| Trend format | 360 Orbit (fast) | Dynamic rotation for viral content |

**Format**: Always 9:16 (1080x1920). Duration: 5-15 seconds.

### Animated Short Clips

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Character intro | Static or gentle Dolly-In | Let animation be the star |
| Scene transition | Dolly-Left/Right | Smooth lateral transition |
| Reveal | Jib-Up | Rising to show animated environment |
| Action sequence | Static | Camera stability + fast animation = dynamic |
| Close-up detail | Dolly-In (slow) | Gentle approach to animated detail |

---

## 6. ComfyUI Node Reference

### LoRA Loading Nodes

| Node | Used For |
|------|----------|
| `LoraLoaderModelOnly` | Camera LoRAs, Distilled LoRA |
| `LTXVQ8LoraModelLoader` | Q8 quantized LoRA variants |
| `LTXICLoRALoaderModelOnly` | All IC-LoRAs (extracts downscale factor) |

### Sampler Nodes

| Node | Used For |
|------|----------|
| `LTXVBaseSampler` | Standard T2V/I2V with camera LoRAs |
| `LTXVInContextSampler` | IC-LoRA workflows (requires `guiding_latents` input) |
| `LTXVExtendSampler` | Video continuation/extension |

### IC-LoRA Preprocessing Nodes (from `comfyui_controlnet_aux`)

| Node | IC-LoRA | Notes |
|------|---------|-------|
| `CannyEdgePreprocessor` | Canny Control | Adjustable low/high thresholds |
| Lotus Depth D v1.1 / `MiDaS-DepthMapPreprocessor` | Depth Control | Lotus is official choice |
| `DWPose Estimator` | Pose Control | Recommended over OpenPose |

### Other Key Nodes

| Node | Purpose |
|------|---------|
| `LTXAddVideoICLoRAGuide` | Adds downscaled reference latent as guide |
| `LTXVScheduler` | LTX-specific noise scheduler |
| `LTXVLatentUpsampler` | 2x spatial upscale in latent space |
| `LTXVLatentUpsamplerModelLoader` | Loads the upscaler model |
| `DualClipLoader` | Loads Gemma 3 12B text encoder |

### Example Workflow Files

| Workflow | Use Case |
|----------|----------|
| `LTX-2_T2V_Full_wLora.json` | Text-to-video with camera LoRA |
| `LTX-2_I2V_Full_wLora.json` | Image-to-video with camera LoRA |
| `LTX-2_T2V_Distilled_wLora.json` | Fast distilled with camera LoRA |
| `LTX-2_I2V_Distilled_wLora.json` | Fast distilled I2V with camera LoRA |
| `LTX-2_ICLoRA_All_Distilled.json` | IC-LoRA with distilled pipeline |

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| Motion blur | Reduce camera LoRA strength by 0.1-0.2 |
| Movement too subtle | Increase strength toward 1.0 |
| Character distortion | Reduce strength to 0.7-0.8 |
| LoRA seems ignored | Ensure model compatibility; verify it loaded in ComfyUI |
| Two LoRAs fighting | Reduce both to 0.5-0.6, or use only one |
| IC-LoRA reference bleeding through | Keep strength at 1.0; below 1.0 causes bleed |
| Detailer over-sharpening | Reduce to 0.5; never use above 0.8 |
| VRAM issues with IC-LoRA | Only run one IC-LoRA type at a time; use Union Control instead |
| Camera LoRA + IC-LoRA not working | Cannot combine — use in separate passes or choose one |
| Brightness flash on extend | Reduce injected frame strength |

### CivitAI Camera LoRAs (Wan2.1/2.2 — check LTX-2.3 compatibility)

- **360 Orbit** — Full rotation. Strength 0.9-1.0. Great for product showcases.
- **Crash Zoom In** — Rapid dramatic zoom. Strength 0.7-0.9. TikTok scroll-stoppers.
- **Crash Zoom Out** — Rapid pull-back. Context reveals.
- **Crane Up/Down/Overhead** — Vertical crane movements.
- **Arc Shot** — Curved path (lateral + rotational). More cinematic than orbit.
- **Face-to-Feet Sweep** — Vertical scan. Strength 0.7-1.0. Fashion/apparel.
