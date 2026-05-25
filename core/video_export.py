from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import cv2


def _get_ffmpeg_exe() -> str | None:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def _reencode_ffmpeg_h264(src: Path, dst: Path) -> bool:
    ffmpeg = _get_ffmpeg_exe()
    if not ffmpeg:
        return False

    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False

    return dst.exists() and dst.stat().st_size > 0


def _reencode_opencv_h264(src: Path, dst: Path) -> bool:
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25

    writer = None
    for codec in ("avc1", "H264", "X264"):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        candidate = cv2.VideoWriter(str(dst), fourcc, fps, (width, height))
        if candidate.isOpened():
            writer = candidate
            break
        candidate.release()

    if writer is None:
        cap.release()
        return False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
    finally:
        cap.release()
        writer.release()

    return dst.exists() and dst.stat().st_size > 0


def finalize_video_for_web(path: Path) -> Path:
    """Перекодирует видео в H.264 для воспроизведения в браузере (st.video)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return path

    temp_out = path.with_name(f"{path.stem}_web{path.suffix}")
    converted = _reencode_ffmpeg_h264(path, temp_out) or _reencode_opencv_h264(
        path, temp_out
    )
    if converted:
        os.replace(temp_out, path)
    elif temp_out.exists():
        temp_out.unlink(missing_ok=True)

    return path
