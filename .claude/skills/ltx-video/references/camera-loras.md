# Camera LoRAs Reference — LTX-2.3 & ComfyUI

## Table of Contents
1. Official LTX-2 Camera LoRAs
2. CivitAI Camera Motion LoRAs (Wan2.1/2.2 compatible)
3. IC-LoRA (Motion Track Control)
4. Content-Type Camera Selection Guide
5. LoRA Strength & Trigger Word Reference
6. Combining LoRAs

---

## 1. Official LTX-2 Camera LoRAs (HuggingFace)

These are the official Lightricks LoRAs designed for the LTX-2 model family.
No trigger words needed — controlled entirely via LoRA strength.

| LoRA Name | Movement | HuggingFace Path | Strength |
|-----------|----------|-----------------|----------|
| Camera-Control-Static | No camera movement | Lightricks/LTX-2-19b-LoRA-Camera-Control-Static | 0.7-1.0 |
| Camera-Control-Dolly-In | Camera pushes toward subject | Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-In | 0.8-1.0 |
| Camera-Control-Dolly-Out | Camera pulls away from subject | Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Out | 0.8-1.0 |
| Camera-Control-Dolly-Left | Camera translates left | Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left | 0.8-1.0 |
| Camera-Control-Dolly-Right | Camera translates right | Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Right | 0.8-1.0 |
| Camera-Control-Jib-Up | Camera rises vertically | Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Up | 0.8-1.0 |
| Camera-Control-Jib-Down | Camera descends vertically | Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Down | 0.8-1.0 |

**Key principle**: LTX-2.3 supports up to 3 LoRAs simultaneously. Each adapter is only 1-128MB.

---

## 2. CivitAI Camera Motion LoRAs

These are community-made LoRAs, primarily trained for Wan2.1/2.2 but concepts translate.
If using with LTX-2.3, check model compatibility first.

### Orbit / Rotation
- **360 Orbit Camera Motion** — Full rotation around subject. Strength: 0.9-1.0.
  Great for product showcases where you need to show all angles.
- **Camera Rotation** — Controlled rotation. Strength: 0.8-1.0 (reduce if blur).

### Vertical Movements
- **Crane Up** — Dramatic upward reveal, showing scale. Good for architecture, tall products.
- **Crane Down** — Descending toward subject. Good for approaching a table-top scene.
- **Crane Overhead** — Bird's eye transition. Good for flat-lay product shots.
- **Face-to-Feet Sweep** — Vertical scan from top to bottom. Strength: 0.7-1.0.
  Specifically designed for fashion/apparel content.

### Zoom Movements
- **Crash Zoom In** — Rapid dramatic zoom. Strength: 0.7-0.9 (high strength overwhelms prompt).
  Perfect for TikTok scroll-stoppers and dramatic product reveals.
- **Crash Zoom Out** — Rapid pull-back reveal. Good for context reveals.

### Advanced
- **Arc Shot** — Curved path around subject. Combines lateral + rotational movement.
  More cinematic than simple orbit.
- **Push-In (Drone-style)** — Forward movement with aerial feel.

---

## 3. IC-LoRA — Motion Track Control

The IC-LoRA (In-Context LoRA) for LTX-2.3 provides a different approach:
instead of text-based camera control, you provide a **reference video** with
colored spline overlays indicating desired motion paths.

**When to use IC-LoRA instead of camera LoRAs:**
- When you need precise control over WHERE objects move in frame
- When text prompts aren't capturing the exact motion you want
- When you have a reference video showing the desired camera path

**Important**: Run only one IC-LoRA group at a time to avoid VRAM issues on 32GB cards.

---

## 4. Content-Type Camera Selection Guide

### Product Shots / Advertisements

The goal is to showcase the product with elegance and precision.

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Hero reveal | Dolly-In | Draws viewer toward product, builds importance |
| Detail showcase | Static | No camera distraction, pure focus on textures |
| 360 showcase | 360 Orbit (CivitAI) | Shows all angles of product |
| Unboxing feel | Jib-Down | Descending toward product creates anticipation |
| Scale context | Dolly-Out | Pulls back to show product in environment |
| Luxury feel | Slow Dolly-In + Static | Gentle approach then hold on beauty |

**Shot sequence for a 30s product ad:**
1. Dolly-Out: Wide establishing (5s) — shows the environment/lifestyle
2. Dolly-In: Medium approach (5s) — introduces the product
3. Static: Close-up hold (3s) — highlights key feature
4. 360 Orbit: Product showcase (5s) — shows all angles
5. Dolly-In: Detail macro (3s) — texture/quality proof
6. Static: Brand moment (3s) — clean product shot for CTA

### B-Roll Footage

B-roll needs variety and cinematic flow. Mix movements for a professional reel.

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Environment sweep | Dolly-Left/Right | Lateral exploration of space |
| Scale reveal | Jib-Up | Rising to show scope of location |
| Detail capture | Dolly-In | Approaching interesting textures/objects |
| Movement tracking | Dolly-Left/Right | Parallel tracking of moving subjects |
| Establishing shot | Dolly-Out + Jib-Up | Pulling back and rising for grand reveal |

**B-Roll best practice:** Generate 10-15 second clips. Longer gives more editing flexibility.
Hold each composition for at least 3 seconds before cutting.

### TikTok / Short-Form Social Media

Energy and attention-grabbing movement. First 0.5 seconds must hook the viewer.

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Scroll-stopper open | Crash Zoom In | Aggressive, attention-grabbing |
| Product reveal | Dolly-In (fast) | Quick approach builds excitement |
| Transition | Dolly-Left/Right (fast) | Energetic lateral movement |
| Drama beat | Jib-Up | Rising moment for emotional peaks |
| Trend format | 360 Orbit (fast) | Dynamic rotation for viral content |

**Format**: Always 9:16 (portrait). Resolution: 1080×1920.
**Duration**: 5-15 seconds per clip. Faster movements than traditional video.

### Animated Short Clips

Animation benefits from deliberate, controlled camera work that doesn't compete
with the animated elements.

| Shot Type | Recommended LoRA | Why |
|-----------|-----------------|-----|
| Character intro | Static or gentle Dolly-In | Let animation be the star |
| Scene transition | Dolly-Left/Right | Smooth lateral transition |
| Reveal | Jib-Up | Rising to show animated environment |
| Action sequence | Static (with fast subject) | Camera stability + fast animation = dynamic |
| Close-up detail | Dolly-In (slow) | Gentle approach to animated detail |

---

## 5. LoRA Strength & Trigger Word Reference

### Strength Guidelines

| Scenario | Strength Range | Notes |
|----------|---------------|-------|
| Strong, definitive movement | 0.9-1.0 | Full camera motion effect |
| Subtle, gentle movement | 0.7-0.8 | Lighter touch, less aggressive |
| Combined with other LoRAs | 0.6-0.8 each | Reduce when stacking to prevent conflicts |
| Competing with prompt | Start 1.0, reduce | If LoRA fights your text, reduce strength |

### Troubleshooting LoRA Issues

| Problem | Solution |
|---------|----------|
| Motion blur | Reduce strength by 0.1-0.2 |
| Movement too subtle | Increase strength toward 1.0 |
| Character distortion | Reduce strength to 0.7-0.8 |
| LoRA seems ignored | Ensure model compatibility; check it loaded |
| Two LoRAs fighting | Reduce both to 0.5-0.6, or use only one |

### Trigger Words

Most LTX-2 camera LoRAs do NOT require trigger words — they're purely strength-based.
The motion is encoded in the LoRA weights, activated by the strength parameter.

**Exception**: If using CivitAI community LoRAs, always check the model card for trigger words.
Some community LoRAs use phrases like "camera orbits", "crash zoom", etc.

---

## 6. Combining Multiple LoRAs

LTX-2.3 supports up to 3 simultaneous LoRAs. Use this for complex movements:

**Example combination: Product orbit with jib**
- 360 Orbit LoRA at 0.7
- Jib-Up LoRA at 0.5
- Result: Camera rises while rotating around product (helicopter-like)

**Example combination: Tracking with zoom**
- Dolly-Right at 0.7
- Dolly-In at 0.5
- Result: Camera moves right while pushing forward (diagonal approach)

**Rules for combining:**
1. Reduce each LoRA strength when stacking (0.5-0.7 each)
2. Don't combine opposing directions (Dolly-In + Dolly-Out)
3. Test with shorter clips first to verify the combination works
4. Complementary movements work best (lateral + vertical, or lateral + zoom)
