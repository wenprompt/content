import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(50), default="short_clip")
    target_platform: Mapped[str] = mapped_column(String(50), default="tiktok")
    style_mood: Mapped[str] = mapped_column(Text, default="")
    duration_target: Mapped[int] = mapped_column(Integer, default=15)
    audio_needs: Mapped[str] = mapped_column(Text, default="")
    key_message: Mapped[str] = mapped_column(Text, default="")
    tool_preference: Mapped[str] = mapped_column(String(20), default="auto")
    budget_limit: Mapped[float] = mapped_column(Float, default=20.0)
    reference_images: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    shots: Mapped[list["Shot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Shot.order_index"
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), default="")
    shot_type: Mapped[str] = mapped_column(String(50), default="text_to_video")
    tool: Mapped[str] = mapped_column(String(20), default="ltx")
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[float] = mapped_column(Float, default=5.0)
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    fps: Mapped[int] = mapped_column(Integer, default=24)
    cfg: Mapped[float] = mapped_column(Float, default=3.5)
    steps: Mapped[int] = mapped_column(Integer, default=40)
    seed: Mapped[int] = mapped_column(Integer, default=-1)
    lora_name: Mapped[str] = mapped_column(String(255), default="")
    lora_strength: Mapped[float] = mapped_column(Float, default=0.9)
    transition_type: Mapped[str] = mapped_column(String(20), default="last_frame")
    reference_image: Mapped[str] = mapped_column(Text, default="")
    output_path: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")

    project: Mapped["Project"] = relationship(back_populates="shots")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    current_shot_index: Mapped[int] = mapped_column(Integer, default=0)
    total_shots: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    output_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")


class TrendAnalysis(Base):
    __tablename__ = "trend_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    platform: Mapped[str] = mapped_column(String(20))
    niche: Mapped[str] = mapped_column(String(100))
    video_url: Mapped[str] = mapped_column(Text, default="")
    video_id: Mapped[str] = mapped_column(String(255), default="")
    metrics: Mapped[str] = mapped_column(Text, default="{}")
    gemini_analysis: Mapped[str] = mapped_column(Text, default="{}")
    video_intelligence: Mapped[str] = mapped_column(Text, default="{}")
    aggregated_insights: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
