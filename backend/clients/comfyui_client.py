"""ComfyUI API client for LTX-2.3 video generation.

Builds API-format workflows matching the proven two-stage distilled pipeline:
  Stage 1: half-res generation (8 steps, euler_ancestral_cfg_pp)
  Latent upscale: LTXVLatentUpsampler 2x
  Stage 2: full-res refinement (4 steps, euler_cfg_pp)

Reference workflows: docs/video_ltx2_3_t2v.json, docs/video_ltx2_3_i2v.json
"""

import asyncio
import json
import random
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import websockets
import websockets.asyncio.client


class ComfyUIError(Exception):
    pass


class ComfyUIClient:
    def __init__(self, base_url: str = "http://localhost:8188") -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())
        self._timeout = 600.0
        self._max_retries = 3

    # ── Low-level API methods ──────────────────────────────────────────

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/queue", timeout=5.0)
                return r.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def upload_image(self, image_path: str | Path, subfolder: str = "") -> str:
        path = Path(image_path)
        async with httpx.AsyncClient() as client:
            with path.open("rb") as f:
                r = await client.post(
                    f"{self.base_url}/upload/image",
                    files={"image": (path.name, f, "image/png")},
                    data={"subfolder": subfolder, "overwrite": "true"},
                    timeout=30.0,
                )
            r.raise_for_status()
            data = r.json()
            return str(data.get("name", path.name))

    async def queue_prompt(self, prompt: dict[str, Any]) -> str:
        payload = {"prompt": prompt, "client_id": self.client_id}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            prompt_id: str = data["prompt_id"]
            return prompt_id

    async def get_history(self, prompt_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=30.0,
            )
            r.raise_for_status()
            result: dict[str, Any] = r.json()
            return result

    async def get_output_video(
        self, filename: str, subfolder: str = "video"
    ) -> bytes:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": "output"},
                timeout=120.0,
            )
            r.raise_for_status()
            return r.content

    # ── Workflow builder ───────────────────────────────────────────────

    def _build_workflow(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_frames: int,
        seed: int,
        fps: int,
        image_filename: str | None = None,
        lora_name: str = "",
        lora_strength: float = 0.9,
        i2v_strength: float = 0.7,
        img_compression: int = 28,
        guide_frames: list[tuple[str, int, float]] | None = None,
    ) -> dict[str, Any]:
        """Build the LTX-2.3 two-stage distilled API workflow.

        For T2V (no image): EmptyLTXVLatentVideo feeds directly into sampling.
        For I2V (with image): LoadImage → preprocess → LTXVImgToVideoInplace
        injects the reference image into the latent at both stages.
        For guided T2V: LTXVAddGuide injects keyframe images at specific frame
        indices (e.g. frame 0 and frame -1 for first/last frame conditioning).

        guide_frames: list of (filename, frame_idx, strength) tuples.
          frame_idx: 0 for first frame, -1 for last frame, etc.
          strength: 0.0-1.0, how strongly to condition on the image.

        ComfyUI validates ALL node inputs at submission time, so T2V cannot
        include LoadImage with a nonexistent file — the workflows must differ.
        """
        is_i2v = image_filename is not None
        half_w = width // 2
        half_h = height // 2

        w: dict[str, Any] = {}

        # ── Model loaders ──────────────────────────────────────────────

        w["236"] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"},
        }
        w["243"] = {
            "class_type": "LTXAVTextEncoderLoader",
            "inputs": {
                "text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors",
                "ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors",
                "device": "default",
            },
        }
        w["221"] = {
            "class_type": "LTXVAudioVAELoader",
            "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"},
        }
        w["232"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "lora_name": "ltx-2.3-22b-distilled-lora-384.safetensors",
                "strength_model": 0.5,
                "model": ["236", 0],
            },
        }
        w["233"] = {
            "class_type": "LatentUpscaleModelLoader",
            "inputs": {"model_name": "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"},
        }

        # Optional camera LoRA — chain after distilled LoRA
        model_source: list[str | int] = ["232", 0]
        if lora_name:
            w["234"] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "lora_name": lora_name,
                    "strength_model": lora_strength,
                    "model": ["232", 0],
                },
            }
            model_source = ["234", 0]

        # ── Text encoding ──────────────────────────────────────────────

        w["240"] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["243", 0]},
        }
        w["247"] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt
                or "pc game, console game, video game, cartoon, childish, ugly",
                "clip": ["243", 0],
            },
        }
        w["239"] = {
            "class_type": "LTXVConditioning",
            "inputs": {
                "frame_rate": fps,
                "positive": ["240", 0],
                "negative": ["247", 0],
            },
        }

        # ── Guide frames (LTXVAddGuide — keyframe conditioning) ────────

        has_guides = bool(guide_frames)

        # ── I2V: Reference image preprocessing ─────────────────────────

        if is_i2v:
            w["269"] = {
                "class_type": "LoadImage",
                "inputs": {"image": image_filename},
            }
            w["238"] = {
                "class_type": "ResizeImageMaskNode",
                "inputs": {
                    "resize_type": "scale dimensions",
                    "resize_type.width": width,
                    "resize_type.height": height,
                    "resize_type.crop": "center",
                    "scale_method": "lanczos",
                    "input": ["269", 0],
                },
            }
            w["235"] = {
                "class_type": "ResizeImagesByLongerEdge",
                "inputs": {"longer_edge": 1536, "images": ["238", 0]},
            }
            w["248"] = {
                "class_type": "LTXVPreprocess",
                "inputs": {"img_compression": img_compression, "image": ["235", 0]},
            }

        # ── Stage 1: Base generation at half resolution ────────────────

        w["228"] = {
            "class_type": "EmptyLTXVLatentVideo",
            "inputs": {
                "width": half_w,
                "height": half_h,
                "length": num_frames,
                "batch_size": 1,
            },
        }

        # ── Guide frame nodes (after empty latent, before stage 1) ─────

        # Track conditioning sources — guides will override these
        stage1_pos: list[str | int] = ["239", 0]
        stage1_neg: list[str | int] = ["239", 1]
        stage1_latent: list[str | int] = ["228", 0]

        if has_guides and guide_frames:
            for i, (gf_filename, gf_frame_idx, gf_strength) in enumerate(guide_frames):
                load_id = f"g_load_{i}"
                resize_id = f"g_resize_{i}"
                guide_id = f"g_guide_{i}"

                w[load_id] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": gf_filename},
                }
                w[resize_id] = {
                    "class_type": "ResizeImageMaskNode",
                    "inputs": {
                        "resize_type": "scale dimensions",
                        "resize_type.width": half_w,
                        "resize_type.height": half_h,
                        "resize_type.crop": "center",
                        "scale_method": "lanczos",
                        "input": [load_id, 0],
                    },
                }
                w[guide_id] = {
                    "class_type": "LTXVAddGuide",
                    "inputs": {
                        "positive": stage1_pos,
                        "negative": stage1_neg,
                        "vae": ["236", 2],
                        "latent": stage1_latent,
                        "image": [resize_id, 0],
                        "frame_idx": gf_frame_idx,
                        "strength": gf_strength,
                    },
                }
                # Chain: next guide takes this guide's outputs
                stage1_pos = [guide_id, 0]
                stage1_neg = [guide_id, 1]
                stage1_latent = [guide_id, 2]

        # Stage 1 video latent source:
        # - I2V: LTXVImgToVideoInplace injects image into latent
        # - Guides (no I2V): guide chain already modified the latent
        # - Plain T2V: use empty latent directly
        if is_i2v:
            w["249"] = {
                "class_type": "LTXVImgToVideoInplace",
                "inputs": {
                    "strength": i2v_strength,
                    "bypass": False,
                    "vae": ["236", 2],
                    "image": ["248", 0],
                    "latent": ["228", 0],
                },
            }
            stage1_video_source: list[str | int] = ["249", 0]
        elif has_guides:
            stage1_video_source = stage1_latent
        else:
            stage1_video_source = ["228", 0]

        w["214"] = {
            "class_type": "LTXVEmptyLatentAudio",
            "inputs": {
                "frames_number": num_frames,
                "frame_rate": fps,
                "batch_size": 1,
                "audio_vae": ["221", 0],
            },
        }
        w["222"] = {
            "class_type": "LTXVConcatAVLatent",
            "inputs": {
                "video_latent": stage1_video_source,
                "audio_latent": ["214", 0],
            },
        }
        w["231"] = {
            "class_type": "CFGGuider",
            "inputs": {
                "cfg": 1,
                "model": model_source,
                "positive": stage1_pos,
                "negative": stage1_neg,
            },
        }
        w["209"] = {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler_ancestral_cfg_pp"},
        }
        w["252"] = {
            "class_type": "ManualSigmas",
            "inputs": {
                "sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0",
            },
        }
        w["237"] = {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": seed},
        }
        w["215"] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["237", 0],
                "guider": ["231", 0],
                "sampler": ["209", 0],
                "sigmas": ["252", 0],
                "latent_image": ["222", 0],
            },
        }

        # ── Separate + Upscale ─────────────────────────────────────────

        w["217"] = {
            "class_type": "LTXVSeparateAVLatent",
            "inputs": {"av_latent": ["215", 0]},
        }
        w["253"] = {
            "class_type": "LTXVLatentUpsampler",
            "inputs": {
                "samples": ["217", 0],
                "upscale_model": ["233", 0],
                "vae": ["236", 2],
            },
        }

        # ── Stage 2: Refinement at full resolution ─────────────────────

        # Stage 2 video latent source: I2V re-injects image, T2V uses upscaled directly
        if is_i2v:
            w["230"] = {
                "class_type": "LTXVImgToVideoInplace",
                "inputs": {
                    "strength": 1,
                    "bypass": False,
                    "vae": ["236", 2],
                    "image": ["248", 0],
                    "latent": ["253", 0],
                },
            }
            stage2_video_source: list[str | int] = ["230", 0]
        else:
            stage2_video_source = ["253", 0]

        w["212"] = {
            "class_type": "LTXVCropGuides",
            "inputs": {
                "positive": stage1_pos,
                "negative": stage1_neg,
                "latent": ["217", 0],
            },
        }
        w["229"] = {
            "class_type": "LTXVConcatAVLatent",
            "inputs": {
                "video_latent": stage2_video_source,
                "audio_latent": ["217", 1],
            },
        }
        w["213"] = {
            "class_type": "CFGGuider",
            "inputs": {
                "cfg": 1,
                "model": model_source,
                "positive": ["212", 0],
                "negative": ["212", 1],
            },
        }
        w["246"] = {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler_cfg_pp"},
        }
        w["211"] = {
            "class_type": "ManualSigmas",
            "inputs": {"sigmas": "0.85, 0.7250, 0.4219, 0.0"},
        }
        w["216"] = {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": (seed + 1) % (2**32)},
        }
        w["219"] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["216", 0],
                "guider": ["213", 0],
                "sampler": ["246", 0],
                "sigmas": ["211", 0],
                "latent_image": ["229", 0],
            },
        }

        # ── Decode + Output ────────────────────────────────────────────

        w["218"] = {
            "class_type": "LTXVSeparateAVLatent",
            "inputs": {"av_latent": ["219", 0]},
        }
        w["251"] = {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "tile_size": 768,
                "overlap": 64,
                "temporal_size": 4096,
                "temporal_overlap": 4,
                "samples": ["218", 0],
                "vae": ["236", 2],
            },
        }
        w["220"] = {
            "class_type": "LTXVAudioVAEDecode",
            "inputs": {
                "samples": ["218", 1],
                "audio_vae": ["221", 0],
            },
        }
        w["242"] = {
            "class_type": "CreateVideo",
            "inputs": {
                "fps": fps,
                "images": ["251", 0],
                "audio": ["220", 0],
            },
        }
        w["75"] = {
            "class_type": "SaveVideo",
            "inputs": {
                "filename_prefix": "video/ltx",
                "format": "auto",
                "codec": "auto",
                "video": ["242", 0],
            },
        }

        return w

    # ── High-level generation ──────────────────────────────────────────

    async def generate_video(
        self,
        prompt_text: str,
        negative_prompt: str = "",
        width: int = 1280,
        height: int = 720,
        num_frames: int = 121,
        steps: int = 20,
        cfg: float = 3.0,
        seed: int = -1,
        fps: int = 24,
        reference_image: str | None = None,
        lora_name: str = "",
        lora_strength: float = 0.9,
        i2v_strength: float = 0.7,
        img_compression: int = 28,
        guide_frames: list[tuple[str, int, float]] | None = None,
        progress_callback: Callable[[int, int], Any] | None = None,
    ) -> Path:
        """Generate video via ComfyUI LTX-2.3 pipeline.

        Note: steps and cfg parameters are accepted for interface compatibility
        but are not used — the distilled pipeline uses fixed 8+4 steps and CFG=1.

        guide_frames: list of (local_image_path, frame_idx, strength) tuples.
          Mutually exclusive with reference_image (I2V). Uses LTXVAddGuide nodes
          to condition on keyframe images at specific frame positions.
        """
        if reference_image and guide_frames:
            raise ValueError(
                "reference_image and guide_frames are mutually exclusive"
            )

        if seed < 0:
            seed = random.randint(0, 2**32 - 1)

        # Upload reference image if provided
        image_filename: str | None = None
        if reference_image:
            image_filename = await self.upload_image(reference_image)

        # Upload guide frame images if provided
        uploaded_guides: list[tuple[str, int, float]] | None = None
        if guide_frames:
            uploaded_guides = []
            for img_path, frame_idx, strength in guide_frames:
                filename = await self.upload_image(img_path)
                uploaded_guides.append((filename, frame_idx, strength))

        workflow = self._build_workflow(
            prompt_text=prompt_text,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            seed=seed,
            fps=fps,
            image_filename=image_filename,
            lora_name=lora_name,
            lora_strength=lora_strength,
            i2v_strength=i2v_strength,
            img_compression=img_compression,
            guide_frames=uploaded_guides,
        )

        # Queue prompt with retries
        prompt_id: str | None = None
        for attempt in range(self._max_retries):
            try:
                prompt_id = await self.queue_prompt(workflow)
                break
            except (httpx.HTTPError, OSError) as e:
                if attempt == self._max_retries - 1:
                    raise ComfyUIError(
                        f"Failed to queue prompt after {self._max_retries} attempts: {e}"
                    ) from e
                await asyncio.sleep(1.0)

        if prompt_id is None:
            raise ComfyUIError("Failed to obtain prompt_id after retries")

        # Listen for progress via WebSocket
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws?clientId={self.client_id}"

        try:
            async with asyncio.timeout(self._timeout):
                async with websockets.asyncio.client.connect(ws_url) as ws:
                    while True:
                        raw = await ws.recv()
                        if isinstance(raw, bytes):
                            continue
                        msg = json.loads(raw)
                        msg_type = msg.get("type", "")

                        if msg_type == "progress":
                            data = msg["data"]
                            if data.get("prompt_id") == prompt_id or "prompt_id" not in data:
                                step = int(data["value"])
                                total = int(data["max"])
                                if progress_callback is not None:
                                    await progress_callback(step, total)

                        elif msg_type == "executing":
                            data = msg["data"]
                            if data.get("prompt_id") == prompt_id and data.get("node") is None:
                                break  # Execution complete

                        elif msg_type == "execution_error":
                            data = msg.get("data", {})
                            error_msg = data.get(
                                "exception_message", "Unknown execution error"
                            )
                            raise ComfyUIError(f"ComfyUI execution error: {error_msg}")
        except TimeoutError:
            raise ComfyUIError(
                f"Video generation timed out after {self._timeout}s"
            ) from None

        # Get output filename from history
        history = await self.get_history(prompt_id)
        prompt_history = history.get(prompt_id, {})
        outputs = prompt_history.get("outputs", {})

        # Find SaveVideo node output (node "75")
        video_filename: str | None = None
        subfolder: str = "video"
        for node_outputs in outputs.values():
            for key in ("images", "videos", "gifs"):
                if key in node_outputs:
                    for item in node_outputs[key]:
                        video_filename = item.get("filename")
                        subfolder = item.get("subfolder", "video")
                        break
                if video_filename:
                    break
            if video_filename:
                break

        if not video_filename:
            raise ComfyUIError("No video output found in ComfyUI history")

        # Download video
        video_bytes = await self.get_output_video(video_filename, subfolder=subfolder)
        output_path = Path(f"output/comfyui_{prompt_id}.mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(video_bytes)
        return output_path
