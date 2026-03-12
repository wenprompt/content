from datetime import datetime

from pydantic import BaseModel, ConfigDict

# --- Project ---

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    content_type: str = "short_clip"
    target_platform: str = "tiktok"
    style_mood: str = ""
    duration_target: int = 15
    audio_needs: str = ""
    key_message: str = ""
    tool_preference: str = "auto"
    budget_limit: float = 20.0


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content_type: str | None = None
    target_platform: str | None = None
    style_mood: str | None = None
    duration_target: int | None = None
    audio_needs: str | None = None
    key_message: str | None = None
    tool_preference: str | None = None
    budget_limit: float | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    content_type: str
    target_platform: str
    style_mood: str
    duration_target: int
    audio_needs: str
    key_message: str
    tool_preference: str
    budget_limit: float
    reference_images: str
    status: str
    created_at: datetime
    updated_at: datetime
    shots: list["ShotResponse"] = []


# --- Shot ---

class ShotCreate(BaseModel):
    name: str = ""
    shot_type: str = "text_to_video"
    tool: str = "ltx"
    prompt: str = ""
    negative_prompt: str = ""
    duration: float = 5.0
    width: int = 1920
    height: int = 1080
    fps: int = 24
    cfg: float = 3.5
    steps: int = 40
    seed: int = -1
    lora_name: str = ""
    lora_strength: float = 0.9
    transition_type: str = "last_frame"
    reference_image: str = ""


class ShotUpdate(BaseModel):
    name: str | None = None
    shot_type: str | None = None
    tool: str | None = None
    prompt: str | None = None
    negative_prompt: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    cfg: float | None = None
    steps: int | None = None
    seed: int | None = None
    lora_name: str | None = None
    lora_strength: float | None = None
    transition_type: str | None = None
    reference_image: str | None = None


class ShotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    order_index: int
    name: str
    shot_type: str
    tool: str
    prompt: str
    negative_prompt: str
    duration: float
    width: int
    height: int
    fps: int
    cfg: float
    steps: int
    seed: int
    lora_name: str
    lora_strength: float
    transition_type: str
    reference_image: str
    output_path: str
    status: str


class ShotReorder(BaseModel):
    shot_ids: list[str]


# --- Job ---

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: str
    current_shot_index: int
    total_shots: int
    progress: float
    message: str
    error: str
    output_path: str
    created_at: datetime
    completed_at: datetime | None


# --- Trend ---

class TrendFetchRequest(BaseModel):
    platform: str = "tiktok"
    niche: str = ""
    region: str = "us"
    time_range: str = "7d"
    min_views: int = 100000
    max_results: int = 50
    hashtags: list[str] = []


class TrendAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    niche: str
    video_url: str
    video_id: str
    metrics: str
    gemini_analysis: str
    video_intelligence: str
    aggregated_insights: str
    created_at: datetime
