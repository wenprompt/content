import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.clients.comfyui_client import ComfyUIClient, ComfyUIError

WS_CONNECT = (
    "backend.clients.comfyui_client.websockets.asyncio.client.connect"
)


@pytest.fixture
def client() -> ComfyUIClient:
    return ComfyUIClient("http://localhost:8188")


def _mock_http(
    method: str = "get", response: MagicMock | None = None
) -> MagicMock:
    """Create a mock httpx.AsyncClient context manager."""
    mock_http = AsyncMock()
    if response is None:
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json.return_value = {}
    setattr(mock_http, method, AsyncMock(return_value=response))
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)
    return mock_http


def _mock_ws(messages: list[str]) -> AsyncMock:
    """Create a mock websocket context manager."""
    ws = AsyncMock()
    ws.recv = AsyncMock(side_effect=messages)
    ws.__aenter__ = AsyncMock(return_value=ws)
    ws.__aexit__ = AsyncMock(return_value=None)
    return ws


class TestIsAvailable:
    async def test_available(self, client: ComfyUIClient) -> None:
        mock = _mock_http("get")
        with patch("backend.clients.comfyui_client.httpx.AsyncClient", return_value=mock):
            assert await client.is_available() is True

    async def test_unavailable(self, client: ComfyUIClient) -> None:
        mock = _mock_http("get")
        mock.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        with patch("backend.clients.comfyui_client.httpx.AsyncClient", return_value=mock):
            assert await client.is_available() is False


class TestUploadImage:
    async def test_upload(self, client: ComfyUIClient, tmp_path: Path) -> None:
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake")

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"name": "test.png"}
        mock = _mock_http("post", resp)

        with patch("backend.clients.comfyui_client.httpx.AsyncClient", return_value=mock):
            result = await client.upload_image(img)

        assert result == "test.png"
        mock.post.assert_called_once()


class TestQueuePrompt:
    async def test_queue(self, client: ComfyUIClient) -> None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"prompt_id": "abc-123"}
        mock = _mock_http("post", resp)

        with patch("backend.clients.comfyui_client.httpx.AsyncClient", return_value=mock):
            result = await client.queue_prompt({"test": "workflow"})

        assert result == "abc-123"
        payload = mock.post.call_args.kwargs["json"]
        assert payload["prompt"] == {"test": "workflow"}
        assert "client_id" in payload


class TestGetHistory:
    async def test_history(self, client: ComfyUIClient) -> None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"abc-123": {"outputs": {}}}
        mock = _mock_http("get", resp)

        with patch("backend.clients.comfyui_client.httpx.AsyncClient", return_value=mock):
            result = await client.get_history("abc-123")

        assert "abc-123" in result


class TestBuildWorkflow:
    def test_t2v_workflow_structure(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="A cat walking", negative_prompt="ugly",
            width=1280, height=720, num_frames=121, seed=42, fps=24,
        )
        # T2V should NOT have image nodes (ComfyUI validates all inputs)
        expected_nodes = {
            "236": "CheckpointLoaderSimple",
            "243": "LTXAVTextEncoderLoader",
            "221": "LTXVAudioVAELoader",
            "232": "LoraLoaderModelOnly",
            "233": "LatentUpscaleModelLoader",
            "240": "CLIPTextEncode",
            "247": "CLIPTextEncode",
            "239": "LTXVConditioning",
            "228": "EmptyLTXVLatentVideo",
            "214": "LTXVEmptyLatentAudio",
            "222": "LTXVConcatAVLatent",
            "231": "CFGGuider",
            "209": "KSamplerSelect",
            "252": "ManualSigmas",
            "237": "RandomNoise",
            "215": "SamplerCustomAdvanced",
            "217": "LTXVSeparateAVLatent",
            "253": "LTXVLatentUpsampler",
            "212": "LTXVCropGuides",
            "229": "LTXVConcatAVLatent",
            "213": "CFGGuider",
            "246": "KSamplerSelect",
            "211": "ManualSigmas",
            "216": "RandomNoise",
            "219": "SamplerCustomAdvanced",
            "218": "LTXVSeparateAVLatent",
            "251": "VAEDecodeTiled",
            "220": "LTXVAudioVAEDecode",
            "242": "CreateVideo",
            "75": "SaveVideo",
        }
        for node_id, class_type in expected_nodes.items():
            assert w[node_id]["class_type"] == class_type, (
                f"Node {node_id}: expected {class_type}, "
                f"got {w[node_id]['class_type']}"
            )

    def test_t2v_no_image_nodes(self, client: ComfyUIClient) -> None:
        """T2V must not include image nodes — ComfyUI validates all inputs."""
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        for node_id in ("269", "238", "235", "248", "249", "230"):
            assert node_id not in w, f"T2V should not have node {node_id}"

    def test_t2v_direct_wiring(self, client: ComfyUIClient) -> None:
        """T2V: EmptyLTXVLatentVideo → ConcatAVLatent (stage 1),
        LTXVLatentUpsampler → ConcatAVLatent (stage 2)."""
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        # Stage 1: empty latent directly to concat
        assert w["222"]["inputs"]["video_latent"] == ["228", 0]
        # Stage 2: upsampled latent directly to concat
        assert w["229"]["inputs"]["video_latent"] == ["253", 0]

    def test_i2v_has_image_nodes(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
            image_filename="ref.png",
        )
        assert w["269"]["inputs"]["image"] == "ref.png"
        assert w["249"]["inputs"]["bypass"] is False
        assert w["230"]["inputs"]["bypass"] is False
        # Stage 1: image injected via LTXVImgToVideoInplace
        assert w["222"]["inputs"]["video_latent"] == ["249", 0]
        # Stage 2: image re-injected via LTXVImgToVideoInplace
        assert w["229"]["inputs"]["video_latent"] == ["230", 0]

    def test_half_resolution_stage1(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["228"]["inputs"]["width"] == 640
        assert w["228"]["inputs"]["height"] == 360

    def test_prompt_and_negative(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="A cat on a beach",
            negative_prompt="blurry, ugly",
            width=1280, height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["240"]["inputs"]["text"] == "A cat on a beach"
        assert w["247"]["inputs"]["text"] == "blurry, ugly"

    def test_default_negative_prompt(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert "worst quality" in w["247"]["inputs"]["text"]

    def test_seed_propagation(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["237"]["inputs"]["noise_seed"] == 42
        assert w["216"]["inputs"]["noise_seed"] == 43

    def test_fps_propagation(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=25,
        )
        assert w["239"]["inputs"]["frame_rate"] == 25
        assert w["214"]["inputs"]["frame_rate"] == 25
        assert w["242"]["inputs"]["fps"] == 25

    def test_cfg_is_1_for_distilled(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["231"]["inputs"]["cfg"] == 1
        assert w["213"]["inputs"]["cfg"] == 1

    def test_no_camera_lora(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert "234" not in w
        # Without camera LoRA, CFGGuiders connect directly to model source
        assert w["231"]["inputs"]["model"] == ["232", 0]
        assert w["213"]["inputs"]["model"] == ["232", 0]

    def test_with_camera_lora(self, client: ComfyUIClient) -> None:
        lora = "ltx-2-19b-lora-camera-control-dolly-in.safetensors"
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
            lora_name=lora, lora_strength=0.85,
        )
        assert w["234"]["class_type"] == "LoraLoaderModelOnly"
        assert w["234"]["inputs"]["model"] == ["232", 0]
        assert w["234"]["inputs"]["strength_model"] == 0.85
        # CFGGuiders take camera LoRA output
        assert w["231"]["inputs"]["model"] == ["234", 0]
        assert w["213"]["inputs"]["model"] == ["234", 0]

    def test_model_files(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        ckpt = "ltx-2.3-22b-dev-fp8.safetensors"
        assert w["236"]["inputs"]["ckpt_name"] == ckpt
        assert w["243"]["inputs"]["text_encoder"] == (
            "gemma_3_12B_it_fp4_mixed.safetensors"
        )
        assert w["232"]["inputs"]["lora_name"] == (
            "ltx-2.3-22b-distilled-lora-384.safetensors"
        )
        assert w["233"]["inputs"]["model_name"] == (
            "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
        )

    def test_stage1_sigmas_8_steps(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        sigmas = w["252"]["inputs"]["sigmas"]
        assert len(sigmas.split(",")) == 9  # 8 steps = 9 values

    def test_stage2_sigmas_4_steps(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["211"]["inputs"]["sigmas"].startswith("0.85")

    def test_stage1_sampler(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["209"]["inputs"]["sampler_name"] == (
            "euler_ancestral_cfg_pp"
        )

    def test_stage2_sampler(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["246"]["inputs"]["sampler_name"] == "euler_cfg_pp"

    def test_vae_decode_tiled(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
        )
        assert w["251"]["class_type"] == "VAEDecodeTiled"
        assert w["251"]["inputs"]["tile_size"] == 768
        assert w["251"]["inputs"]["overlap"] == 64

    def test_num_frames_propagation(self, client: ComfyUIClient) -> None:
        w = client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=97, seed=42, fps=24,
        )
        assert w["228"]["inputs"]["length"] == 97
        assert w["214"]["inputs"]["frames_number"] == 97


class TestBuildWorkflowGuides:
    """Tests for LTXVAddGuide (guide frame conditioning)."""

    def _build_with_guides(
        self, client: ComfyUIClient,
        guides: list[tuple[str, int, float]] | None = None,
    ) -> dict[str, Any]:
        return client._build_workflow(
            prompt_text="test", negative_prompt="", width=1280,
            height=720, num_frames=121, seed=42, fps=24,
            guide_frames=guides,
        )

    def test_guide_nodes_present(self, client: ComfyUIClient) -> None:
        """LTXVAddGuide nodes created for each guide frame."""
        w = self._build_with_guides(client, [
            ("first.png", 0, 1.0),
            ("last.png", -1, 0.8),
        ])
        assert w["g_load_0"]["class_type"] == "LoadImage"
        assert w["g_load_0"]["inputs"]["image"] == "first.png"
        assert w["g_resize_0"]["class_type"] == "ResizeImageMaskNode"
        assert w["g_guide_0"]["class_type"] == "LTXVAddGuide"
        assert w["g_guide_0"]["inputs"]["frame_idx"] == 0
        assert w["g_guide_0"]["inputs"]["strength"] == 1.0

        assert w["g_load_1"]["inputs"]["image"] == "last.png"
        assert w["g_guide_1"]["inputs"]["frame_idx"] == -1
        assert w["g_guide_1"]["inputs"]["strength"] == 0.8

    def test_guides_no_i2v_nodes(self, client: ComfyUIClient) -> None:
        """Guide frames should NOT include LTXVImgToVideoInplace nodes."""
        w = self._build_with_guides(client, [("img.png", 0, 1.0)])
        for node_id in ("269", "238", "235", "248", "249", "230"):
            assert node_id not in w, f"Guide workflow should not have node {node_id}"

    def test_guides_chain_to_cfgguider(self, client: ComfyUIClient) -> None:
        """Stage 1 CFGGuider should use guide chain outputs."""
        w = self._build_with_guides(client, [
            ("first.png", 0, 1.0),
            ("last.png", -1, 1.0),
        ])
        # Last guide node is g_guide_1
        assert w["231"]["inputs"]["positive"] == ["g_guide_1", 0]
        assert w["231"]["inputs"]["negative"] == ["g_guide_1", 1]

    def test_guides_chain_to_cropguides(self, client: ComfyUIClient) -> None:
        """Stage 2 LTXVCropGuides should use guide-modified conditioning."""
        w = self._build_with_guides(client, [
            ("first.png", 0, 1.0),
            ("last.png", -1, 1.0),
        ])
        assert w["212"]["inputs"]["positive"] == ["g_guide_1", 0]
        assert w["212"]["inputs"]["negative"] == ["g_guide_1", 1]

    def test_guides_latent_to_concat(self, client: ComfyUIClient) -> None:
        """Stage 1 ConcatAVLatent should use guide latent output."""
        w = self._build_with_guides(client, [("img.png", 0, 1.0)])
        assert w["222"]["inputs"]["video_latent"] == ["g_guide_0", 2]

    def test_guide_chain_wiring(self, client: ComfyUIClient) -> None:
        """Second guide chains from first guide's outputs."""
        w = self._build_with_guides(client, [
            ("first.png", 0, 1.0),
            ("last.png", -1, 1.0),
        ])
        # Second guide takes first guide's outputs
        assert w["g_guide_1"]["inputs"]["positive"] == ["g_guide_0", 0]
        assert w["g_guide_1"]["inputs"]["negative"] == ["g_guide_0", 1]
        assert w["g_guide_1"]["inputs"]["latent"] == ["g_guide_0", 2]

    def test_guide_resize_half_res(self, client: ComfyUIClient) -> None:
        """Guide images should be resized to half resolution (stage 1)."""
        w = self._build_with_guides(client, [("img.png", 0, 1.0)])
        assert w["g_resize_0"]["inputs"]["resize_type.width"] == 640
        assert w["g_resize_0"]["inputs"]["resize_type.height"] == 360

    def test_single_guide_wiring(self, client: ComfyUIClient) -> None:
        """Single guide: first guide chains from LTXVConditioning."""
        w = self._build_with_guides(client, [("img.png", 0, 1.0)])
        assert w["g_guide_0"]["inputs"]["positive"] == ["239", 0]
        assert w["g_guide_0"]["inputs"]["negative"] == ["239", 1]
        assert w["g_guide_0"]["inputs"]["latent"] == ["228", 0]


class TestGenerateVideoFlow:
    async def test_full_t2v_flow(
        self, client: ComfyUIClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Mock the full T2V flow: queue -> WS -> history -> download."""
        monkeypatch.setattr(
            client, "queue_prompt",
            AsyncMock(return_value="prompt-123"),
        )
        monkeypatch.setattr(
            client, "get_history",
            AsyncMock(return_value={
                "prompt-123": {
                    "outputs": {
                        "75": {"images": [
                            {"filename": "ltx_00001_.mp4", "subfolder": "video"}
                        ]}
                    }
                }
            }),
        )
        monkeypatch.setattr(
            client, "get_output_video",
            AsyncMock(return_value=b"fake-video-data"),
        )

        ws_messages = [
            json.dumps({"type": "progress", "data": {"value": 1, "max": 8}}),
            json.dumps({"type": "progress", "data": {"value": 8, "max": 8}}),
            json.dumps({
                "type": "executing",
                "data": {"node": None, "prompt_id": "prompt-123"},
            }),
        ]
        progress_calls: list[tuple[int, int]] = []

        async def track_progress(step: int, total: int) -> None:
            progress_calls.append((step, total))

        with patch(WS_CONNECT, return_value=_mock_ws(ws_messages)):
            result = await client.generate_video(
                prompt_text="A cat walking",
                seed=42,
                progress_callback=track_progress,
            )

        assert result.exists()
        assert result.read_bytes() == b"fake-video-data"
        assert progress_calls == [(1, 8), (8, 8)]
        result.unlink(missing_ok=True)

    async def test_execution_error(
        self, client: ComfyUIClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            client, "queue_prompt",
            AsyncMock(return_value="prompt-err"),
        )

        ws_messages = [json.dumps({
            "type": "execution_error",
            "data": {"exception_message": "Out of VRAM"},
        })]

        with (
            patch(WS_CONNECT, return_value=_mock_ws(ws_messages)),
            pytest.raises(ComfyUIError, match="Out of VRAM"),
        ):
            await client.generate_video(prompt_text="test", seed=1)

    async def test_timeout(
        self, client: ComfyUIClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client._timeout = 0.01
        monkeypatch.setattr(
            client, "queue_prompt",
            AsyncMock(return_value="prompt-timeout"),
        )

        async def hang() -> str:
            await asyncio.sleep(10)
            return ""

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=hang)
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(WS_CONNECT, return_value=mock_ws),
            pytest.raises(ComfyUIError, match="timed out"),
        ):
            await client.generate_video(prompt_text="test", seed=1)

    async def test_no_output_in_history(
        self, client: ComfyUIClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            client, "queue_prompt",
            AsyncMock(return_value="prompt-noout"),
        )
        monkeypatch.setattr(
            client, "get_history",
            AsyncMock(return_value={"prompt-noout": {"outputs": {}}}),
        )

        ws_messages = [json.dumps({
            "type": "executing",
            "data": {"node": None, "prompt_id": "prompt-noout"},
        })]

        with (
            patch(WS_CONNECT, return_value=_mock_ws(ws_messages)),
            pytest.raises(ComfyUIError, match="No video output"),
        ):
            await client.generate_video(prompt_text="test", seed=1)

    async def test_i2v_uploads_image(
        self,
        client: ComfyUIClient,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        img = tmp_path / "ref.png"
        img.write_bytes(b"\x89PNG")

        mock_upload = AsyncMock(return_value="ref.png")
        mock_queue = AsyncMock(return_value="prompt-i2v")
        monkeypatch.setattr(client, "upload_image", mock_upload)
        monkeypatch.setattr(client, "queue_prompt", mock_queue)
        monkeypatch.setattr(
            client, "get_history",
            AsyncMock(return_value={
                "prompt-i2v": {
                    "outputs": {"75": {"images": [
                        {"filename": "out.mp4", "subfolder": "video"}
                    ]}}
                }
            }),
        )
        monkeypatch.setattr(
            client, "get_output_video",
            AsyncMock(return_value=b"video"),
        )

        ws_messages = [json.dumps({
            "type": "executing",
            "data": {"node": None, "prompt_id": "prompt-i2v"},
        })]

        with patch(WS_CONNECT, return_value=_mock_ws(ws_messages)):
            result = await client.generate_video(
                prompt_text="test", seed=1,
                reference_image=str(img),
            )

        mock_upload.assert_called_once_with(str(img))
        queued = mock_queue.call_args[0][0]
        # I2V workflow should have image nodes
        assert "269" in queued
        assert queued["249"]["inputs"]["bypass"] is False
        result.unlink(missing_ok=True)

    async def test_retry_on_queue_failure(
        self, client: ComfyUIClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_queue = AsyncMock(side_effect=[
            httpx.ConnectError("refused"),
            httpx.ConnectError("refused"),
            "prompt-ok",
        ])
        monkeypatch.setattr(client, "queue_prompt", mock_queue)
        monkeypatch.setattr(
            client, "get_history",
            AsyncMock(return_value={
                "prompt-ok": {
                    "outputs": {"75": {"images": [
                        {"filename": "out.mp4", "subfolder": "video"}
                    ]}}
                }
            }),
        )
        monkeypatch.setattr(
            client, "get_output_video",
            AsyncMock(return_value=b"video"),
        )

        ws_messages = [json.dumps({
            "type": "executing",
            "data": {"node": None, "prompt_id": "prompt-ok"},
        })]

        with (
            patch(WS_CONNECT, return_value=_mock_ws(ws_messages)),
            patch(
                "backend.clients.comfyui_client.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await client.generate_video(
                prompt_text="test", seed=1,
            )

        assert mock_queue.call_count == 3
        result.unlink(missing_ok=True)
