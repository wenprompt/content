# Product Requirements Document: AI Content Creation Pipeline

**Author:** Wang
**Date:** March 11, 2026
**Version:** 3.0 (Final)
**Status:** Final — Consolidated with Trend Intelligence Module

---

## 1. Executive Summary

An automated, end-to-end content creation pipeline that takes a creative brief and produces short-form video content for social media and marketing. The system provides a local web UI where users describe what they want, upload reference images, and receive finished video clips with all intermediate steps handled automatically.

The pipeline includes a **Trend Intelligence Module** that fetches viral videos from TikTok, Instagram, and Facebook via Apify scrapers, analyzes them with Gemini 3 Pro and Google Video Intelligence API to understand what makes them successful, and feeds those insights directly into prompt generation so all generated content is informed by real platform performance data.

**Target hardware:** Windows PC, NVIDIA RTX 5090 (32GB VRAM), ComfyUI installed locally with LTX-2.3.

### Content Types Supported

- Short clips (10s–60s) for TikTok, Instagram Reels, Facebook, YouTube Shorts
- Animated short clips (same platforms)
- Product visuals and hero shots
- B-roll footage
- Product advertisements

### Pipeline Flow

*Trend Browser (analyze viral content) → Creative Brief Form → Shot Planner (trend-informed) → Image Generation → Video Generation → Concatenation → Final Output*

---

## 2. Problem Statement

Creating AI-generated video content currently requires manually:

1. Writing optimized prompts for each tool (different syntax per model)
2. Copying prompts into ComfyUI, Veo, Sora, or Nano Banana 2 individually
3. Downloading outputs, extracting last frames, re-uploading for continuations
4. Concatenating clips manually in video editing software
5. Having no data on what visual styles, pacing, and hooks are actually performing on each platform

This pipeline eliminates all manual steps after the initial creative brief and adds data-driven trend intelligence.

---

## 3. Goals

- **Single interface:** One web UI to control all generation tools
- **Brief-to-video:** From a text description and optional images to finished video
- **Trend-informed:** Analyze viral content and automatically apply winning patterns to prompts
- **Multi-tool orchestration:** Route work to ComfyUI (LTX-2.3), Google (Veo 3.1 / Nano Banana 2), or OpenAI (Sora 2 / GPT Image) based on shot requirements
- **Seamless concatenation:** Automatic last-frame extraction and video stitching for clips exceeding single-generation limits
- **Beginner-friendly:** Clear UI with progress feedback, no terminal required after initial setup

---

## 4. Non-Goals (v1)

- Real-time video editing or timeline editor (use DaVinci Resolve or CapCut for post-production)
- Training custom LoRAs (out of scope; use existing camera LoRAs)
- Audio post-production (mixing, mastering)
- Direct social media publishing (export MP4, user uploads manually)
- Mobile app

---

## 5. System Architecture

The system is composed of four layers: Frontend (Next.js web UI), Backend (Python FastAPI server), External APIs (ComfyUI, Google, OpenAI), and Post-Processing (FFmpeg).

### Architecture Overview

```
Web UI (Next.js 16 + Tailwind v4, localhost:3000)
    |  REST API + WebSocket
    v
Backend Server (Python FastAPI, localhost:8000)
    |--- Trend Intelligence Module
    |       |--- Apify Scrapers (TikTok, Instagram, Facebook)
    |       |--- Gemini 3 Pro (creative video analysis)
    |       |--- Video Intelligence API (structured analysis)
    |       |--- Google Trends API (topic context)
    |
    |--- Pipeline Orchestrator
    |       |--- Brief Parser + Prompt Generator
    |       |--- Trend-Informed Prompt Enhancer
    |
    |--- Generation Clients
    |       |--- ComfyUI Client (localhost:8188) -> LTX-2.3
    |       |--- Google Client -> Nano Banana 2 + Veo 3.1
    |       |--- OpenAI Client -> GPT Image + Sora 2
    |
    |--- Post-Processing (FFmpeg)
            |--- Last-frame extraction
            |--- Video concatenation
            |--- Resolution normalization
            |--- Format conversion (MP4 H.264)
```

---

## 6. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js 16 (React 19) + Tailwind CSS v4 + TanStack Query v5 | SSR/SSG, App Router, server-first architecture; Turbopack default bundler (replaces Vite) |
| Backend | Python 3.11+ / FastAPI | Async support, clean API design |
| Local Video | ComfyUI REST API (localhost:8188) | LTX-2.3 runs here, already installed |
| Google APIs | google-genai Python SDK | Nano Banana 2 + Veo 3.1 |
| OpenAI APIs | openai Python SDK | GPT Image + Sora 2 |
| Video Processing | FFmpeg (CLI via subprocess) | Industry standard, all formats |
| Task Queue | Python asyncio + in-memory queue | Simple for single-user |
| Database | SQLite (via SQLAlchemy) | Lightweight, project history + job status |
| Trend Scraping | Apify Python SDK | TikTok, Instagram, Facebook scrapers |
| Video Analysis | Gemini 3 Pro + Video Intelligence | Style, pacing, hooks analysis |
| Trend Context | Google Trends API (alpha) | Rising topics and search interest |
| Config | .env + pydantic-settings | API keys, ComfyUI URL, output paths |

---

## 7. API Integrations

### 7.1 ComfyUI (LTX-2.3) — Local Video Generation

**Connection:** REST API at `http://localhost:8188` + WebSocket at `ws://localhost:8188/ws`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Submit workflow JSON for execution |
| `/queue` | GET | Check running/pending jobs |
| `/history/{prompt_id}` | GET | Poll for completion + get outputs |
| `/view` | GET | Download generated images/videos |
| `/upload/image` | POST | Upload input images for image-to-video |
| `/ws?clientId={id}` | WS | Real-time progress (sampling %) |

#### Workflow Building (Programmatic, not JSON templates)

Workflows are built programmatically in `backend/clients/comfyui_client.py` — no static JSON template files. This approach is more maintainable because node connections, LoRA insertion, and T2V/I2V branching are handled in Python code.

**Critical: T2V and I2V use separate workflow structures.** ComfyUI validates ALL node inputs at submission time (no native bypass/mute in API format — see [GitHub Issue #4028](https://github.com/comfyanonymous/ComfyUI/issues/4028)). A T2V workflow that includes `LoadImage("example.png")` with `bypass=True` will still fail validation with a 400 error. Therefore:

- **T2V workflow:** Excludes all image nodes (LoadImage, ResizeImageMaskNode, ResizeImagesByLongerEdge, LTXVPreprocess, LTXVImgToVideoInplace). `EmptyLTXVLatentVideo` feeds directly into `LTXVConcatAVLatent` for stage 1, and `LTXVLatentUpsampler` feeds directly into stage 2.
- **I2V workflow:** Includes image preprocessing chain and `LTXVImgToVideoInplace` at both stages with `bypass=False`.

**Two-stage distilled pipeline (LTX-2.3):**
```
Stage 1: Half-resolution (w/2, h/2), 8 steps, euler_ancestral_cfg_pp, CFG=1
    → LTXVLatentUpsampler 2x
Stage 2: Full-resolution, 4 steps (3 sigmas), euler_cfg_pp, CFG=1
    → VAEDecodeTiled → CreateVideo → SaveVideo
```

**Required models:**
- Checkpoint: `ltx-2.3-22b-dev-fp8.safetensors` (loaded via CheckpointLoaderSimple)
- Text encoder: `gemma_3_12B_it_fp4_mixed.safetensors` (loaded via LTXAVTextEncoderLoader, NOT CLIPLoader)
- Distilled LoRA: `ltx-2.3-22b-distilled-lora-384.safetensors` (always loaded, strength 0.5)
- Latent upscaler: `ltx-2.3-spatial-upscaler-x2-1.0.safetensors`
- Audio VAE: loaded via LTXVAudioVAELoader from checkpoint

**Key node types (NOT the same as older LTX-Video 2b):**
- `LTXAVTextEncoderLoader` (not CLIPLoader)
- `SamplerCustomAdvanced` + `CFGGuider` (not SamplerCustom)
- `ManualSigmas` (not LTXVScheduler)
- `VAEDecodeTiled` (not VAEDecode — for VRAM efficiency)
- `LoraLoaderModelOnly` (not LoraLoader — model-only variant)
- `LTXVImgToVideoInplace` (I2V only)
- `LTXVEmptyLatentAudio` + `LTXVConcatAVLatent` + `LTXVSeparateAVLatent` + `LTXVAudioVAEDecode` (native audio)

**Image upload for I2V:** Use `POST /upload/image` with `subfolder=""` (empty string). Using `subfolder="input"` places the file in `input/input/` which `LoadImage` cannot find.

**History output key:** ComfyUI returns video files under the `"images"` key (not `"videos"` or `"gifs"`) in the history response.

#### Key Parameters

| Parameter | Range | Default | Notes |
|-----------|-------|---------|-------|
| seed | 0 to 2^32 | random | Set for reproducibility; stage 2 uses seed+1 |
| steps | N/A | 8+4 (fixed) | Distilled pipeline uses fixed sigma schedules |
| cfg | N/A | 1 (fixed) | Distilled LoRA requires CFG=1 |
| width/height | div by 32 | 1280/720 | Half-res for stage 1, full for stage 2 |
| num_frames | 8n+1 | 121 | 121 frames = ~5s at 24fps. Minimum: 9 frames |

#### Async Flow

1. POST `/prompt` → receive `prompt_id`
2. Connect WebSocket `/ws` → listen for progress events
3. On "executing" with `node=null` → job complete
4. GET `/history/{prompt_id}` → get output filenames
5. GET `/view?filename={name}&type=output` → download video/image

---

### 7.2 Google Gemini API — Nano Banana 2 (Image Generation)

**SDK:** google-genai Python package | **Model:** `gemini-3.1-flash-image-preview`

Images returned as base64-encoded PNG in the response. Supports aspect ratios: 1:1, 4:5, 9:16, 16:9, and more. Resolutions: 512px, 1K, 2K, 4K.

| Resolution | Cost/Image | Use Case |
|-----------|-----------|----------|
| Up to 1024x1024 | ~$0.039 | Quick concepts, drafts |
| 2K (2048x2048) | ~$0.07 | Production product photos |
| 4K (4096x4096) | ~$0.24 | Hero images, print-ready |

---

### 7.3 Google Vertex AI — Veo 3.1 (Video Generation)

**SDK:** google-genai | **Model:** `veo-3.1-generate-001` (GA)

Supports text-to-video, image-to-video, reference images (Ingredients to Video, up to 3 images), and scene extension (up to 148s via 20 extensions of 7s each). Outputs to Google Cloud Storage. Native synchronized audio generation (dialogue, SFX, music, ambient).

| Tier | Cost/Second | 8s Video | Best For |
|------|-----------|---------|----------|
| Fast | $0.15 | $1.20 | Rapid iteration, drafts |
| Standard | $0.40 | $3.20 | Production with reference images |
| Full | $0.75 | $6.00 | Highest quality final output |

Async pattern: `generate_videos()` returns an Operation object. Poll every 10–15 seconds. Typical generation time: 2–5 minutes.

**Dependency:** Requires a Google Cloud Storage bucket for output. Pipeline must upload inputs and download outputs from GCS.

---

### 7.4 OpenAI — GPT Image (Image Generation)

**SDK:** openai Python package | **Model:** `gpt-image-1.5`

Supports sizes: 1024x1024, 1536x1024, 1024x1536. Quality: low (~$0.03), medium (~$0.08), high (~$0.167). Returns base64 or URL.

---

### 7.5 OpenAI — Sora 2 (Video Generation)

**SDK:** openai (async) | **Models:** `sora-2` (fast), `sora-2-pro` (high quality)

Supports text-to-video and image-to-video. Duration: 6–60 seconds. Resolution: 720p (sora-2), 720p/1080p (sora-2-pro). Native synchronized audio. Async polling: check status every 10 seconds until completed.

| Model | Resolution | Cost/Second |
|-------|-----------|------------|
| sora-2 | 720p | $0.10 |
| sora-2-pro | 720p | $0.30 |
| sora-2-pro | 1080p | $0.50 |

---

## 8. Trend Intelligence Module

This module fetches viral videos from social platforms, analyzes what makes them successful, and feeds those insights into the prompt generation pipeline.

### Pipeline Flow

```
Apify Scrapers (fetch viral videos by niche/platform)
    |
    v
Download video temporarily to local storage
    |
    +--> Gemini 3 Pro (creative analysis: hooks, style, pacing, audio)
    +--> Video Intelligence API (structured: shot cuts, objects, text, logos)
    |
    v
Aggregate insights across top N videos
    |
    v
Trend-Informed Prompt Enhancer
    (modifies shot plans, camera LoRA selections, color palettes, pacing)
    |
    v
Delete temporary video files (keep only analysis JSON)
```

### 8.1 Data Sources — Apify Scrapers

Official TikTok and Meta APIs do not provide trending content discovery for commercial use. Apify scrapers are the practical, cost-effective approach. They scrape only publicly visible data.

| Scraper | Platform | Data Returned | Cost |
|---------|----------|--------------|------|
| `apidojo/tiktok-scraper` | TikTok | Views, likes, shares, comments, video URL, hashtags, audio, creator data | ~$0.30/1K posts |
| `apify/instagram-reel-scraper` | Instagram Reels | Views, likes, comments, video URL, caption, hashtags, audio | ~$2.60/1K results |
| `apify/facebook-posts-scraper` | Facebook | Reactions, shares, comments, video URL, caption | ~$2.00/1K results |

**Supplementary:** Google Trends API (free, alpha) for rising topic context and search interest data.

### 8.2 Video Analysis

#### A. Gemini 3 Pro — Creative/Stylistic Analysis

Accepts native video input (not frame-by-frame). Extracts structured JSON covering 8 dimensions:

- Hook analysis (first 1–2 seconds): what visual element stops the scroll, camera angle, text overlay technique
- Visual style: color palette, lighting setup, camera lens feel, overall aesthetic
- Camera work: shot types, movements, transitions, average shot duration
- Pacing: tempo, energy curve, number of cuts, total duration
- Audio: music genre/tempo, sound effects, voice-over tone, audio-visual sync moments
- Content structure: hook-setup-payoff pattern, transformation, tutorial format
- Product presentation: how product is introduced, features highlighted, time to first appearance
- Engagement drivers: shareability factor, emotional trigger, call to action

**Cost:** ~$0.015 per 15-second video (258 tokens/second input rate). Extremely cost-effective.

#### B. Google Video Intelligence API — Structured Technical Analysis

Specialized ML models providing precise, quantitative data:

| Feature | What It Detects | Why It Matters |
|---------|----------------|---------------|
| SHOT_CHANGE_DETECTION | Frame boundaries between cuts | Calculates exact pacing (cuts per minute) |
| LABEL_DETECTION | Objects, scenes, actions in video | Identifies subjects and props in viral content |
| TEXT_DETECTION | On-screen text and overlays | Captures CTAs, titles, caption style patterns |
| OBJECT_TRACKING | Moving objects through frames | Tracks product visibility duration |
| LOGO_DETECTION | Brand logos in video | Identifies brand placement patterns |

**Cost:** 1,000 minutes free/month, then $0.10/minute. Analyzing 50 fifteen-second videos = ~12.5 minutes (well within free tier).

### 8.3 Insight → Prompt Pipeline

Analysis outputs directly modify the prompt generation system:

| Insight | What It Modifies | Example |
|---------|-----------------|---------|
| Hook style: crash zoom | Camera LoRA for Shot 1 | Dolly-In at 0.9 strength, dramatic close-up opening |
| Color palette: warm amber | Lighting directives in all prompts | Warm side-lighting at 3200K, dark moody background |
| Pacing: 1.5s avg shot duration | Shot count in plan | 8–10 shots for 15s video (vs default 4–5) |
| Audio: upbeat electronic | Audio directives (Veo/Sora) | Energetic electronic beat, bass drop at 0:05 |
| Structure: hook → details → hero | Shot template override | Match exact viral content structure |
| Driver: satisfying transformation | Key message emphasis | Transformation moment as climax shot |

### 8.4 Monthly Cost Estimates

| Usage | TikTok (Apify) | Instagram (Apify) | Video Analysis (Gemini) | Video Intelligence | Google Trends | Total |
|-------|---------------|-------------------|------------------------|-------------------|---------------|-------|
| Light (50 vids/week) | ~$0.06 | ~$0.52 | ~$3.00 | Free tier | Free | ~$3.58 |
| Medium (200 vids/week) | ~$0.24 | ~$2.08 | ~$12.00 | ~$2.00 | Free | ~$16.32 |
| Heavy (500 vids/week) | ~$0.60 | ~$5.20 | ~$30.00 | ~$5.00 | Free | ~$40.80 |

---

## 9. Frontend Screens

### Architecture: Next.js App Router

All screens map to route segments in the `app/` directory. Server Components are the default — use `"use client"` only where interactivity requires it (forms, WebSocket listeners, drag-and-drop). Data fetching pattern: Server Components handle initial data loads (project list, trend data); TanStack Query v5 handles all client-side data fetching (polling APIs, job status, generation progress). TanStack Query uses `isPending` (not `isLoading`), `gcTime` (not `cacheTime`), and `HydrationBoundary` for SSR prefetching.

| Screen | Route | Component Strategy |
|--------|-------|-------------------|
| Trend Browser | `app/trends/page.tsx` | Server Component for initial trend data; `"use client"` for filters, search, and "Analyze" actions |
| Creative Brief | `app/brief/page.tsx` | `"use client"` — interactive form with file uploads and trend auto-population |
| Shot Planner | `app/planner/page.tsx` | `"use client"` — drag-and-drop reordering, editable prompts, LoRA sliders |
| Progress Monitor | `app/progress/page.tsx` | `"use client"` — WebSocket for ComfyUI, TanStack Query polling for cloud API status |
| Output Gallery | `app/gallery/page.tsx` | Server Component for initial load; `"use client"` for video playback and regenerate actions |

### Screen 1: Trend Browser

A new screen that lets users explore viral content before creating their own.

**Inputs:**

- Niche / category (dropdown: beauty, food, tech, fashion, fitness, etc.)
- Platform (TikTok, Instagram Reels, Facebook)
- Time range (last 24h, 7 days, 30 days)
- Region (country selector)
- Hashtag filter (optional, comma-separated)
- Minimum views threshold (slider: 100K, 500K, 1M, 5M+)

**Outputs (scrollable grid):**

- Thumbnail + play preview for each viral video
- Metrics: view count, likes, shares, engagement rate
- Creator handle and follower count
- Hashtags and duration
- "Analyze" button per video → runs Gemini + Video Intelligence analysis
- "Analyze Top 10" button → batch analysis with aggregated insights panel
- "Use as Reference" button → feeds insights into Creative Brief form

### Screen 2: Creative Brief Form

Captures all information needed to plan the content. Fields include: project name, content type, target platform, subject/product description, reference image uploads, style/mood, duration target, audio needs, key message/CTA, tool preference (auto/LTX-only/cloud-only), and optional budget limit.

If trend analysis was performed, "Trend Recommendations" auto-populate relevant fields (color palette, pacing, hook style) that the user can accept or override.

### Screen 3: Shot Planner

Displays the AI-generated shot plan as editable cards. Each card shows: shot name/type, duration, tool assignment (LTX/Veo/Sora) with override dropdown, generated prompt (editable), camera LoRA selection and strength slider (LTX shots), reference image thumbnail, transition type to next shot, and collapsible technical parameters.

Actions: reorder shots via drag-and-drop, add/remove shots, regenerate prompt per shot, "Start Generation" button.

### Screen 4: Progress Monitor

Real-time view: overall progress bar, per-shot status (pending → generating with % → complete with thumbnail), estimated time remaining, live WebSocket updates from ComfyUI, polling indicators for cloud APIs, error display with retry button, and cancel button.

### Screen 5: Output Gallery

Displays final concatenated video (playable in browser), individual shot clips with download buttons, generated reference images, "Download All" (ZIP) and "Download Final Video" (MP4) buttons, per-shot "Regenerate" button, and "New Project" button.

---

## 10. Pipeline Orchestrator — Core Logic

The orchestrator is the heart of the system. It takes a project with a confirmed shot plan and executes each shot in sequence, handling transitions automatically.

### Execution Flow

1. For each shot: check if a reference image is needed and none was provided. If so, generate one via Nano Banana 2 or GPT Image.
2. Generate video for this shot by routing to the correct client (ComfyUI for LTX-2.3, Google for Veo 3.1, OpenAI for Sora 2).
3. Handle transition to next shot: if "last_frame", extract last frame as PNG and pass as next shot input. If "extend", pass the full video for continuation.
4. After all shots complete, concatenate all clips via FFmpeg into the final video (MP4 H.264, web-optimized).

### Multi-Clip Concatenation Strategy

| Transition Type | When to Use | How It Works |
|----------------|------------|-------------|
| Video Extend | Same scene continues | Pass full video to extend endpoint; model continues from last frames |
| Last-Frame Bridge | Scene shift with visual continuity | Extract last frame as PNG → use as image-to-video input for next shot |
| Hard Cut | Intentional scene change | Just cut; plan framing to match aesthetically |

### Tool Selection Logic

| Need | Best Tool | Reason |
|------|----------|--------|
| Free, local, with LoRA control | LTX-2.3 | Camera LoRAs, no cost, fast iteration |
| Synchronized native audio | Veo 3.1 | Best-in-class audio generation |
| Character consistency across shots | Veo 3.1 (with references) | Up to 3 reference images |
| Highest photorealism | Sora 2 Pro or Veo 3.1 Full | Both excel here |
| Quick iteration / drafts | LTX-2.3 | Fastest (local GPU, no queue) |
| Extended single take (>20s) | Veo 3.1 | Scene extension up to 148s |
| Privacy-sensitive content | LTX-2.3 | Fully local processing |

---

## 11. ComfyUI Camera LoRAs

LTX-2.3 has official camera control LoRAs from Lightricks. Key principle: let the LoRA handle camera motion, and use your text prompt to describe what the camera reveals (not the movement itself). No trigger words needed; controlled entirely via LoRA strength.

### 11.1 Official LTX-2 Camera LoRAs

| LoRA | Movement | Strength | Best For |
|------|----------|---------|----------|
| Camera-Control-Dolly-In | Camera pushes toward subject | 0.8–1.0 | Product reveals, dramatic emphasis |
| Camera-Control-Dolly-Out | Camera pulls away from subject | 0.8–1.0 | Scene reveals, context reveal |
| Camera-Control-Dolly-Left | Camera translates left | 0.8–1.0 | Lateral reveals, tracking |
| Camera-Control-Dolly-Right | Camera translates right | 0.8–1.0 | Lateral tracking, exploration |
| Camera-Control-Jib-Up | Camera rises vertically | 0.8–1.0 | Scale reveals, dramatic height |
| Camera-Control-Jib-Down | Camera descends vertically | 0.8–1.0 | Approaching, descending reveals |
| Camera-Control-Static | No camera movement | 0.7–1.0 | Product focus, no distraction |

### 11.2 Content-Type Camera Recommendations

| Content Type | Recommended Sequence |
|-------------|---------------------|
| Product Ads | Dolly-Out (establishing) → Dolly-In (product intro) → Static (detail) → Dolly-Right (in-use) → Dolly-In (texture) → Static (brand) |
| B-Roll | Mix: Dolly-Left/Right (tracking), Jib-Up (environmental), Dolly-In (details), Static (mood) |
| TikTok / Short-form | Dolly-In fast (scroll-stopper hook) → dynamic movements → match Shot 1 framing for loop |
| Animated Shorts | Static or gentle Dolly-In (let animation be the star) → Dolly-Left/Right (scene transitions) |

### 11.3 CivitAI Community LoRAs (Wan2.1/2.2)

Additional camera movements available from CivitAI community, primarily trained for Wan2.1/2.2 models: 360 Orbit (strength 0.9–1.0), Crash Zoom In/Out (0.7–0.9), Crane Up/Down/Overhead, Arc Shot, Face-to-Feet Sweep (0.7–1.0). Check model cards for compatibility with LTX-2.3.

---

## 12. Project Structure

```
content-pipeline/
├── .env                           # API keys and config
├── requirements.txt                # Python dependencies
├── package.json                    # Frontend dependencies
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── models.py                  # SQLAlchemy models
│   ├── database.py                # SQLite connection
│   │
│   ├── api/                       # REST endpoints
│   │   ├── projects.py            # CRUD for projects/briefs
│   │   ├── jobs.py                # Job status, progress, cancel
│   │   └── websocket.py           # Live progress to frontend
│   │
│   ├── pipeline/                  # Core orchestration
│   │   ├── orchestrator.py        # Main pipeline logic
│   │   ├── brief_parser.py        # Brief → shot plan
│   │   ├── prompt_generator.py    # Tool-specific prompts
│   │   └── concatenator.py        # FFmpeg concat + frame extraction
│   │
│   ├── clients/                   # External API clients
│   │   ├── comfyui_client.py      # ComfyUI REST + WebSocket
│   │   ├── google_client.py       # Gemini image + Veo video
│   │   ├── openai_client.py       # GPT Image + Sora
│   │   └── ffmpeg_client.py       # FFmpeg subprocess wrapper
│   │
│   ├── trend_intelligence/        # Trend analysis module
│   │   ├── fetchers/
│   │   │   ├── tiktok_fetcher.py      # Apify TikTok scraper
│   │   │   ├── instagram_fetcher.py   # Apify Instagram scraper
│   │   │   ├── facebook_fetcher.py    # Apify Facebook scraper
│   │   │   └── google_trends.py       # Google Trends API
│   │   ├── analyzers/
│   │   │   ├── gemini_analyzer.py     # Gemini 3 Pro video analysis
│   │   │   ├── video_intelligence.py  # Google Video Intelligence
│   │   │   └── insight_aggregator.py  # Aggregate across videos
│   │   └── prompt_enhancer.py     # Apply trends to prompts
│   │
│   ├── workflows/                 # ComfyUI JSON templates
│   └── skills/                    # Prompt engineering knowledge
│
├── frontend/                      # Next.js 16 + Tailwind v4 + TanStack Query v5
│   ├── app/                      # App Router routes
│   │   ├── layout.tsx            # Root layout (QueryClientProvider, global styles)
│   │   ├── page.tsx              # Home / dashboard
│   │   ├── trends/
│   │   │   └── page.tsx          # Trend Browser screen
│   │   ├── brief/
│   │   │   └── page.tsx          # Creative Brief Form screen
│   │   ├── planner/
│   │   │   └── page.tsx          # Shot Planner screen
│   │   ├── progress/
│   │   │   └── page.tsx          # Progress Monitor screen
│   │   └── gallery/
│   │       └── page.tsx          # Output Gallery screen
│   ├── components/               # Shared UI components
│   └── lib/                      # API clients, query utilities, TanStack Query hooks
│
└── output/{project_id}/           # Generated content
    ├── images/  clips/  frames/  final/
```

---

## 13. Configuration (.env)

```env
# ComfyUI (Local)
COMFYUI_URL=http://localhost:8188
COMFYUI_OUTPUT_DIR=C:/ComfyUI/output

# Google APIs
GEMINI_API_KEY=your-gemini-api-key
GCS_BUCKET=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# OpenAI APIs
OPENAI_API_KEY=sk-your-openai-key

# Trend Intelligence
APIFY_API_TOKEN=your-apify-token
TREND_DEFAULT_REGION=us
TREND_DEFAULT_TIME_RANGE=7d
TREND_MIN_VIEWS=100000
TREND_MAX_VIDEOS_PER_FETCH=50
TREND_ANALYSIS_MODEL=gemini-3-pro

# Pipeline Settings
OUTPUT_DIR=./output
DEFAULT_VIDEO_TOOL=ltx
DEFAULT_IMAGE_TOOL=nano_banana
MAX_CLOUD_BUDGET_PER_PROJECT=20.00
LTX_CFG=3.5
LTX_STEPS=40
```

---

## 14. Dependencies

### Python (requirements.txt)

```
fastapi>=0.110.0      uvicorn>=0.29.0       httpx>=0.27.0
websockets>=12.0      openai>=1.60.0        google-genai>=1.5.0
google-cloud-storage>=2.16.0                google-cloud-videointelligence>=2.13.0
sqlalchemy>=2.0.0     pydantic>=2.6.0       pydantic-settings>=2.2.0
python-multipart>=0.0.9  aiofiles>=23.2.1   pillow>=10.2.0
apify-client>=1.7.0
```

### Node.js (frontend)

```
next ^16.0   react ^19.0   react-dom ^19.0
tailwindcss ^4.0   @tanstack/react-query ^5.0   lucide-react ^0.344
```

**Notes:** `react-router-dom` is dropped — Next.js App Router provides built-in file-system routing. Vite is dropped — Turbopack is the default bundler in Next.js 16. Tailwind v4 uses CSS-first configuration (`@import "tailwindcss"` in CSS, no `tailwind.config.js`).

### System

- FFmpeg (must be on PATH)
- ComfyUI (running on localhost:8188)
- Node.js 20+
- Python 3.11+

---

## 15. Error Handling

| Error | Detection | Recovery |
|-------|----------|---------|
| ComfyUI not running | Connection refused on 8188 | Show "Start ComfyUI" instruction |
| ComfyUI out of VRAM | WebSocket error during sampling | Reduce resolution, retry |
| Google API rate limit | 429 response | Exponential backoff (10s, 20s, 40s) |
| OpenAI rate limit | 429 response | Exponential backoff |
| Sora generation failed | status: "failed" on poll | Show error, offer retry with modified prompt |
| Veo generation timeout | >5 min no completion | Show timeout, offer retry |
| FFmpeg concat fails | Non-zero exit code | Check resolution mismatch, normalize, retry |
| Budget exceeded | Cost > MAX_CLOUD_BUDGET | Pause, show cost, ask user to approve or switch to LTX |
| Invalid API key | 401 response | Show "Check API key" in settings |
| GCS bucket missing | Storage error from Veo | Show bucket setup instructions |
| Apify scraper fails | Actor run error | Retry with reduced maxItems, show error |

---

## 16. Legal and Terms of Service

- **Apify scrapers:** Scrape only publicly visible data. Pipeline downloads videos temporarily for analysis then deletes them. Only analysis JSON is stored, not video files.
- **Google APIs:** All Google APIs used under standard commercial terms with API key authentication.
- **Video Intelligence API:** Requires uploading video to GCS for analysis. Videos deleted from GCS after analysis completes.
- **Data retention:** Auto-delete downloaded viral videos after analysis (default: delete immediately after Gemini analysis, keep only JSON insights).
- **Copyright:** Generated content uses AI models; users are responsible for ensuring their generated content does not infringe on third-party rights.

---

## 17. Future Enhancements (v2+)

- Prompt memory: save successful prompts and reuse/remix them
- A/B testing: generate 2 versions of each shot, let user pick the better one
- Audio post-processing: add background music tracks, normalize audio levels
- Direct social publishing: integrate TikTok/Instagram/YouTube APIs for one-click publish
- LoRA training: train custom product/character LoRAs from user images
- Template library: pre-built project templates (product launch, unboxing, tutorial, etc.)
- Batch processing: queue multiple projects, run overnight
- Cost estimator: show estimated cloud costs before generation starts
- Mobile companion: preview and approve shots on phone

---

## 18. Open Questions

| # | Question | Options |
|---|---------|---------|
| 1 | GCS bucket for Veo: require user setup or proxy transparently? | User setup (simpler) vs auto-proxy (better UX) |
| 2 | Workflow JSON templates: export from user ComfyUI or provide setup wizard? | Capture tool vs pre-built wizard |
| 3 | LLM-powered prompt gen: integrate Claude API for dynamic prompts? | Higher quality + latency/cost vs rule-based templates |
| 4 | Concurrent generation: parallel shots or strictly sequential? | Parallel (faster, higher resource) vs sequential (simpler) |
| 5 | Quality verification: auto blur/artifact detection before concat? | Automated check vs user review |
| 6 | Trend video storage: local temp for Gemini, GCS for Video Intelligence, or both? | Local only vs GCS only vs both |
| 7 | Trend analysis trigger: auto per project or manual from Trend Browser? | Auto (30s latency) vs manual (user-initiated) |
