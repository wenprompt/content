from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ComfyUI
    comfyui_url: str = "http://localhost:8188"
    comfyui_output_dir: str = "C:/ComfyUI/output"

    # Google APIs
    gemini_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Trend Intelligence
    apify_api_token: str = ""
    trend_default_regions: str = "sg,us"
    trend_default_time_range: str = "7d"
    trend_min_views: int = 100000
    trend_max_videos_per_fetch: int = 50
    trend_analysis_model: str = "gemini-3-pro"

    # Pipeline
    output_dir: str = "./output"
    default_video_tool: str = "ltx"
    default_image_tool: str = "nano_banana"
    max_cloud_budget_per_project: float = 20.00
    ltx_cfg: float = 3.5
    ltx_steps: int = 40
    brief_parser_provider: str = "gemini"
    brief_parser_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
