from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.pipeline.concatenator import concatenate_project


class TestConcatenateProject:
    async def test_multi_shot(self, tmp_path: Path) -> None:
        shot_paths = [tmp_path / "shot_00.mp4", tmp_path / "shot_01.mp4"]
        for p in shot_paths:
            p.write_bytes(b"fake")

        with (
            patch(
                "backend.pipeline.concatenator.normalize_video",
                new_callable=AsyncMock,
            ) as mock_norm,
            patch(
                "backend.pipeline.concatenator.concatenate_videos",
                new_callable=AsyncMock,
            ) as mock_concat,
        ):
            mock_norm.side_effect = lambda src, dst, **kw: Path(dst)
            mock_concat.side_effect = lambda paths, dst: Path(dst)

            result = await concatenate_project(
                project_id="proj-1",
                shot_paths=shot_paths,
                output_dir=tmp_path,
                width=1920,
                height=1080,
                fps=24,
            )

        assert result == tmp_path / "proj-1" / "final" / "final.mp4"
        assert mock_norm.call_count == 2
        mock_concat.assert_called_once()

    async def test_single_shot(self, tmp_path: Path) -> None:
        shot_path = tmp_path / "shot_00.mp4"
        shot_path.write_bytes(b"fake")

        with (
            patch(
                "backend.pipeline.concatenator.normalize_video",
                new_callable=AsyncMock,
            ) as mock_norm,
            patch(
                "backend.pipeline.concatenator.concatenate_videos",
                new_callable=AsyncMock,
            ) as mock_concat,
        ):
            mock_norm.side_effect = lambda src, dst, **kw: Path(dst)

            result = await concatenate_project(
                project_id="proj-1",
                shot_paths=[shot_path],
                output_dir=tmp_path,
            )

        assert result == tmp_path / "proj-1" / "final" / "final.mp4"
        # Single shot: normalize but don't concatenate
        mock_norm.assert_called_once()
        mock_concat.assert_not_called()

    async def test_custom_resolution(self, tmp_path: Path) -> None:
        shot_paths = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
        for p in shot_paths:
            p.write_bytes(b"fake")

        with (
            patch(
                "backend.pipeline.concatenator.normalize_video",
                new_callable=AsyncMock,
            ) as mock_norm,
            patch(
                "backend.pipeline.concatenator.concatenate_videos",
                new_callable=AsyncMock,
            ) as mock_concat,
        ):
            mock_norm.side_effect = lambda src, dst, **kw: Path(dst)
            mock_concat.side_effect = lambda paths, dst: Path(dst)

            await concatenate_project(
                project_id="proj-2",
                shot_paths=shot_paths,
                output_dir=tmp_path,
                width=1080,
                height=1920,
                fps=30,
            )

        # Verify resolution/fps passed through
        for c in mock_norm.call_args_list:
            assert c.kwargs["width"] == 1080
            assert c.kwargs["height"] == 1920
            assert c.kwargs["fps"] == 30
