---
name: content-pipeline
description: |
  Master content creation pipeline orchestrator for AI-powered video and image production.
  Use this skill whenever the user wants to create short-form video content (TikTok, Reels,
  Facebook), product advertisements, product visuals, b-roll footage, animated short clips,
  or any kind of visual content for social media or marketing. This is the FIRST skill to
  trigger when the user says things like "make me a video", "create content for TikTok",
  "I need a product ad", "generate some b-roll", "make me an animation", "create a commercial",
  or any variation of content creation requests. This skill orchestrates the full pipeline:
  interviewing the user for requirements, planning shots, generating images via Nano Banana 2
  or ChatGPT, then generating video via LTX-2.3, Veo 3.1, or Sora 2. Even if the user just
  says "help me make some content" or "I have a product to promote", trigger this skill.
  It handles the entire creative workflow from concept to final prompts.
---

# Content Creation Pipeline — Master Orchestrator

## Overview

This skill orchestrates a complete content creation pipeline:

```
User Brief → Creative Interview → Shot Planning → Image Generation → Video Generation → Final Content
```

It draws on four specialized skills for the generation steps:
- **nano-banana-2** — Image generation (product photos, character references, stills)
- **ltx-video** — Local video generation via ComfyUI (free, LoRA support)
- **veo-video** — Cloud video generation via Google (native audio, character consistency)
- **sora-video** — Cloud video generation via OpenAI (cinematic quality)

Read the relevant skill's SKILL.md when you need detailed prompting guidance for that tool.

---

## Phase 1: Creative Interview

Before generating anything, interview the user to extract a complete creative brief.
This is the most important phase — poor requirements lead to wasted generation time.

### The 10 Questions

Work through these questions conversationally. Don't dump them all at once — adapt
based on what the user has already told you. Skip questions they've already answered.

**1. Content Type** — What are we making?
- Short clip (10s-1min) for TikTok/Facebook/Reels?
- Animated short clip?
- Product visual / hero shot?
- B-roll footage?
- Product advertisement?
- Something else?

**2. Product/Subject** — What's being featured?
- Physical product? (get brand, model, colors, materials, key features)
- Service? (what does it look like in action?)
- Person/character? (detailed appearance description)
- Abstract concept? (what visual metaphor?)

**3. Target Platform** — Where will this be posted?
- TikTok → 9:16, 15-60s, energetic, scroll-stopping hook
- Instagram Reels → 9:16, 15-90s, polished, aesthetic
- Facebook → 16:9 or 1:1, 15-60s, accessible
- YouTube Shorts → 9:16, up to 60s
- Website/landing page → 16:9, any length, premium quality
- Multiple platforms? → Generate for strictest format, adapt

**4. Mood & Style** — What should it feel like?
- Luxury/premium → slow movements, warm lighting, shallow DOF
- Energetic/fun → fast cuts, bright colors, dynamic camera
- Professional/corporate → clean, steady, well-lit
- Artistic/moody → dramatic lighting, cinematic color grade
- Casual/authentic → handheld feel, natural lighting

**5. Duration** — How long?
- Under 10s → single clip, no concatenation needed
- 10-20s → single LTX-2.3 clip or 2-3 Veo clips
- 20-60s → multi-clip, needs shot planning and concatenation
- Over 60s → full shot list, multiple generation rounds

**6. Reference Material** — Does the user have any of these?
- Existing product photos → can use as image-to-video input
- Brand guidelines → colors, fonts, mood boards
- Competitor examples → "I want something like this"
- Storyboard/shot list → great, we can work from this

**7. Key Message** — What should viewers take away?
- Product quality/features?
- Lifestyle aspiration?
- Brand awareness?
- Call to action? (if so, what?)

**8. Audio Needs** — What should it sound like?
- Music? (genre, tempo, mood)
- Voice-over? (if so, what does it say?)
- Sound effects? (satisfying clicks, nature sounds, etc.)
- Silent? (for platforms where auto-play is muted)

**9. Budget/Tool Preference** — Which generation tools to use?
- Free/local only → LTX-2.3 via ComfyUI
- Cloud OK → Veo 3.1 or Sora 2
- Best quality regardless → Veo 3.1 Standard/Full
- Need native audio → Veo 3.1 (best) or Sora 2

**10. Existing Assets** — What images/footage already exists?
- Product photos that can feed image-to-video?
- Brand logos/assets for end cards?
- Character photos for reference?

---

## Phase 2: Creative Brief Summary

After the interview, compile a creative brief and confirm with the user before proceeding.

### Brief Template

```
PROJECT: [Name/description]
CONTENT TYPE: [Short clip / Animation / Product ad / B-roll]
PLATFORM: [TikTok / Instagram / Facebook / YouTube / Website]
ASPECT RATIO: [9:16 / 16:9 / 1:1]
DURATION: [Total length]
STYLE: [Mood description]
SUBJECT: [Detailed description]
KEY MESSAGE: [What viewers should feel/know]
AUDIO: [Music/SFX/Voice/Silent]

GENERATION TOOLS:
- Images: [Nano Banana 2 / ChatGPT / User-provided]
- Video: [LTX-2.3 / Veo 3.1 / Sora 2]

SHOT PLAN:
[See Phase 3]
```

---

## Phase 3: Shot Planning

Based on the brief, create a detailed shot list. Each shot becomes one generation task.

### Shot List Template

```
SHOT 1: [Name]
- Type: [Establishing / Medium / Close-up / Detail / Action / Transition]
- Duration: [seconds]
- Camera: [Movement + Lens]
- Subject: [What's in frame]
- Action: [What happens]
- Lighting: [Setup]
- Audio: [What we hear]
- LoRA: [If using LTX-2.3, which camera LoRA]
- Transition to next: [Cut / Extend / Last-frame bridge]

SHOT 2: [Name]
...
```

### Content-Type Shot Templates

#### Template: Product Advertisement (30s)

```
SHOT 1 — Establishing (5s)
  Wide shot, lifestyle context. Product's world.
  Camera: Slow dolly-in or pan. LoRA: Dolly-In (0.7)
  Audio: Ambient scene sounds, soft music begins

SHOT 2 — Product Introduction (5s)
  Medium shot. First clear view of product.
  Camera: Dolly-In. LoRA: Dolly-In (0.9)
  Audio: Music builds, satisfying product sound

SHOT 3 — Feature Highlight (3-5s)
  Close-up. Key selling feature in detail.
  Camera: Static or very slow Dolly-In. LoRA: Static (0.8)
  Audio: Feature sound (click, snap, pour, etc.)

SHOT 4 — In-Action (5-8s)
  Medium-wide. Product being used in context.
  Camera: Tracking or Dolly-Right. LoRA: Dolly-Right (0.8)
  Audio: Usage sounds, music at peak

SHOT 5 — Detail/Quality (3s)
  Extreme close-up. Texture, material, craftsmanship.
  Camera: Static. LoRA: Static (1.0)
  Audio: Music softens

SHOT 6 — Brand Moment (3-5s)
  Clean product shot, possible CTA.
  Camera: Static or gentle Dolly-Out. LoRA: Dolly-Out (0.7)
  Audio: Music resolves, brand sting
```

#### Template: TikTok Short Clip (15-30s)

```
SHOT 1 — Hook (2-3s)
  Most dramatic/interesting visual. Stops the scroll.
  Camera: Crash zoom or fast Dolly-In
  Audio: Impact sound or trending audio hook

SHOT 2 — Setup (3-5s)
  Context for what's happening
  Camera: Medium shot, handheld energy
  Audio: Music kicks in, energetic

SHOT 3 — Payoff (3-5s)
  The main event / reveal / transformation
  Camera: Dynamic movement matching energy
  Audio: Peak moment, bass drop or silence-then-impact

SHOT 4 — Reaction/Result (2-3s)
  Aftermath, satisfaction, result
  Camera: Close-up or medium
  Audio: Resolution, satisfying sound

SHOT 5 — CTA/Loop Point (2s)
  End that encourages replay or action
  Camera: Match Shot 1 framing for seamless loop
  Audio: Loop back to hook sound
```

#### Template: B-Roll Package (60s)

```
Generate 8-12 varied clips of 5-10s each. Mix:
- 2-3 wide establishing shots (different angles)
- 2-3 medium detail shots
- 2-3 close-up texture/detail shots
- 1-2 movement/action shots
- 1-2 atmospheric/mood shots

Vary camera movements: pan, dolly, jib, tracking, static
Each clip should be independently usable — clean start and end
```

#### Template: Animated Short (30-60s)

```
SHOT 1 — World Introduction (5-8s)
  Establish the animated world. Style, color palette, atmosphere.
  Camera: Wide, slow pan or jib-up
  Audio: Theme music intro, ambient world sounds

SHOT 2 — Character Entrance (5-8s)
  Introduce main character with personality-revealing action
  Camera: Medium shot, gentle tracking
  Audio: Character-specific sounds, music develops

SHOT 3 — Story Beat 1 (5-8s)
  First narrative moment / problem / discovery
  Camera: Varies with emotion (close-up for intimacy, wide for scale)
  Audio: Reactive audio

SHOT 4 — Story Beat 2 (5-8s)
  Development, escalation, or transformation
  Camera: Dynamic, matching energy
  Audio: Music shifts, new sounds

SHOT 5 — Resolution (5-8s)
  Conclusion, punchline, or emotional payoff
  Camera: Pull-back or static hold
  Audio: Resolving music, satisfying conclusion
```

---

## Phase 4: Image Generation

Before video generation, create reference images for subjects that don't have existing photos.

### Decision Tree: Do We Need to Generate Images?

```
Does the user have product/subject photos?
├── YES → Use those as image-to-video input. Skip to Phase 5.
├── PARTIALLY → Generate missing angles/contexts. Proceed below.
└── NO → Generate full reference set. Proceed below.
```

### What Images to Generate

**For product content:**
1. Hero product shot (clean, studio lit) → primary video input
2. Detail close-up (textures, features) → for detail shots
3. Lifestyle context image (product in setting) → for establishing shots

**For character content:**
1. Front-facing portrait → primary reference
2. Three-quarter angle → secondary reference
3. Profile view → depth reference
4. Expression variants if needed

**For animated content:**
1. Character design reference → consistent appearance guide
2. Environment/world reference → setting consistency
3. Key props or objects → detail consistency

### Image Generation Prompts

Read the **nano-banana-2** skill for detailed prompting guidance when using Nano Banana 2.
Read the **sora-video** skill for ChatGPT image generation guidance.

**Key principle**: Images generated here become inputs for video generation. They must be:
- High resolution (1080p+)
- Clean composition with clear subject
- Consistent lighting and style across the set
- Leaving enough visual context for the video model to understand the scene

---

## Phase 5: Video Generation

Now generate the video for each shot in the shot list.

### Tool Selection Per Shot

Choose the right tool for each shot:

| Shot Need | Best Tool | Why |
|-----------|-----------|-----|
| Local, free, with LoRA control | LTX-2.3 | Camera LoRAs, no cost |
| Needs synchronized audio | Veo 3.1 | Best native audio |
| Needs character consistency | Veo 3.1 (with references) | Reference image support |
| Highest photorealism | Sora 2 or Veo 3.1 | Both excel here |
| Quick iteration/draft | LTX-2.3 | Fastest (local GPU) |
| Extended scene (>20s single take) | Veo 3.1 | Scene extension to 148s |

### Generating Prompts

For each shot, generate a complete prompt using the relevant skill:

1. Read the shot plan
2. Read the relevant skill (ltx-video, veo-video, or sora-video)
3. Write the prompt following that skill's formula
4. Include all technical parameters (resolution, duration, FPS, LoRA, etc.)
5. Present to the user for approval before generation

### Multi-Clip Assembly Strategy

For content longer than one clip's maximum duration:

**LTX-2.3 (max 20s per clip)**:
1. Generate Shot 1
2. Extract last frame as PNG
3. Use last frame as image-to-video input for Shot 2
4. Write continuation prompt for Shot 2
5. Repeat for each subsequent shot
6. Use LTX-2.3's video extend feature when continuing within the same scene
7. Use last-frame image-to-video when transitioning between scenes

**Veo 3.1 (max 8s per clip)**:
1. Generate Shot 1
2. Use scene extension for continuation within same scene (adds 7s each)
3. For new scenes, generate separately with same character references
4. Up to 20 extensions possible (~148s total)

**Sora 2 (max 12s per clip) / Sora 2 Pro (max 25s per clip)**:
1. Generate each shot independently
2. Use image-to-video with consistent reference image for each shot
3. Plan for post-production editing to assemble

### Transition Strategy Between Clips

| Transition Type | When to Use | How |
|----------------|-------------|-----|
| Video Extend | Same scene continues | Let model continue from last frames |
| Last-frame bridge | Scene shift but visual continuity | Extract last frame → image-to-video |
| Hard cut | Intentional scene change | Just cut — plan framing to match |
| Match cut | Creative transition | End clip A and start clip B on similar visual |

---

## Phase 6: Output & Delivery

### Final Prompt Package

Deliver a complete set of prompts organized by shot, including:

```
=== SHOT [N]: [Name] ===

TOOL: [LTX-2.3 / Veo 3.1 / Sora 2]
INPUT: [Text-only / Image reference → filename]

PROMPT:
[Full generation prompt]

NEGATIVE PROMPT (if LTX-2.3):
[Negative prompt text]

PARAMETERS:
- Resolution: [WxH]
- Duration: [seconds]
- FPS: [24/25/48/50]
- Aspect Ratio: [16:9 / 9:16 / 1:1]
- CFG/Guidance: [value]
- LoRA: [name + strength] (if LTX-2.3)
- Tier: [Fast/Standard/Full] (if Veo 3.1)

TRANSITION TO NEXT:
[Extend / Last-frame / Hard cut]

NOTES:
[Any special instructions for this shot]
```

### Assembly Notes

Include instructions for assembling the final video:
- Which clips need to be concatenated
- Where to add cuts vs. where clips should flow continuously
- Audio considerations (where to use native audio vs. replace)
- Color grading consistency checks
- Platform-specific export settings (codec, bitrate, aspect ratio)

---

## Quick Start Flows

### "I just want a quick TikTok clip"

1. Ask: What's the subject? What's the hook?
2. Generate 1 reference image if no product photo exists
3. Write 1-3 shot prompts (15-30s total)
4. Recommend LTX-2.3 for speed, Veo 3.1 for audio

### "I need a product advertisement"

1. Full creative interview (10 questions)
2. Plan 5-6 shots (30s total)
3. Generate product reference images if needed
4. Write all prompts with camera LoRA selections
5. Plan transitions between shots

### "Give me some b-roll"

1. Ask: What's the subject/theme? What mood?
2. Plan 8-12 varied clips
3. Mix camera movements and angles
4. Generate all prompts — each clip independent
5. Each clip 5-10s for editing flexibility

### "Make me an animated short"

1. Ask: What's the story? What style?
2. Generate character/world reference images
3. Plan 5-8 story beats
4. Write prompts maintaining style consistency
5. Plan smooth transitions between beats

---

## Common Pitfalls to Avoid

1. **Skipping the interview** — Generating without clear requirements wastes credits and time.
   Always confirm the brief before generating.

2. **Inconsistent descriptions** — Changing even small words between shots breaks consistency.
   Copy character/product descriptions verbatim across all prompts.

3. **Overcomplicating single clips** — One dominant action per clip. If you need complexity,
   use multiple clips.

4. **Ignoring audio** — Silent content performs worse on social media. Plan audio from the start.

5. **Wrong aspect ratio** — 9:16 for TikTok/Reels, 16:9 for YouTube/website, 1:1 for Instagram feed.
   Getting this wrong means re-generating everything.

6. **Not planning transitions** — Multi-clip content needs deliberate transitions.
   Plan these in the shot list, not as an afterthought.

7. **Forgetting platform requirements** — Each platform has different optimal durations,
   aspect ratios, and engagement patterns. Design for the platform from the start.
