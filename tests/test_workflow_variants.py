"""Comprehensive LTX-2.3 workflow variant tests against real ComfyUI.

Exercises every workflow variant (T2V, I2V, FL2V, FML2V, all camera LoRAs,
LoRA combos), exports each successful workflow as reference JSON, and reports results.

Run with: uv run pytest tests/test_workflow_variants.py -v -s
"""

import asyncio
import json
from pathlib import Path

import pytest

from backend.clients.comfyui_client import ComfyUIClient

COMFYUI_URL = "http://127.0.0.1:8188"
TEST_IMG = Path(__file__).resolve().parent.parent / "docs" / "coca.png"
TEST_IMG2 = Path(__file__).resolve().parent.parent / "docs" / "coca2.png"
TEST_AUDIO = Path(__file__).resolve().parent.parent / "docs" / "test_audio.wav"
WORKFLOW_DIR = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "ltx-video"
    / "references"
    / "workflows"
)

# 768x512 at 121 frames (~5s at 24fps) — enough to see camera motion
WIDTH = 768
HEIGHT = 512
NUM_FRAMES = 121
FPS = 24
SEED = 42


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


async def _run_variant(
    client: ComfyUIClient,
    name: str,
    *,
    prompt_text: str,
    reference_image: str | None = None,
    lora_name: str = "",
    lora_strength: float = 0.9,
    i2v_strength: float = 0.7,
    img_compression: int = 28,
    guide_frames: list[tuple[str, int, float]] | None = None,
    nag_video_cfg: float = 0.0,
    nag_audio_cfg: float = 0.0,
    single_pass: bool = False,
    audio_input: str | None = None,
) -> Path:
    """Build workflow, export JSON, submit to ComfyUI, return output path."""
    progress_steps: list[tuple[int, int]] = []

    async def on_progress(step: int, total: int) -> None:
        progress_steps.append((step, total))
        print(f"  [{name}] progress: {step}/{total}")

    # 1. Build workflow for JSON export (use uploaded filenames for images/audio)
    build_kwargs: dict = dict(
        prompt_text=prompt_text,
        negative_prompt="",
        width=WIDTH,
        height=HEIGHT,
        num_frames=NUM_FRAMES,
        seed=SEED,
        fps=FPS,
        lora_name=lora_name,
        lora_strength=lora_strength,
        i2v_strength=i2v_strength,
        img_compression=img_compression,
        nag_video_cfg=nag_video_cfg,
        nag_audio_cfg=nag_audio_cfg,
        single_pass=single_pass,
    )
    if reference_image:
        build_kwargs["image_filename"] = Path(reference_image).name
    if guide_frames:
        build_kwargs["guide_frames"] = [
            (Path(p).name, idx, s) for p, idx, s in guide_frames
        ]
    if audio_input:
        build_kwargs["audio_filename"] = Path(audio_input).name

    workflow = client._build_workflow(**build_kwargs)

    # 2. Export workflow JSON
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    json_path = WORKFLOW_DIR / f"{name}.json"
    json_path.write_text(json.dumps(workflow, indent=2))
    print(f"  [{name}] exported workflow to {json_path}")

    # 3. Submit to ComfyUI via generate_video()
    gen_kwargs: dict = dict(
        prompt_text=prompt_text,
        width=WIDTH,
        height=HEIGHT,
        num_frames=NUM_FRAMES,
        seed=SEED,
        fps=FPS,
        lora_name=lora_name,
        lora_strength=lora_strength,
        i2v_strength=i2v_strength,
        img_compression=img_compression,
        nag_video_cfg=nag_video_cfg,
        nag_audio_cfg=nag_audio_cfg,
        single_pass=single_pass,
        progress_callback=on_progress,
    )
    if reference_image:
        gen_kwargs["reference_image"] = reference_image
    if guide_frames:
        gen_kwargs["guide_frames"] = guide_frames
    if audio_input:
        gen_kwargs["audio_input"] = audio_input

    print(f"\n--- [{name}] submitting to ComfyUI ---")
    result = await client.generate_video(**gen_kwargs)
    print(f"  [{name}] output: {result} ({result.stat().st_size:,} bytes)")
    print(f"  [{name}] progress steps received: {len(progress_steps)}")

    return result


# ── Test classes ─────────────────────────────────────────────────────


class TestT2VBasic:
    """Text-to-video without LoRAs."""

    async def test_t2v_basic(self, client: ComfyUIClient) -> None:
        """T2V basic — no image, no LoRA."""
        result = await _run_variant(
            client,
            "t2v_basic",
            prompt_text=(
                "A red Coca-Cola can sits on a wooden table, condensation "
                "droplets forming on the cold metal surface. Warm sunlight "
                "streams through a window, casting soft shadows. Product shot, "
                "cinematic lighting, shallow depth of field."
            ),
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestI2VVariants:
    """Image-to-video variants."""

    async def test_i2v_basic(self, client: ComfyUIClient) -> None:
        """I2V basic — coca.png, default CRF 28."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_basic",
            prompt_text=(
                "A hand reaches in and picks up the Coca-Cola can from the "
                "table. The can tilts as it is lifted, condensation dripping "
                "down the side. Smooth motion, product commercial style, "
                "warm lighting, shallow depth of field."
            ),
            reference_image=str(TEST_IMG),
            img_compression=28,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_low_crf(self, client: ComfyUIClient) -> None:
        """I2V low CRF 18 (RuneXX style) — more motion freedom."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_low_crf",
            prompt_text=(
                "The Coca-Cola can spins slowly on the table, revealing the "
                "full label. Condensation beads shimmer as they catch the light. "
                "Smooth 360 rotation, product showcase, studio lighting."
            ),
            reference_image=str(TEST_IMG),
            img_compression=18,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_dolly_in(self, client: ComfyUIClient) -> None:
        """I2V + dolly-in camera LoRA."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_dolly_in",
            prompt_text=(
                "The Coca-Cola logo text becomes sharply legible. Fine water "
                "droplets on the aluminum surface catch individual highlights. "
                "The red paint shows subtle metallic flake texture. Extreme "
                "product macro, cinematic shallow depth of field."
            ),
            reference_image=str(TEST_IMG),
            lora_name="ltx-2-19b-lora-camera-control-dolly-in.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_static(self, client: ComfyUIClient) -> None:
        """I2V + static camera LoRA — locked-off product shot."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_static",
            prompt_text=(
                "The Coca-Cola can stands perfectly still. Condensation droplets "
                "slowly slide down the cold aluminum surface. A bead of water "
                "reaches the table and pools at the base. Warm studio lighting, "
                "no camera movement, product beauty shot."
            ),
            reference_image=str(TEST_IMG),
            lora_name="ltx-2-19b-lora-camera-control-static.safetensors",
            lora_strength=0.8,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_jib_up(self, client: ComfyUIClient) -> None:
        """I2V + jib-up camera LoRA."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_jib_up",
            prompt_text=(
                "Above the Coca-Cola can, a shelf of vintage soda bottles comes "
                "into view. Warm Edison bulbs hang from exposed ceiling beams. "
                "The rustic bar interior reveals itself — brick walls, chalkboard "
                "menus. Golden hour light streams through high windows."
            ),
            reference_image=str(TEST_IMG),
            lora_name="ltx-2-19b-lora-camera-control-jib-up.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestT2VCameraLoRAs:
    """T2V with every camera LoRA direction."""

    async def test_t2v_dolly_in(self, client: ComfyUIClient) -> None:
        """T2V + dolly-in — pushes toward subject."""
        result = await _run_variant(
            client,
            "t2v_dolly_in",
            prompt_text=(
                "A ceramic coffee mug rests on a slate countertop. The intricate "
                "hand-painted floral pattern becomes visible — fine brushstrokes, "
                "tiny imperfections in the glaze. Steam wisps curl above the rim, "
                "catching warm morning light. Shallow depth of field, product macro."
            ),
            lora_name="ltx-2-19b-lora-camera-control-dolly-in.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_dolly_out(self, client: ComfyUIClient) -> None:
        """T2V + dolly-out — pulls away from subject."""
        result = await _run_variant(
            client,
            "t2v_dolly_out",
            prompt_text=(
                "A pair of wireless earbuds rests on a dark slate surface. Behind "
                "them, a modern desk setup reveals itself — a curved ultrawide "
                "monitor glowing with ambient light, a mechanical keyboard, and a "
                "potted monstera plant in the corner. Twilight cityscape through "
                "floor-to-ceiling windows."
            ),
            lora_name="ltx-2-19b-lora-camera-control-dolly-out.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_dolly_left(self, client: ComfyUIClient) -> None:
        """T2V + dolly-left — translates left."""
        result = await _run_variant(
            client,
            "t2v_dolly_left",
            prompt_text=(
                "A row of colorful spice jars lines a wooden shelf. To the left, "
                "copper pots hang from a wrought iron rack. A marble mortar and "
                "pestle sits beside bundles of fresh herbs. Warm kitchen lighting, "
                "rustic farmhouse interior."
            ),
            lora_name="ltx-2-19b-lora-camera-control-dolly-left.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_dolly_right(self, client: ComfyUIClient) -> None:
        """T2V + dolly-right — translates right."""
        result = await _run_variant(
            client,
            "t2v_dolly_right",
            prompt_text=(
                "A vinyl record player spins on a mid-century credenza. To the "
                "right, a shelf of vinyl records reveals colorful album spines. "
                "A warm-toned floor lamp casts amber light across a shag rug. "
                "Cozy living room, evening ambiance."
            ),
            lora_name="ltx-2-19b-lora-camera-control-dolly-right.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_jib_up(self, client: ComfyUIClient) -> None:
        """T2V + jib-up — rises vertically."""
        result = await _run_variant(
            client,
            "t2v_jib_up",
            prompt_text=(
                "A barista pours steaming oat milk into a ceramic latte cup on "
                "the counter. Above, exposed brick walls rise to industrial "
                "ceiling beams strung with Edison bulbs. Morning light streams "
                "through skylights, casting warm geometric patterns."
            ),
            lora_name="ltx-2-19b-lora-camera-control-jib-up.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_jib_down(self, client: ComfyUIClient) -> None:
        """T2V + jib-down — descends vertically."""
        result = await _run_variant(
            client,
            "t2v_jib_down",
            prompt_text=(
                "Looking down from above, a wooden cutting board comes into view "
                "on a granite countertop. Fresh ingredients are arranged neatly — "
                "sliced avocado, cherry tomatoes, microgreens. A chef's knife "
                "rests beside the board. Overhead kitchen lighting, food styling."
            ),
            lora_name="ltx-2-19b-lora-camera-control-jib-down.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_static(self, client: ComfyUIClient) -> None:
        """T2V + static — locked-off, no camera movement."""
        result = await _run_variant(
            client,
            "t2v_static",
            prompt_text=(
                "A luxury watch rests on dark brushed marble in a minimalist "
                "studio. Warm amber side-lighting catches the polished bezel. "
                "The second hand sweeps smoothly around the dial. Subtle "
                "reflections dance across the sapphire crystal as light shifts."
            ),
            lora_name="ltx-2-19b-lora-camera-control-static.safetensors",
            lora_strength=0.8,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_lora_low_strength(self, client: ComfyUIClient) -> None:
        """T2V + dolly-in at 0.6 strength — tests distilled→camera LoRA chain."""
        result = await _run_variant(
            client,
            "t2v_lora_low_strength",
            prompt_text=(
                "A glass perfume bottle stands on a mirrored surface. Light "
                "refracts through the amber liquid, casting prismatic patterns "
                "on the mirror. Fine gold lettering on the label catches a "
                "spotlight. Luxury product photography, dark studio background."
            ),
            lora_name="ltx-2-19b-lora-camera-control-dolly-in.safetensors",
            lora_strength=0.6,
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestGuideFrameVariants:
    """First/last/mid frame guide variants."""

    async def test_fl2v_first_last(self, client: ComfyUIClient) -> None:
        """FL2V — coca.png frame 0, coca2.png frame -1."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        assert TEST_IMG2.exists(), f"Test image not found: {TEST_IMG2}"
        result = await _run_variant(
            client,
            "fl2v_first_last",
            prompt_text=(
                "A Coca-Cola can smoothly rotates on a glossy surface, "
                "transitioning from the front label view to reveal the "
                "nutrition facts panel on the back. Smooth continuous "
                "rotation, product commercial, studio lighting."
            ),
            guide_frames=[
                (str(TEST_IMG), 0, 1.0),
                (str(TEST_IMG2), -1, 1.0),
            ],
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_fml2v_three_guides(self, client: ComfyUIClient) -> None:
        """FML2V — three guide frames: first, mid, last."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        assert TEST_IMG2.exists(), f"Test image not found: {TEST_IMG2}"
        mid_frame = NUM_FRAMES // 2
        result = await _run_variant(
            client,
            "fml2v_three_guides",
            prompt_text=(
                "A Coca-Cola can rotates on a glossy surface. Starting from "
                "the front label, it passes through a side view at the "
                "midpoint, and ends showing the back of the can. Smooth "
                "continuous rotation, product showcase, warm studio lighting."
            ),
            guide_frames=[
                (str(TEST_IMG), 0, 1.0),
                (str(TEST_IMG), mid_frame, 0.5),
                (str(TEST_IMG2), -1, 1.0),
            ],
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_fl2v_dolly_in(self, client: ComfyUIClient) -> None:
        """FL2V + dolly-in camera LoRA — guide frames with camera motion."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        assert TEST_IMG2.exists(), f"Test image not found: {TEST_IMG2}"
        result = await _run_variant(
            client,
            "fl2v_dolly_in",
            prompt_text=(
                "The Coca-Cola can transitions from a wide establishing shot "
                "to a tight close-up. Fine label details and condensation "
                "texture become visible. The background softens into warm "
                "bokeh. Product reveal, commercial photography."
            ),
            guide_frames=[
                (str(TEST_IMG), 0, 1.0),
                (str(TEST_IMG2), -1, 1.0),
            ],
            lora_name="ltx-2-19b-lora-camera-control-dolly-in.safetensors",
            lora_strength=0.9,
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestNAGVariants:
    """Negative Anchor Guidance (DualCFGGuider) variants."""

    async def test_t2v_nag(self, client: ComfyUIClient) -> None:
        """T2V + NAG — split video/audio negative guidance."""
        result = await _run_variant(
            client,
            "t2v_nag",
            prompt_text=(
                "A man speaks directly to the camera in a warm, well-lit studio. "
                "His voice is clear and conversational. Behind him, soft bokeh "
                "lights create a professional podcast setting. Talking head, "
                "natural eye contact, subtle hand gestures."
            ),
            nag_video_cfg=0.25,
            nag_audio_cfg=2.5,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_nag(self, client: ComfyUIClient) -> None:
        """I2V + NAG — image input with split guidance."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_nag",
            prompt_text=(
                "The Coca-Cola can is picked up from the table. The sound of "
                "aluminum against wood, then the crisp pop of the tab opening. "
                "Fizzing carbonation bubbles rise. Product commercial, ASMR "
                "sound design, warm studio lighting."
            ),
            reference_image=str(TEST_IMG),
            nag_video_cfg=0.25,
            nag_audio_cfg=2.5,
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestSinglePass:
    """Single-pass pipeline (skip stage 2 refinement)."""

    async def test_t2v_single_pass(self, client: ComfyUIClient) -> None:
        """T2V single-pass — full res in one stage, no upscale."""
        result = await _run_variant(
            client,
            "t2v_single_pass",
            prompt_text=(
                "A red Coca-Cola can sits on a wooden table, condensation "
                "droplets forming on the cold metal surface. Warm sunlight "
                "streams through a window, casting soft shadows. Product shot, "
                "cinematic lighting, shallow depth of field."
            ),
            single_pass=True,
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_i2v_single_pass(self, client: ComfyUIClient) -> None:
        """I2V single-pass — faster iteration with image input."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        result = await _run_variant(
            client,
            "i2v_single_pass",
            prompt_text=(
                "The Coca-Cola can slowly rotates, revealing the label. "
                "Condensation droplets shimmer. Product showcase, studio lighting."
            ),
            reference_image=str(TEST_IMG),
            single_pass=True,
        )
        assert result.exists()
        assert result.stat().st_size > 1000


class TestIA2V:
    """Image+Audio to Video (IA2V) — real audio input."""

    async def test_ia2v_basic(self, client: ComfyUIClient) -> None:
        """IA2V — I2V with real audio input encoded via LTXVAudioVAEEncode."""
        assert TEST_IMG.exists(), f"Test image not found: {TEST_IMG}"
        assert TEST_AUDIO.exists(), f"Test audio not found: {TEST_AUDIO}"
        result = await _run_variant(
            client,
            "ia2v_basic",
            prompt_text=(
                "The Coca-Cola can sits on a wooden table. A hand reaches in "
                "and taps the side of the can rhythmically. The metallic "
                "tapping sound rings out clearly. Product shot, warm lighting, "
                "shallow depth of field."
            ),
            reference_image=str(TEST_IMG),
            audio_input=str(TEST_AUDIO),
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    async def test_t2v_with_audio(self, client: ComfyUIClient) -> None:
        """T2V with real audio input (no reference image)."""
        assert TEST_AUDIO.exists(), f"Test audio not found: {TEST_AUDIO}"
        result = await _run_variant(
            client,
            "t2v_with_audio",
            prompt_text=(
                "A musician strums an acoustic guitar in a cozy room. Warm "
                "golden light illuminates the wooden body of the guitar. "
                "Fingers move across the fretboard. Close-up, shallow depth "
                "of field, intimate concert feel."
            ),
            audio_input=str(TEST_AUDIO),
        )
        assert result.exists()
        assert result.stat().st_size > 1000
