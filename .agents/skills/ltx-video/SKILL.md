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
released March 2026. It runs locally via ComfyUI and is open-source (Apache 2.0). RTX 5090
with 32GB VRAM meets the minimum requirement.

**Capabilities**: text-to-video, image-to-video, audio-to-video, video extend, retake (partial re-gen).
**Max duration**: 20 seconds per clip (extendable via video extend).
**Resolutions**: 480p to 1440p native, 4K via latent upscaler.
**Frame rates**: 24, 25, 48, or 50 FPS (videos >10s limited to 24-25 FPS at 1080p).

### Strengths (Use LTX-2.3 For)

- Product shots, hero reveals, turntable/360 spins
- B-roll footage (landscapes, cityscapes, nature, atmospheric)
- Talking heads with native audio lip sync
- Cinematic slow motion (steam, fabric, fog, smoke, water)
- Camera LoRA-driven content (dolly, jib, tracking shots)
- Food/cooking content (pours, steam, sizzling, plating)
- Fashion/lifestyle (single subject, controlled lighting)
- Architecture/real estate walkthroughs
- Abstract/artistic motion (particles, painterly styles)

### Weaknesses (Use Sora 2 / Veo 3.1 Instead)

- Fast/chaotic action (punches, explosions, combat, jumping, juggling)
- Complex multi-character interactions
- Crowd scenes (facial detail degrades)
- Complex physics simulations
- Readable text/signage
- Multiple overlapping voices

### Benchmark Scores (Curious Refuge)

- Overall: 6.18/10
- Visual fidelity: **7.3/10** (strongest area)
- Motion quality: 5.8/10 (mechanical, lacks overlapping movement)
- Temporal consistency: 5.6/10 (forgets context in longer sequences)

---

## Prompting Philosophy

LTX-2.3 uses a **Gemma 3 12B** text encoder with a **gated attention text connector** that is 4x larger
than LTX-2's. It follows complex instructions much better than previous versions.

**Write prompts as flowing paragraphs — not lists, not tags.**
**Longer, more descriptive prompts consistently outperform short ones.**
**Use present-tense verbs exclusively.**

### Film Director Mindset

Think **chronologically**, not statically. LTX-2.3 is extremely prompt-sensitive — static descriptions
produce static videos. Describe what **happens over time**, not just what the scene looks like.

- Write as a sequence of events: "She picks up the cup, takes a sip, then sets it down"
- **Double-confirm important actions**: "the woman talks to the viewer, she says: ..." reinforces intent
- **Small 1-2 word changes drastically alter results** — LTX-2.3 is more sensitive than Wan/Sora
- For longer clips (10s+), use **timestamp-based prompting**:
  ```
  0-4 sec: A barista grinds coffee beans, the grinder whirring loudly.
  4-8 sec: She pours steaming water over the grounds in a slow spiral.
  8-12 sec: The camera pushes in as latte art forms in the cup.
  ```

### The 6-Element Prompt Formula

Every effective LTX-2.3 prompt covers these elements in 4-8 sentences:

1. **Scene Anchor** — Where and when: location, time of day, atmosphere
2. **Subject** — Who/what is in frame, with visual detail (age, hairstyle, clothing, texture, material). Express emotion through physical cues ("shoulders tensed, jaw clenched") NOT abstract labels ("she looks sad")
3. **Action** — What happens, using present-tense verbs ("walks", "pours", "rotates"). Write as a natural flowing sequence
4. **Camera** — Shot type and movement using cinematography terms. **Skip this element when using camera LoRAs**
5. **Lighting & Mood** — Backlighting, rim light, color palette, warmth/coolness, surface textures
6. **Audio** — Sound descriptions for synchronized audio. Describe ambience, SFX, dialogue (in quotes), music

### Prompt Length by Duration

| Duration | Sentences | Guidance |
|----------|-----------|----------|
| Under 5s | 2-3 | Single action, simple camera, one environment detail |
| 5-10s | 4-8 | 2-3 connected actions, one camera movement, clear progression |
| 10-20s | 8+ | Mini-narrative with scene headers, multiple sequences, camera changes |

**Critical**: Long videos need long prompts. A short prompt for a 10s video causes the model to fill in arbitrarily.

### The "Over Time" Suffix Technique

End prompts with "Over time, [gradual change]" to evolve the scene naturally:
```
Over time, the vibration intensifies and the steam thickens.
```

---

## Words & Phrases That Work

### Camera Stability (reduces temporal jitter ~22%)
"steady dolly," "smooth gimbal," "tripod-locked," "constant speed pan," "stabilized footage"

### Realism Anchors
"live-action," "raw footage," "no CGI," "high fidelity," "4K," "natural motion blur," "180-degree shutter equivalent"

### Lens Language
"35mm" (neutral cinematic), "50mm" (intimate/food), "85mm" (portraits), "macro" (texture), "f/1.8-f/2.8"

### Film Emulation
"Kodak Portra," "Kodak 2383 print look," "chiaroscuro," "volumetric fog," "desaturated cinematic," "film grain"

### Texture/Material
"rough stone," "smooth metal," "worn fabric," "glossy surfaces," "brushed steel," "sapphire crystal," "dark brushed marble"

### Lighting
"warm tungsten," "cool streetlamp," "backlighting," "rim light," "raking light," "hard side lighting," "soft north-window light," "neon glow," "golden hour bounce"

### Style Terms
Animation: stop-motion, 2D/3D animation, claymation, hand-drawn
Stylized: comic book, cyberpunk, 8-bit pixel, surreal, minimalist, painterly
Cinematic: period drama, film noir, fantasy, epic space opera

---

## What Makes a BAD Prompt

- **Emotional labels without visuals**: "she looks sad" → "shoulders tensed, jaw clenched"
- **Text/signage requests**: LTX-2.3 cannot render readable text
- **Too many simultaneous actions**: More instructions = more things that won't render
- **Vague mood words alone**: "cozy minimalist" → describe what makes it cozy
- **Lists or bullet points**: Use flowing paragraph form
- **Conflicting camera directions**: Don't say "static" and "dolly-in" together
- **Short prompts for long videos**: Causes model to rush or stay static
- **Camera movement words WITH camera LoRA**: Let the LoRA handle motion
- **Numerical precision**: "exactly 3 birds at 45 degrees" won't work
- **Stacking 3+ camera movements**: One camera motion per clip

---

## Negative Prompts

5-8 targeted negative terms work best. Stacking 20+ causes unpredictable results.

**Standard (all content):**
```
worst quality, low quality, blurry, pixelated, grainy, distorted,
watermark, text, logo, shaky, glitchy, deformed, disfigured,
morphing, warping, flicker, temporal artifacts, freeze frame
```

**+ Hands/faces:**
```
fused fingers, bad anatomy, extra hands, deformed hands, malformed face
```

**+ Motion (for action/dynamic):**
```
static, still image, frozen, motion smear, jitter, stutter, frame blending
```

---

## Use Case Guides & Verified Prompts

### Product Videos

LTX-2.3's best use case. Single subject, controlled lighting, camera does the storytelling.

**Turntable/360:**
```
[Product] rotating 360-degree turntable, black velvet backdrop, edge light,
minimal reflections, no object duplication.
```

**Hero Reveal (with Dolly-In LoRA — no camera description):**
```
A luxury watch rests on dark brushed marble in a minimalist studio. Warm amber
side-lighting catches the polished bezel, casting soft highlights across the
sapphire crystal. The intricate dial texture becomes visible — brushed indices,
slim dauphine hands sweeping smoothly, the date window magnified by a cyclops
lens. Fine brushstroke patterns in the steel links emerge in sharp detail.
A subtle mechanical tick punctuates the silence.
```

**UGC Unboxing:**
```
Handheld smartphone UGC clip of a woman unboxing a new skincare bottle at a
kitchen table. She peels the seal, smiles, and turns the bottle toward camera.
Soft window daylight, natural colors, subtle room tone + packaging crinkle.
```

**Lifestyle Usage:**
```
Lifestyle: [person] uses [product] by window, gentle handheld micro-shake,
golden hour rim, keep horizon level, no face warp.
```

**30-Second Product Ad Shot Sequence:**
1. Dolly-Out LoRA: Wide establishing (5s)
2. Dolly-In LoRA: Medium approach (5s)
3. Static LoRA: Close-up hold (3s)
4. Dolly-Right LoRA: Product showcase (5s)
5. Dolly-In LoRA: Detail macro (3s)
6. Static LoRA: Brand moment (3s)

Settings: 1080p, 24fps, dev pipeline for final quality.

---

### B-Roll Footage

Slow, deliberate camera motion + environmental compositions = LTX-2.3 sweet spot.

**City Skyline:**
```
City skyline, slow pan right, golden hour, long shadows, no flicker, no
horizon roll.
```

**Golden-Hour Boulevard:**
```
Golden-hour city boulevard: city cyclist weaving through traffic: slow
dolly-in, 35mm, f/2.0: soft contrast, Kodak 2383: film-like cadence,
steady velocity: no text, no logos.
```

**Forest Path:**
```
Forest path, slow track forward, overcast diffuse light, deep focus,
no flicker.
```

**Pre-Dawn Desert:**
```
Pre-dawn desert highway: vintage car idling, heat shimmer: crane up 3m
then settle, 24mm: monochromatic, fine film grain: 180-degree shutter
equivalent, no judder.
```

**Foggy Lake:**
```
A lone fisherman rows across a foggy lake before sunrise, the boat creaking
softly as water laps at its sides. The camera glides overhead, tracking his
slow progress. His lantern casts a warm circle of light, reflecting in ripples
while reeds sway gently on the shoreline. A distant bird call echoes as mist
rolls across the surface, partially obscuring the horizon.
```

**Key insight**: Explicit camera paths ("dolly," "crane," "orbit") reduce temporal jitter ~22% versus
unspecified camera motion. Generate 10-15s clips, hold compositions for 3+ seconds.

Settings: 1080p or 1440p, 24fps, Dolly-Left/Right or Jib-Up LoRAs.

---

### Talking Heads / Speaking Characters

LTX-2.3 generates synchronized audio + lip sync in a single pass.

**Dialogue formatting rules:**
1. Put spoken words in **quotation marks**
2. Break long monologues into short phrases with acting directions between
3. Include tone cues: "(quietly)," "(with hesitation)," "(grinning)"
4. Specify accent/language if needed
5. Describe physical reactions to speech
6. Use "A beat," "A pause" for timing

**News Reporter (official LTX example):**
```
EXT. SMALL TOWN STREET -- MORNING -- LIVE NEWS BROADCAST
The reporter, composed but visibly excited, looks directly into the camera,
microphone in hand.
Reporter (live):
"Thank you, Sylvia. And yes -- this is a sentence I never thought I'd say on
live television -- but this morning, here in the quiet town of New Castle,
Vermont... black gold has been found!"
He gestures slightly toward the field behind him.
Reporter (grinning):
"If my cameraman can pan over, you'll see what all the excitement's about."
```

**Family Drama (official):**
```
A warm sunny backyard. The camera starts in a tight cinematic close-up of a
woman and a man in their 30s, facing each other with serious expressions. The
woman, emotional and dramatic, says softly, "That's it... Dad's lost it. And
we've lost Dad." The man exhales, slightly annoyed: "Stop being so dramatic,
Jess." A beat. He glances aside, then mutters defensively, "He's just having
fun."
```

**Sci-Fi Character (official):**
```
The young african american woman wearing a futuristic transparent visor and a
bodysuit with a tube attached to her neck. she is soldering a robotic arm. she
stops and looks to her right as she hears a suspicious strong hit sound from a
distance. she gets up slowly from her chair and says with an angry african
american accent: "Rick I told you to close that goddamn door after you!"
```

**Limits**: No overlapping voices. Focus camera on one speaker at a time.
Resolution: 1080p minimum for face detail. Use "85mm portrait" lens language.

---

### Cinematic Slow Motion

The model excels at deliberate, atmospheric motion.

**Template (from Stoke McToke):**
```
A [shot size] of [subject] performing [continuous action]. The scene takes
place in [environment]. The camera [specific slow movement]. Lighting is
[key/contrast/atmosphere]. Shot on [lens/look/realism]. Over time, [one or
two gradual changes].
```

**Cooking Pot (verified):**
```
A close-up of a vintage cooking-pot vibrating on a stove-top as steam rises
continuously from the inside. In the pot a meaty stew can be seen cooking. The
scene takes place in a small kitchen at night, lit only by a single overhead
lamp. The camera is tripod-locked and performs a slow dolly in toward the
cooking pot. Lighting is warm tungsten with deep shadows and soft highlights
in the steam. Shot on a 50mm lens, live-action realism, natural motion blur.
Over time, the vibration intensifies and the steam thickens.
```

**Noir Scene (verified):**
```
An anarchist holding a flaming Molotov bottle under a streetlamp in the rain,
slow arc from three-quarter to profile, hard top-down key with fog, 85mm,
gritty desaturated noir. Over time: throws bottle, headlights sweep, rain
and breathing audible.
```

Keywords: "natural motion blur," "180-degree shutter equivalent," "lingering shot,"
"gentle breeze," "drifting," "curling," "swaying"

For true slow-motion: generate at 48fps, conform to 24fps in post.

---

### Food / Cooking Content

Controlled environments, single subjects, warm lighting, atmospheric effects = sweet spot.

**Overhead Gourmet Burger:**
```
Overhead shot of gourmet burger with visible layers on dark slate board. Steam
rises gently. Camera slowly descends closer, revealing texture details.
Dramatic food photography with hard side lighting creating strong shadows.
```

**Latte Pour (official):**
```
A young barista in a cozy coffee shop pours steaming oat milk into a ceramic
latte cup, creating a rosetta pattern in the foam. Morning sunlight streams
through the window, backlighting the steam with golden warmth. The camera
tracks the pour from a low angle, then tilts up to catch her satisfied smile.
Ambient cafe sounds mix with the gentle hiss of the espresso machine.
```

**Cinemagraph Loop (for social media):**
```
Loopable 3-second cinemagraph of [scene], one element moving (steam/water),
no extra motion.
```

Camera LoRAs: Static (detail), Dolly-In (approaching dish), Jib-Down (overhead-to-table reveal).
Lens: "50mm macro, raking light" for texture.

---

### Fashion / Lifestyle

Fabric textures and material surfaces render well in controlled conditions.

**Walking/Lifestyle:**
```
[person] walks toward camera, track backward at slow pace, stable background,
no rolling shutter wobble.
```

**Texture Detail:**
```
Stop-scroll macro of [texture], 50mm macro, raking light, crisp detail,
no mushy surfaces.
```

Camera LoRAs: Dolly-In (fabric detail), Static (full outfit), Dolly-Left/Right (parallel tracking walk).
Limits: One outfit per clip. Fast runway motion causes artifacts.

---

### Architecture / Real Estate

Slow camera through static environments with controlled lighting.

**Interior (Jib-Up LoRA):**
```
Exposed brick walls rise to industrial ceiling beams strung with Edison bulbs.
Wooden shelving displays rows of single-origin coffee bags. Morning light
streams through skylights, casting warm geometric patterns across the
polished concrete floor.
```

**Exterior:**
```
Drone-style reveal, slow tilt up from ground to skyline, stable motion,
no rapid handheld.
```

Camera LoRAs: Dolly-Left/Right (walkthroughs), Jib-Up (ceiling reveals), Dolly-In (entryways).
Use I2V from real estate photos for maximum architectural fidelity.

---

### Nature / Wildlife

Single-subject wildlife in controlled conditions works well. "Animals like grazing ponies moving
naturally without distortion" (Curious Refuge).

**Documentary:**
```
Long lens compression 200mm, tripod-locked, distant wildlife, natural color
science, gentle breeze movement, no sudden camera moves.
```

**Close-Up Nature:**
```
Close-up flower in breeze, macro, shallow DOF, natural sway, no duplication
of petals.
```

Stick to one animal, one action. Use telephoto lens language and stability tokens.
Fast animals, swimming, flocks = unreliable.

---

### Abstract / Artistic

The model handles stylized aesthetics, particles, and artistic effects well when deliberate.

Works: painterly styles, noir, analog film, comic book, stop-motion, particle systems, lens flares.
Struggles: complex physics simulations, multiple overlapping particle systems.

Keep abstract motion to single-element compositions (one particle stream, one fluid pour).

---

## Image-to-Video (I2V) — Critical Limitations & Workarounds

**I2V has a well-documented "frozen frame" problem** (GitHub Issues #11, #117, #126). The model
often produces static or barely-moving output, especially for dynamic content.

### The CRF Compression Trick (MOST IMPORTANT)

LTX was trained on video frames with MPEG compression artifacts. Clean images confuse the model
into treating them as stills. A Lightricks developer confirmed this.

**Fix:** `LTXVPreprocess` node with `img_compression` (CRF) set to **25-35**.
- Lower CRF = more compression artifacts = more motion
- Images sourced from actual video work "almost 100% of the time"
- Our pipeline's `img_compression` parameter controls this (default: 28)
- **RuneXX uses CRF 18** for maximum motion — try 18-25 if output is too static

### I2V Strength (LTXVImgToVideoInplace)

| Strength | Behavior | Use Case |
|----------|----------|----------|
| 0.85-1.0 | Locked to first frame | Identity preservation, slow pan |
| **0.55-0.75** | **Balanced** | **General I2V (recommended)** |
| 0.4-0.55 | Loose guide, more freedom | Maximum motion potential |
| < 0.4 | Image barely influences | Risk losing reference |

### I2V Prompting Rules

- **DO NOT re-describe what's visible** — the model can see the image
- **DO describe what HAPPENS next** — action, movement, changes
- **DO describe environment changes** from the action
- Focus on **one clear action sequence**

### T2V vs I2V for Dynamic Content

**T2V is more reliable for motion.** I2V excels at identity preservation in calm shots.
For dynamic content: use T2V, describe the character's appearance in the prompt.
For I2V action: strength 0.55-0.65, CRF 25-30, roll 5-10 seeds per shot.

---

## Native Audio Prompting

LTX-2.3 generates synchronized audio in a single pass. Describe sounds explicitly:

- **Ambient**: "The faint hum of chatter and distant drilling fills the air"
- **SFX**: "The sound of the hammer hitting the nail into the wood is a strong thud"
- **Music**: "There is slight country blues music playing softly from an antique gramophone"
- **Dialogue**: Place in quotation marks, specify accent/language
- **Volume**: "whisper," "mutter," "shout," "scream"
- **Timing**: "steam burst at 2.5s," "hit on second snare"

`audio_guidance_scale`: **7.0** (dev pipeline).

---

## Camera LoRAs

**Cardinal rule: describe what the camera REVEALS, not the movement itself.**
Apply LoRAs during Stage 1 only — the upsampler preserves established motion.

For detailed LoRA reference (filenames, IC-LoRAs, stacking rules): `references/camera-loras.md`

### Quick Reference

| LoRA | Best For | Strength |
|------|----------|----------|
| `ltx-2-19b-lora-camera-control-dolly-in` | Product reveals, emphasis | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-out` | Scene reveals, context | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-left` | Lateral tracking | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-dolly-right` | Lateral tracking | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-jib-up` | Scale reveals, height | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-jib-down` | Descending, approaching | 0.8-1.0 |
| `ltx-2-19b-lora-camera-control-static` | No camera distraction | 0.7-1.0 |

### Content-Type Recommendations

- **Product**: Dolly-In (reveal) → Static (detail) → Dolly-Out (context)
- **B-Roll**: Dolly-Left/Right (tracking) or Jib-Up (environmental)
- **TikTok**: Dolly-In fast for scroll-stopping hook
- **Food**: Static (plating), Dolly-In (approach), Jib-Down (overhead reveal)
- **Architecture**: Dolly-Left/Right (walkthrough), Jib-Up (ceiling)
- **Action**: Static LoRA (let animation be the star, no fighting camera motion)

### Stacking Rules

- Camera + Camera: compatible (reduce to 0.5-0.7 each, complementary directions)
- Camera + Distilled: compatible
- **Camera + IC-LoRA: INCOMPATIBLE** (different sampler requirements)
- Total combined strength: stay under 2.0
- Don't combine opposing directions (Dolly-In + Dolly-Out)

---

## Sampler Selection Guide

Sampler choice is the **#1 technical quality factor** for LTX-2.3. The Rectified Flow architecture
responds very differently to 1st-order vs 2nd-order solvers.

### Sampler Rankings (Community-Tested)

| Stage 1 Sampler | Stage 2 Sampler | Quality | Notes |
|----------------|----------------|---------|-------|
| **`euler_ancestral_cfg_pp`** | **`euler_cfg_pp`** | **Best** | Official LTX recommendation, natural motion |
| `lcm` | `lcm` | Good | Soft-focus aesthetic, fastest |
| `euler` | `euler` | Decent | Stable but less dynamic |
| `res_2s` | `res_2s` | **Avoid** | Slow-motion artifact, over-baked look |
| `euler_ancestral` | `euler_ancestral` | **Avoid** | Temporal flickering, unstable |

### Why This Matters

- **1st-order solvers** (`euler`, `euler_ancestral`) follow the flow field directly — simpler, faster
- **2nd-order solvers** (`res_2s`, `dpmpp_2s`) estimate the midpoint — more accurate per step but can
  over-correct with LTX's distilled sigmas, causing the "slow-motion" artifact
- **`_cfg_pp` variants** apply classifier-free guidance as a post-processing step rather than inline,
  which prevents the contrast burn that standard CFG causes at low step counts
- The pipeline uses `euler_ancestral_cfg_pp` (stage 1) + `euler_cfg_pp` (stage 2) by default

---

## Key Parameters

### Dev Pipeline (Full Quality)

| Parameter | Value | Notes |
|-----------|-------|-------|
| CFG | **3.0** | Above 4.0 causes contrast burn, ringing, flicker |
| Stage 1 steps | **20** | Base generation |
| Stage 2 steps | **10** | Refinement |
| audio_guidance_scale | **7.0** | Separate audio quality control |

### Distilled Pipeline (Fast)

| Parameter | Value | Notes |
|-----------|-------|-------|
| CFG | **1.0** | Must be 1.0 with distilled LoRA |
| Stage 1 steps | **8** | Base generation |
| Stage 2 steps | **4** | Refinement |
| Speed | ~3-4x faster | Slightly less creative output |

### When Dev Wins Over Distilled

- Complex lighting setups
- Fine texture detail (skin, fabric, materials)
- Production final renders
- Complex prompts with many elements

### When Distilled Is Fine

- Drafting/iteration
- Simple compositions (single-subject, controlled lighting)
- Social media content
- As Stage 2 refiner on top of dev Stage 1

### Distilled LoRA Techniques

- **"Both-pass" technique**: Use dev model + distilled LoRA at **0.5-0.6 strength in BOTH stages**.
  This allows flexible step counts (not locked to the preset ManualSigmas values)
- Our pipeline uses **0.5** strength; RuneXX workflows use **0.6** — slightly more aggressive distillation
- When using the **distilled base model** (not dev + distilled LoRA): **bypass** the distilled LoRA node
  entirely — it's already baked in
- **IC-Detail LoRA**: Less necessary in 2.3 than 2.0 — skip for most workflows unless you specifically
  need fine detail enhancement

### Resolution & Duration Planning

| Content Type | Resolution | FPS | Duration | Notes |
|-------------|-----------|-----|----------|-------|
| **Dynamic / action** | **1280x720** | **48** | **3-5s** | Best motion quality |
| Cinematic / slow | 1920x1080 | 24 | 5-20s | High res, deliberate motion |
| Product reveal | 1280x720 | 24 | 5-10s | Smooth, controlled |
| TikTok/Reels | 1080x1920 | 24 | 5-10s | Vertical |
| B-roll (1440p) | 2560x1440 | 24 | 5-15s | Maximum quality |
| Fast iteration | 768x432 | 24 | 1-3s | Testing prompts |

Frame count must be divisible by 8 + 1 (e.g., 9, 17, 25, 33, 41, 49, 57, 65, 73, 81, 97, 121, 161, 241).
Width/height must be divisible by 32.

---

## Multi-Clip Strategy: Going Beyond 20 Seconds

### Video Extend

1. Generate base clip
2. `LTXVExtendSampler` analyzes last frames for motion/lighting/composition
3. Generates new frames continuing the narrative
4. Extend by 1-20 seconds each time

**Recommended overlap**: **73 frames** (3s at 25fps). Minimum: 25 frames.

### V2V Extend Any Video

Technique for extending any video (not just LTX-generated) with seamless blending:
1. Load external video → extract final segment as overlap region
2. Generate extension frames conditioned on the overlap
3. Blend using **25-frame filmic crossfade** (gamma 2.2 for perceptual uniformity)
4. **Iterative**: run repeatedly for progressively longer clips
5. **Prompt steering** during extension — change the narrative direction with each iteration

This requires `ImageBatchExtendWithOverlap` (KJnodes) or manual tensor blending. Standard ComfyUI
replacement: chain `ImageConcat` nodes with alpha-blended overlap frames.

Best for: extending stock footage, continuing scenes from other models, building long-form content.
See `references/advanced-techniques.md` for full implementation details.

### Last-Frame Image-to-Video Technique

For transitions between different scenes:
1. Generate Clip A → Extract last frame as PNG
2. Use PNG as I2V input with new prompt → Generates Clip B flowing from A
3. Repeat as needed

### Shot Planning (30-60s content)

```
Shot 1 (5-10s): Wide establishing — sets the scene
Shot 2 (5-10s): Medium shot — introduces subject
Shot 3 (3-5s): Close-up — highlights key detail
Shot 4 (5-10s): Action/demo — tells the story
Shot 5 (3-5s): Final — CTA or brand moment
```

---

## Frame-Guided Workflows

Our pipeline supports frame-guided generation via the `guide_frames` parameter, which chains
`LTXVAddGuide` nodes — no KJnodes required. This implements FL2V and FML2V natively.

### FL2V — First + Last Frame (via `guide_frames`)

Pass two guide frames at indices 0 (first) and -1 (last):
```python
guide_frames=[
    ("first_frame.png", 0, 1.0),   # first frame, full strength
    ("last_frame.png", -1, 1.0),   # last frame, full strength
]
```

The model interpolates between the two states.

- **Frames should differ** — identical first/last frames produce minimal motion
- Controls start and end states; the model fills in the transition
- Use cases: A-to-B transitions, morphing sequences, controlled narratives

### FML2V — First + Middle + Last Frame (via `guide_frames`)

Pass three guide frames. Use **strength 0.5** for the middle frame to allow creative freedom:
```python
guide_frames=[
    ("first.png", 0, 1.0),         # first frame, full strength
    ("middle.png", 60, 0.5),       # middle frame, flexible guidance
    ("last.png", -1, 1.0),         # last frame, full strength
]
```

- Frames are **guidance**, not hard constraints — strength < 1.0 allows the model to deviate
- Our code uses `LTXVAddGuide` chaining + `LTXVCropGuides` (same approach as RuneXX FML2V workflows)
- Use cases: consistent characters across clips, controlled scene progression, storyboarded narratives

---

## GGUF Model Options

For memory-constrained setups or faster iteration, GGUF quantized models are available:

| Source | Model | Notes |
|--------|-------|-------|
| QuantStack | Q4/Q5/Q8 variants | Good quality balance |
| Unsloth | Various quantizations | Popular choice |
| Vantage | HuggingFace hosted | Easy download |

- **Q4** provides a good quality/memory balance for VRAM-constrained GPUs
- **GGUF Gemma text encoder**: `unsloth/gemma-3-12b-it-GGUF` — reduces text encoder VRAM
- **When to use**: fast iteration, lower VRAM GPUs, batch generation
- Use same node graph as our standard pipeline but swap `CheckpointLoaderSimple` for GGUF loader

---

## Temporal Upscaling

- `ltx-2.3-temporal-upscaler-x2-1.0` converts **25fps → 50fps**
- Improves smoothness and fine detail (teeth, hair, fabric edges)
- **Optional** — 24-25fps is more cinematic for most content
- Good for slow-motion post-processing: generate at 25fps, temporally upscale to 50fps,
  then conform to 25fps for 2x slow-motion effect
- Apply after spatial upscaling in the pipeline

---

## Upscaling Pipeline

### Two-Stage Architecture

1. Stage 1: Generate at **half target resolution** (e.g., 540p → 1080p)
2. Spatial upscaler: `ltx-2.3-spatial-upscaler-x2-1.0` doubles dimensions
3. Stage 2: Refine at full resolution

Available upscalers:
- `ltx-2.3-spatial-upscaler-x2-1.0` — 2x spatial
- `ltx-2.3-spatial-upscaler-x1.5-1.0` — 1.5x spatial
- `ltx-2.3-temporal-upscaler-x2-1.0` — 2x FPS

**Always use for production.** 75% of blind-test reviewers preferred upscaled 720p over native 4K.
For 4K: 720p → 1440p → 4K (sequential 2x passes look better than single 4x).

---

## TextGenerateLTX2Prompt Node

**NOT a KJnode** — this is from the official `ComfyUI-LTXVideo` extension. Converts simple
descriptions into structured prompts using Gemma-3-12B as an LLM.
Controls: `disable_TextGenerate` (true/false), enhancer seed for variations.

"Tweaking your wording in TextGenerateLTX2Prompt usually yields bigger gains than sampler tweaks."
Useful for casual descriptions. For manually crafted prompts using the 6-element formula, bypass it.

Alternative: **LTX2EasyPrompt-LD** — local uncensored LLM prompt enhancement, zero internet dependency.

---

## Negative Anchor Guidance (NAG)

NAG applies **separate negative guidance strengths** to video and audio channels. Standard
negative prompting applies one CFG scale to everything — NAG lets you be gentle on video
(avoiding over-correction artifacts) while being aggressive on audio (improving clarity).

**How it works** (implementable with standard ComfyUI nodes):
1. Use `DualCFGGuider` instead of `CFGGuider` — this accepts two negative conditionings
2. Set **video negative strength: 0.25** (very light — prevents visual over-sharpening)
3. Set **audio negative strength: 2.5** (aggressive — cleans up audio artifacts)
4. Set **start step: 11** (apply NAG only in later sampling steps, not from the beginning)

The KJnodes `LTX2_NAG` node is just a convenience wrapper around `DualCFGGuider` with
step-gating logic. Our pipeline could implement this by swapping `CFGGuider` for
`DualCFGGuider` and adding a step-conditional switch.

**When to use**: talking head content, dialogue-heavy clips, any generation where audio
quality matters more than visual dynamism.

---

## Single-Pass Pipeline Option

For fast iteration or low-VRAM setups, skip the two-stage upscale entirely:
- Generate directly at target resolution (no half-res → upscale → refine)
- Uses the same sampler/sigma setup as Stage 1
- **Trade-off**: lower quality but ~2-3x faster, significantly less VRAM
- Good for: prompt testing, draft generation, social media content where 720p is fine

Not currently implemented in our backend — would require a `skip_upscale` parameter.

---

## LoRA Naming Note

All camera LoRAs use `ltx-2-19b-*` naming (referencing the older 19B model) but are
**confirmed compatible with the 22B LTX-2.3 model**. No 2.3-specific camera LoRAs exist yet.

The three **LTX-2.3-specific LoRAs** are:
- `ltx-2.3-22b-distilled-lora-384` — distilled inference (used by our pipeline)
- `ltx-2.3-22b-ic-lora-union-control-ref0.5` — updated union control for 2.3
- `ltx-2.3-22b-ic-lora-motion-track-control-ref0.5` — **NEW**: motion tracking IC-LoRA

---

## Prompt Generation Workflow

When generating prompts for the user:

1. **Identify content type** → select from use case guides above
2. **Determine specs** → resolution, fps, duration from the planning table
3. **Select camera** → which LoRA and why (skip camera words in prompt if using LoRA)
4. **Choose pipeline** → dev (quality) or distilled (speed)
5. **Write prompt** → 6-element formula, flowing paragraphs, present tense
6. **Add negative prompt** → 5-8 targeted terms
7. **For I2V** → CRF 25-35, strength 0.55-0.75, don't re-describe the image
8. **For multi-clip** → plan shot sequence and transition strategy

Always explain camera and prompting choices to the user.
