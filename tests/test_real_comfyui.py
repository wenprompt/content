"""Real ComfyUI integration tests — require ComfyUI running on localhost:8188.

Run with: uv run pytest tests/test_real_comfyui.py -v -s
"""

import asyncio
from pathlib import Path

import pytest

from backend.clients.comfyui_client import ComfyUIClient

COMFYUI_URL = "http://127.0.0.1:8188"
# Use coca.png as the standard test image (committed to repo)
TEST_IMG = Path(__file__).resolve().parent.parent / "docs" / "coca.png"


@pytest.fixture
def client() -> ComfyUIClient:
    return ComfyUIClient(COMFYUI_URL)


async def _check_comfyui() -> bool:
    c = ComfyUIClient(COMFYUI_URL)
    return await c.is_available()


pytestmark = pytest.mark.skipif(
    not asyncio.run(_check_comfyui()),
    reason="ComfyUI not running on localhost:8188",
)


class TestRealTextToVideo:
    async def test_t2v_generates_video(self, client: ComfyUIClient) -> None:
        """Generate a short T2V clip and verify output."""
        progress_steps: list[tuple[int, int]] = []

        async def on_progress(step: int, total: int) -> None:
            progress_steps.append((step, total))
            print(f"  T2V progress: {step}/{total}")

        print("\n--- Starting T2V generation (short clip) ---")
        result = await client.generate_video(
            prompt_text=(
                "A red Coca-Cola can sits on a wooden table, condensation "
                "droplets forming on the cold metal surface. Warm sunlight "
                "streams through a window, casting soft shadows. Steam rises "
                "gently from a freshly poured glass nearby. Product shot, "
                "cinematic lighting, shallow depth of field."
            ),
            negative_prompt=(
                "low quality, worst quality, blurry, distorted, "
                "watermark, text, ugly, deformed"
            ),
            width=768,
            height=512,
            num_frames=121,  # ~5s at 24fps
            seed=42,
            fps=24,
            progress_callback=on_progress,
        )
        print(f"  Output: {result}")

        assert result.exists(), f"Output file not found: {result}"
        assert result.stat().st_size > 1000, "Output file too small"
        assert len(progress_steps) > 0, "No progress callbacks received"
        print(f"  File size: {result.stat().st_size:,} bytes")
        print(f"  Progress steps: {len(progress_steps)}")


class TestRealGuideFrames:
    async def test_first_frame_guide(self, client: ComfyUIClient) -> None:
        """Generate video with first frame guide from coca.png."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"

        progress_steps: list[tuple[int, int]] = []

        async def on_progress(step: int, total: int) -> None:
            progress_steps.append((step, total))
            print(f"  Guide progress: {step}/{total}")

        print("\n--- Starting guide frame generation (first frame) ---")
        result = await client.generate_video(
            prompt_text=(
                "A Coca-Cola can slowly rotates on a glossy surface, "
                "revealing the iconic red label and white script logo. "
                "Condensation droplets glisten under warm studio lighting, "
                "smooth slow rotation, product commercial, cinematic"
            ),
            width=768,
            height=512,
            num_frames=121,
            seed=42,
            fps=24,
            guide_frames=[
                (str(TEST_IMG), 0, 1.0),  # first frame
            ],
            progress_callback=on_progress,
        )
        print(f"  Output: {result}")

        assert result.exists(), f"Output file not found: {result}"
        assert result.stat().st_size > 1000, "Output file too small"
        assert len(progress_steps) > 0, "No progress callbacks received"
        print(f"  File size: {result.stat().st_size:,} bytes")
        print(f"  Progress steps: {len(progress_steps)}")


class TestRealImageToVideo:
    async def test_i2v_generates_video(self, client: ComfyUIClient) -> None:
        """Generate I2V from coca.png and verify output."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"

        progress_steps: list[tuple[int, int]] = []

        async def on_progress(step: int, total: int) -> None:
            progress_steps.append((step, total))
            print(f"  I2V progress: {step}/{total}")

        print("\n--- Starting I2V generation (coca.png) ---")
        result = await client.generate_video(
            prompt_text=(
                "A hand reaches in and picks up the Coca-Cola can from the "
                "table. The can tilts as it's lifted, condensation dripping "
                "down the side. Smooth motion, product commercial style, "
                "warm lighting, shallow depth of field."
            ),
            negative_prompt=(
                "low quality, worst quality, blurry, distorted, "
                "watermark, text, ugly, deformed"
            ),
            width=768,
            height=512,
            num_frames=121,  # ~5s at 24fps
            seed=123,
            fps=24,
            reference_image=str(TEST_IMG),
            progress_callback=on_progress,
        )
        print(f"  Output: {result}")

        assert result.exists(), f"Output file not found: {result}"
        assert result.stat().st_size > 1000, "Output file too small"
        assert len(progress_steps) > 0, "No progress callbacks received"
        print(f"  File size: {result.stat().st_size:,} bytes")
        print(f"  Progress steps: {len(progress_steps)}")
