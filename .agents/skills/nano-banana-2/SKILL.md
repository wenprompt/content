---
name: nano-banana-2
description: |
  Expert prompting skill for Google Nano Banana 2 (Gemini 3.1 Flash Image) for AI image
  generation. Use this skill whenever the user wants to generate images using Nano Banana,
  Nano Banana 2, Gemini image generation, or Google's image generation model. Also trigger
  when the user needs product photography, e-commerce images, reference images for video
  generation, character reference sheets, lifestyle product shots, or any static image
  generation that feeds into a content creation pipeline. This skill is especially valuable
  for creating consistent product image sets, character reference images for video workflows,
  and high-quality promotional stills. If the user mentions "image gen" or "generate an image"
  without specifying a model, consider suggesting this skill alongside ChatGPT image gen.
---

# Nano Banana 2 Image Generation — Prompting Guide

## What is Nano Banana 2?

Nano Banana 2 (official name: Gemini 3.1 Flash Image) is Google DeepMind's image generation
and editing model, released February 2026. It combines advanced reasoning with fast generation,
making it excellent for product photography and consistent image sets.

**Key strengths**:
- 2-5x faster generation than predecessors (varies by resolution)
- Native 4K resolution support
- Maintains facial consistency across up to 5 distinct characters
- Preserves fidelity of up to 14 objects in a single workflow
- Accurate text rendering within images
- Multi-language text support
- Configurable reasoning levels (Minimal vs High/Dynamic)

**Access**: Google Gemini API, Google AI Studio, Vertex AI, third-party APIs (Kie AI, fal.ai).
**Model ID**: gemini-3.1-flash-image-preview
**Pricing**: ~$0.067/image at 2K via API. Batch mode offers 50% discount. Third-party providers may be cheaper (~$0.03/call).

---

## Core Prompting Philosophy

Nano Banana 2 is a **thinking model**, not a tag-matching system. It understands creative
intent, physics, spatial relationships, and composition before rendering. Treat it like
giving direction to a skilled photographer, not feeding keywords to a search engine.

### The Photography Language Approach

Nano Banana 2 responds exceptionally well to real photography terminology:

- **Name real cameras**: Canon 5D Mark IV, Sony A7R, Hasselblad, Leica M6
- **Specify lenses**: 50mm f/1.8, 85mm f/1.4, 24-70mm zoom, macro 100mm
- **Reference film stocks**: Kodak Portra 400, Fujifilm Velvia, Ilford HP5
- **Describe lighting setups**: Key light, fill light, rim light, butterfly lighting
- **Include technical settings**: f/2.8 aperture, 1/250 shutter, ISO 100, 3200K color temp

### Example — Photography-Directed Prompt
```
Shot on Canon EOS R5 with 85mm f/1.4 lens. A ceramic pour-over coffee dripper mid-pour,
hot water creating a bloom in the coffee grounds. Warm side lighting from the left at 3200K
color temperature, creating steam highlights. Dark moody background, shallow depth of field
with creamy bokeh. Kodak Portra 400 color science — warm midtones, gentle grain. Product
centered in frame with negative space on the right.
```

---

## Prompt Structure for Different Use Cases

### Product Photography (E-Commerce)

The key to professional e-commerce is **consistency across a set**. Use fixed parameters
that stay constant, with only the angle/context changing.

**Fixed Parameter Template**:
```
FIXED: [Background], [Camera + Lens], [Lighting setup], [Color temperature],
[Aesthetic], [Resolution]

SHOT: [Specific angle/context for this image]
```

**Example — Watch Product Set**:

Shot 1 — Hero:
```
White seamless studio background. Canon EOS R5, 50mm f/1.8 lens. Studio LED panels
at 5500K, key light from upper-left, soft fill from right. Clean minimal aesthetic, 4K.
Luxury watch, three-quarter angle showing face and band, slight tilt to reveal depth.
Sharp focus on watch face, subtle shadow beneath.
```

Shot 2 — Detail:
```
White seamless studio background. Canon EOS R5, 100mm macro lens. Studio LED panels
at 5500K, key light from upper-left, soft fill from right. Clean minimal aesthetic, 4K.
Extreme close-up of watch dial showing hour markers and complications. Crystal-clear
focus on the minute details, shallow depth of field blurs the outer bezel.
```

Shot 3 — Lifestyle:
```
Weathered oak desk surface, warm interior setting. Canon EOS R5, 35mm f/1.4 lens.
Natural window light from the left, golden hour warmth. Warm, inviting aesthetic, 4K.
Watch on wrist of person in tailored navy suit jacket, hand resting casually on the desk
next to a leather notebook and fountain pen. Shallow depth of field, lifestyle context.
```

### 8 Essential E-Commerce Templates

1. **White background hero** — Clean product on white, studio lighting
2. **Lifestyle/in-use** — Product being used in context
3. **Detail/macro** — Close-up of key feature or texture
4. **Comparison** — Product vs alternative (size reference)
5. **Flat lay** — Top-down arrangement with complementary items
6. **Packaging** — Product in its box/packaging
7. **Scale reference** — Person holding/wearing product
8. **Environmental context** — Product in its intended setting

---

### Character Reference Images (For Video Pipelines)

When generating images that will feed into video generation (LTX-2.3, Veo 3.1, Sora),
character consistency is critical.

**Character Reference Sheet Template**:
```
Professional character reference sheet. [Character description: age, ethnicity, build,
hair color/style, distinguishing features]. Neutral expression, clean studio lighting.
Three views: front-facing portrait, three-quarter angle, profile view. White background,
even lighting from all sides. Shot on Canon 5D Mark IV, 85mm f/2.0. Sharp focus on
facial features. Photorealistic, high detail.
```

**For varied expressions** (more reference images = better video consistency):
```
Same [character description]. Expression set: neutral, smiling, surprised, determined,
laughing, contemplative. Bust-level framing, same white background and lighting as
reference sheet. Consistent clothing: [exact outfit description].
```

### Product Reference Images (For Video Pipelines)

Images generated here become the starting point for image-to-video workflows.

```
Clean product photography of [product description]. White or neutral background.
Multiple angles in one image: front view, three-quarter view, side view, top view.
Studio lighting, sharp focus, no background distractions. This image will be used
as reference for video generation — ensure all product details are clearly visible.
```

---

### Promotional / Social Media Stills

```
Instagram-ready promotional image. [Product] arranged in a lifestyle flatlay on
[surface material]. Surrounded by [complementary props that reinforce brand identity].
Overhead camera angle, even soft lighting. [Brand color palette]. Modern, aspirational
aesthetic. Negative space for text overlay on [left/right/top]. 4:5 aspect ratio for
Instagram feed.
```

### Cinematic / Artistic Stills

```
Cinematic still frame. [Subject] in [dramatic setting]. Shot on Hasselblad with Zeiss
80mm lens. [Dramatic lighting description — single source, hard shadows, volumetric].
[Film reference color grade — teal and orange, desaturated noir, warm golden hour].
16:9 aspect ratio, cinematic composition with [rule of thirds / leading lines / symmetry].
```

---

## Advanced Techniques

### Edit Instead of Re-rolling

If an image is 80% correct, request specific changes conversationally:
- "Change the red jacket to black leather, keep everything else"
- "Make the shadow softer and add a slight warm tint"
- "Move the product slightly left and add more negative space on the right"

This is faster and more precise than regenerating from scratch.

### Web-Grounded Knowledge

Nano Banana 2 knows real locations and can render recognizable settings:
- "View from a café in Montmartre, Paris" → recognizable Parisian architecture
- "Brooklyn brownstone stoop in autumn" → appropriate red-brick architecture with fall colors
- "Tokyo Shibuya crossing at night" → neon-lit intersection with characteristic buildings

### Configurable Reasoning Levels

- **Minimal** (default): Fast generation, good for straightforward images
- **High/Dynamic**: Model reasons through complex prompts before rendering. Use for:
  - Multi-subject compositions
  - Complex spatial relationships
  - Images with specific text rendering requirements
  - When precision matters more than speed

### Aspect Ratios

| Ratio | Use Case |
|-------|----------|
| 1:1 (1024×1024) | Instagram feed, product squares |
| 4:5 (1024×1280) | Instagram feed (slightly taller) |
| 16:9 (1024×576) | Landscape, YouTube thumbnails, cinematic |
| 9:16 (576×1024) | Stories, TikTok covers, vertical content |
| 1:4 | Tall vertical banners, infographic strips |
| 4:1 | Wide banners, website headers |
| 1:8 | Ultra-tall vertical strips |
| 8:1 | Ultra-wide banners, cinematic panoramic |

---

## Role in the Content Pipeline

Nano Banana 2 serves as the **image generation engine** in the content creation pipeline:

### Pipeline Flow

```
1. User describes content goal
2. → Nano Banana 2 generates product/character reference images
3. → Reference images feed into video generation (LTX-2.3 / Veo 3.1 / Sora)
4. → Video model animates the reference images with motion + audio
5. → Final video output
```

### Generating Pipeline-Ready Images

When creating images specifically for the video pipeline:

**For LTX-2.3 Image-to-Video**:
- Generate at 1080p or higher (will be downscaled as needed)
- Clean, uncluttered composition — the video model needs clear subject matter
- Avoid extreme close-ups that leave no room for implied motion
- Include enough context for the video model to understand the scene

**For Veo 3.1 Ingredients-to-Video**:
- Character references: front-facing, well-lit, neutral expression
- Product references: clean background, sharp details
- Generate 2-3 reference images per character/product

**For Sora Image-to-Video**:
- Single clear subject per image
- Composition should suggest the direction of motion you want
- Leave "space" in the frame for where the action will go

---

## When to Choose Nano Banana 2 vs ChatGPT Image Gen

| Scenario | Nano Banana 2 | ChatGPT (GPT-4o) |
|----------|--------------|-------------------|
| Speed | 3-5x faster | Standard |
| Character consistency | Up to 5 characters | No built-in consistency |
| Object consistency | Up to 14 objects | Limited |
| Text rendering | Excellent | Good |
| Photography language | Excellent response | Good response |
| Conversational editing | Good | Excellent (natural chat) |
| API access | Gemini API | OpenAI API |
| Cost | Per-call (~$0.03 via third-party) | Included in ChatGPT sub |
| E-commerce sets | Excellent (fixed params) | Requires more discipline |
| Quick concept | Good | Better (conversational) |
