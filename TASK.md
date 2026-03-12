# Content Pipeline — Backend Tasks

## Pre-Phase: Skill Updates
- [x] Update `.claude/skills/ltx-video/references/camera-loras.md` — replace generic LoRA names with actual installed filenames
- [x] Update `.claude/skills/ltx-video/references/camera-loras.md` — add IC LoRA section with 5 installed IC LoRAs
- [x] Update `.claude/skills/ltx-video/references/camera-loras.md` — add Distilled LoRA section
- [x] Update `.claude/skills/ltx-video/SKILL.md` — update Quick Reference table with actual filenames
- [x] Deep research on all installed LoRAs — update skill files with comprehensive usage guides (camera LoRA prompting, IC-LoRA preprocessing/nodes, distilled pipeline params, stacking compatibility matrix, ComfyUI node reference)

## Phase 1: Foundation
- [x] `uv add` all core dependencies (fastapi, uvicorn, sqlalchemy, aiosqlite, pydantic-settings, httpx, python-multipart, aiofiles, pillow)
- [x] Create directory structure (backend/, backend/api/, backend/pipeline/, backend/clients/, backend/trend_intelligence/, backend/trend_intelligence/fetchers/, backend/trend_intelligence/analyzers/, backend/workflows/, output/)
- [x] Create `.env` with all config keys + `.env.example` with placeholders
- [x] Create `backend/config.py` — Settings class with pydantic-settings, SettingsConfigDict, all PRD config fields
- [x] Create `backend/database.py` — async engine (aiosqlite), async_sessionmaker, get_db() dependency, init_db()
- [x] Create `backend/models.py` — Project, Shot, Job, TrendAnalysis models (SQLAlchemy 2.0 Mapped[] types)
- [x] Create `backend/schemas.py` — Pydantic v2 request/response schemas (ProjectCreate/Response, ShotCreate/Response, JobResponse)
- [x] Create `backend/main.py` — FastAPI app with lifespan (init DB, httpx client, job queue), CORS middleware, /health endpoint
- [x] Replace root `main.py` — thin uvicorn launcher
- [x] **TEST**: GET /health returns 200, GET /docs loads Swagger, DB file created

## Phase 2: REST API
- [x] Create `backend/api/projects.py` — APIRouter: POST/GET/PUT/DELETE /api/projects, GET /api/projects/{id} with shots
- [x] Create `backend/api/jobs.py` — APIRouter: POST /api/projects/{id}/generate, GET /api/jobs/{id}, POST /api/jobs/{id}/cancel
- [x] Add shot endpoints in projects.py — POST/PUT/DELETE shots, PUT reorder
- [x] Add file upload endpoint — POST /api/projects/{id}/upload (reference images)
- [x] Register all routers in backend/main.py
- [x] **TEST**: Full CRUD via Swagger — create project, add shots, trigger generate, check job status

## Phase 3: WebSocket + Job Worker + FFmpeg
- [x] Create `backend/api/websocket.py` — ConnectionManager class, /ws/{client_id} endpoint
- [x] Create `backend/clients/ffmpeg_client.py` — extract_last_frame(), concatenate_videos(), normalize_video(), get_video_info()
- [x] Create `backend/pipeline/orchestrator.py` — process_job_queue() background task (stubbed with sleep per shot)
- [x] Wire job queue: generate endpoint -> queue -> worker -> WebSocket progress -> status update
- [x] **TEST**: WebSocket receives progress messages, job completes after stub delay

## Phase 4: ComfyUI Client ✅
- [x] `uv add websockets`
- [x] Create `backend/clients/comfyui_client.py` — ComfyUIClient with programmatic workflow building (no JSON templates)
- [x] Create `backend/pipeline/concatenator.py` — concatenate_project() using FFmpeg client
- [x] Update orchestrator — route tool="ltx" shots through ComfyUI client with real progress
- [x] **TEST**: T2V generates real 5s video (121 frames, 768x512) ✅
- [x] **TEST**: I2V generates real 5s video from luffy.png (121 frames, 768x512) ✅
- [x] 110 unit/integration tests pass, ruff clean, mypy clean

### Implementation Notes (for future reference)

**Workflows are built programmatically** in `comfyui_client.py._build_workflow()` — NOT from static JSON templates. The `backend/workflows/` directory is unused. Reason: conditional node inclusion (T2V vs I2V), LoRA chaining, and parameterization are much cleaner in Python.

**T2V and I2V MUST use separate workflow structures.** ComfyUI API has NO native bypass/mute support (GitHub Issue #4028). A `LoadImage` node with a nonexistent file will cause a 400 validation error even if `LTXVImgToVideoInplace` has `bypass=True`. For T2V, image nodes are excluded entirely from the workflow dict.

**Two-stage distilled pipeline:** Stage 1 (half-res, 8 steps, `euler_ancestral_cfg_pp`) → `LTXVLatentUpsampler` 2x → Stage 2 (full-res, 4 steps/3 sigmas, `euler_cfg_pp`). CFG=1 always. Uses `ManualSigmas` (NOT `LTXVScheduler`), `SamplerCustomAdvanced` + `CFGGuider` (NOT `SamplerCustom`), `VAEDecodeTiled` (NOT `VAEDecode`).

**Image upload:** `POST /upload/image` with `subfolder=""` (empty string, NOT `"input"`). Using `"input"` puts file at `input/input/` which `LoadImage` cannot resolve.

**History parsing:** ComfyUI returns video files under `"images"` key (NOT `"videos"` or `"gifs"`).

**Native audio:** Pipeline includes `LTXVEmptyLatentAudio` → `LTXVConcatAVLatent` → `LTXVSeparateAVLatent` → `LTXVAudioVAEDecode` for LTX-2.3's native audio generation.

**Reference workflows:** `docs/video_ltx2_3_t2v.json` and `docs/video_ltx2_3_i2v.json` contain the original ComfyUI API-format templates used as reference for building the programmatic workflow. These are documentation only, not loaded at runtime.

## Phase 5: Cloud API Clients
- [ ] `uv add google-genai google-cloud-storage openai`
- [ ] Create `backend/clients/google_client.py` — GoogleClient: generate_image() (Gemini flash), generate_video() (Veo 3.1 with polling)
- [ ] Create `backend/clients/openai_client.py` — OpenAIClient: generate_image() (gpt-image-1), generate_video() (Sora 2 with polling)
- [ ] Update orchestrator — route by shot.tool (ltx->ComfyUI, veo->Google, sora->OpenAI)
- [ ] Initialize all clients in lifespan via app.state
- [ ] **TEST**: Mixed project with shots across all 3 tools -> all generate -> concatenated

## Phase 6: Brief Parser + Prompt Generator
- [ ] Create `backend/pipeline/brief_parser.py` — parse_brief() using Gemini to generate shot plan from project description
- [ ] Create `backend/pipeline/prompt_generator.py` — generate_tool_prompt() for LTX/Veo/Sora specific prompts + negative prompts
- [ ] Add endpoint POST /api/projects/{id}/plan — calls brief parser, saves shots to DB
- [ ] **TEST**: Brief "15s product ad for earbuds" -> auto-generated shots with correct tools, LoRAs, transitions

## Phase 7: Trend Intelligence
- [ ] `uv add apify-client google-cloud-videointelligence`
- [ ] Create `backend/trend_intelligence/fetchers/tiktok_fetcher.py` — Apify TikTok scraper
- [ ] Create `backend/trend_intelligence/fetchers/instagram_fetcher.py` — Apify Instagram scraper
- [ ] Create `backend/trend_intelligence/fetchers/facebook_fetcher.py` — Apify Facebook scraper
- [ ] Create `backend/trend_intelligence/fetchers/google_trends.py` — Google Trends API
- [ ] Create `backend/trend_intelligence/analyzers/gemini_analyzer.py` — Gemini 3 Pro video analysis (8 dimensions)
- [ ] Create `backend/trend_intelligence/analyzers/video_intelligence.py` — Google Video Intelligence API
- [ ] Create `backend/trend_intelligence/analyzers/insight_aggregator.py` — aggregate patterns across N videos
- [ ] Create `backend/trend_intelligence/prompt_enhancer.py` — apply trend insights to shot plans
- [ ] Create `backend/api/trends.py` — POST /fetch, POST /analyze, GET /insights, POST /enhance
- [ ] Integrate trend insights into brief_parser.py
- [ ] **TEST**: Fetch TikTok trends -> analyze -> insights modify shot plan
