# Scripts

## tiktok_remix.py

Scrapes a viral TikTok, analyzes it with Gemini, and recreates it as AI-generated video.
Supports three video generation tools: LTX 2.3 (local), Veo 3.1 (Google cloud), Sora 2 (OpenAI cloud).

### How it works

```
1. SCRAPE    Apify clockworks/tiktok-scraper -> top viral videos by niche + min views
2. DOWNLOAD  yt-dlp saves original to downloads/ and output/{project}/source/
3. ANALYZE   Gemini 3.1 Pro watches the video -> 8-dimension analysis + per-shot breakdown
             (camera movements, durations, style, pacing, transitions)
4. ADAPT     Gemini rewrites shot descriptions for the target style/character
             while keeping same structure, camera, duration, transition_type
5. PLAN      prompt_enhancer maps analysis -> ShotPlans with smart tool routing:
               --tool auto (default):
                 - Veo 3.1 for most shots (best multi-shot consistency + native audio)
                 - Sora 2 for animation keywords, complex physics, atmospheric B-roll
               --tool ltx/veo/sora: force all shots to one tool
             Duration clamped per tool: LTX 2-20s, Veo 4/6/8s, Sora 4/8/12s
6. GENERATE  For each shot (orchestrator handles all three tools):
               CHAINING (pre-dispatch, for I2V-capable tools: ltx, veo):
                 - hard_cut: Nano Banana 2 / GPT-4o generates a fresh reference image
                 - last_frame: ffmpeg extracts last frame from previous shot
               DISPATCH:
                 - tool=ltx  -> ComfyUI API -> LTX-2.3 (local GPU, I2V with camera LoRA)
                 - tool=veo  -> Google Gemini API -> Veo 3.1 (cloud, I2V with ref image)
                 - tool=sora -> OpenAI API -> Sora 2 (cloud, T2V only)
7. CONCAT    ffmpeg normalizes all shots (same res/fps) -> concatenates -> final.mp4
```

### Tool comparison

```
           | LTX 2.3          | Veo 3.1           | Sora 2
-----------+-------------------+-------------------+------------------
Cost       | Free (local GPU)  | ~$0.75/sec        | ~$0.20-0.60/shot
Speed      | ~20-40s/shot      | ~60-120s/shot     | ~60-90s/shot
Duration   | 2-20s             | 4, 6, or 8s       | 4, 8, or 12s
Resolution | Up to 1280x720    | Up to 4K          | Up to 1080p
Audio      | Generated (basic) | Native lip-sync   | Synchronized
I2V        | Yes (LoRA-based)  | Yes (ref image)   | No (T2V only)
Best for   | Prototyping, free | Multi-shot ads     | Stylized/physics
```

### Commands

```bash
# Auto tool routing (Veo/Sora based on content)
uv run python -m scripts.tiktok_remix --niche "satisfying" --style "3D Pixar" --tool auto

# Force a specific tool
uv run python -m scripts.tiktok_remix --niche "food" --style "cinematic" --tool veo
uv run python -m scripts.tiktok_remix --niche "anime edit" --style "anime, cel-shaded" --tool sora
uv run python -m scripts.tiktok_remix --niche "fashion" --style "editorial" --tool ltx

# Use a specific URL with custom character + story
uv run python -m scripts.tiktok_remix \
  --url "https://tiktok.com/@user/video/123" \
  --style "anime animation, vibrant colors" \
  --character "An anime hero with spiky black hair and blue eyes" \
  --story "He parkours across rooftops at sunset" \
  --tool auto \
  --max-shots 6 \
  --generate

# All options
uv run python -m scripts.tiktok_remix \
  --niche "pets"           # search term for TikTok scraper
  --url "https://..."      # direct URL (skips scraping)
  --min-views 1000000      # minimum view count filter
  --pick 2                 # pick 2nd result (1-indexed)
  --style "3D Pixar"       # animation style
  --character "a cute cat" # character description
  --story "cat chases..."  # narrative ground truth
  --tool auto              # auto | ltx | veo | sora
  --max-shots 6            # cap number of shots
  --generate               # auto-start generation (needs server running)
```

### Current limitations

- **"Adaptation" != "recreation"**: step 4 rewrites descriptions for a new product/style,
  it does NOT faithfully reproduce the original scene.
- **Reference image quality is key**: LTX/Veo follow the reference image closely. If Nano
  Banana generates a bad first frame, the whole shot is bad.
- **LTX can't do text**: any text/logos/labels in prompts get mangled.
- **Character consistency across hard_cuts**: each hard_cut generates a new reference image,
  so the character may look different between shots. last_frame chaining keeps consistency.
- **Sora has no I2V**: last_frame transitions for Sora shots rely on prompt continuity only,
  not visual chaining from the previous frame.
- **Veo duration is discrete**: only 4, 6, or 8 seconds. Durations are snapped to nearest.

### Output structure

```
output/{project_id}/
├── source/
│   ├── original.mp4      <- the scraped TikTok video
│   ├── analysis.json     <- Gemini's 8-dimension analysis
│   └── adapted.json      <- rewritten shot descriptions
├── references/
│   ├── ref_00.png         <- generated ref images (hard_cut shots)
│   ├── lastframe_05.png   <- extracted last frames (last_frame shots)
│   └── ...
├── shots/
│   ├── shot_00.mp4        <- individual generated clips
│   └── ...
└── final/
    └── final.mp4          <- concatenated final video
```

---

## Product B-roll with your own image (REST API)

For product B-roll using your own reference image, use the REST API directly.
Server must be running: `uv run python -m backend.main`

### Quick start: single product shot with your own image

```bash
# 1. Create a project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Product B-roll",
    "content_type": "b_roll",
    "target_platform": "tiktok",
    "style_mood": "clean minimalist",
    "tool_preference": "ltx"
  }'
# Returns: {"id": "abc-123", ...}

# 2. Upload your product image as reference
curl -X POST http://localhost:8000/api/projects/abc-123/upload \
  -F "file=@my_product.png"

# 3. Add a shot using your image as reference
curl -X POST http://localhost:8000/api/projects/abc-123/shots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hero Reveal",
    "shot_type": "image_to_video",
    "tool": "ltx",
    "prompt": "A sleek white bottle on a marble surface, soft studio lighting, gentle steam rising, the camera slowly pushes in revealing product details",
    "duration": 5.0,
    "width": 768,
    "height": 1344,
    "reference_image": "output/abc-123/references/my_product.png",
    "lora_name": "ltx-camera-dolly-in.safetensors",
    "lora_strength": 0.85,
    "transition_type": "hard_cut"
  }'

# 4. Add more shots (last_frame chains from previous shot)
curl -X POST http://localhost:8000/api/projects/abc-123/shots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Orbit",
    "shot_type": "image_to_video",
    "tool": "ltx",
    "prompt": "Continuing the same scene, the camera orbits around the bottle revealing the label, soft bokeh background",
    "duration": 5.0,
    "width": 768,
    "height": 1344,
    "transition_type": "last_frame"
  }'

# 5. Generate all shots + concat
curl -X POST http://localhost:8000/api/projects/abc-123/generate

# 6. Poll status
curl http://localhost:8000/api/jobs/{job_id}
```

### Multi-shot product B-roll (auto-planned)

Use the brief parser to auto-plan shots from a description:

```bash
# Create project with content_type and tool_preference
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sneaker Ad",
    "description": "Hero product reveal for a new running shoe. Show it from multiple angles with dramatic lighting. Focus on the sole technology and breathable mesh.",
    "content_type": "product_ad",
    "target_platform": "tiktok",
    "style_mood": "dark dramatic, studio lighting",
    "duration_target": 15,
    "tool_preference": "ltx"
  }'

# Parse brief into shots (Gemini plans the shot list)
curl -X POST http://localhost:8000/api/projects/abc-123/parse-brief

# Upload your product image (used as reference for hard_cut shots)
curl -X POST http://localhost:8000/api/projects/abc-123/upload \
  -F "file=@sneaker.png"

# Generate
curl -X POST http://localhost:8000/api/projects/abc-123/generate
```

### Camera LoRAs for LTX (use in lora_name field)

```
ltx-camera-dolly-in.safetensors     <- push in / zoom in
ltx-camera-dolly-out.safetensors    <- pull out / zoom out
ltx-camera-dolly-left.safetensors   <- pan left
ltx-camera-dolly-right.safetensors  <- pan right / tracking
ltx-camera-jib-up.safetensors       <- crane up / tilt up
ltx-camera-jib-down.safetensors     <- crane down / tilt down
(no LoRA)                           <- static shot
```

---

## meiji_milk_remix.py

One-off script that remixes the Coca-Cola ad (YouTube) for fresh milk.
Same pipeline as tiktok_remix.py but hardcoded to a specific video URL.
Mostly superseded by tiktok_remix.py which is more flexible.

```bash
uv run python -m scripts.meiji_milk_remix
```
