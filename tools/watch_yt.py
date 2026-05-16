"""
watch_yt.py — Download a YouTube video and extract frames for analysis.

Usage: uv run watch_yt.py <youtube-url>

After this runs, Claude Code reads the frames directly and writes notes.md.
"""

import sys
import re
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
RESOURCES_DIR = SCRIPT_DIR / "resources" / "day 1"
FRAME_INTERVAL_SECONDS = 5


def sanitize_title(title: str) -> str:
    """Convert video title to safe Windows directory name."""
    safe = re.sub(r'[\\/*?:"<>|]', "", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:80]


def get_video_info(url: str) -> dict:
    """Fetch video metadata without downloading."""
    with YoutubeDL({"quiet": True}) as ydl:
        return ydl.extract_info(url, download=False)


def download_video_and_transcript(url: str, out_dir: Path) -> tuple[Path, Path | None]:
    """Download video to out_dir/video.mp4 and transcript to out_dir/transcript.vtt."""
    ydl_opts = {
        "outtmpl": str(out_dir / "video.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "quiet": False,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    video_path = out_dir / "video.mp4"
    transcript_path = None
    for vtt_file in out_dir.glob("video.*.vtt"):
        vtt_file.rename(out_dir / "transcript.vtt")
        transcript_path = out_dir / "transcript.vtt"
        break

    return video_path, transcript_path


def extract_frames(video_path: Path, out_dir: Path, interval: int = 5) -> list[Path]:
    """Extract one frame every `interval` seconds. Returns list of frame paths."""
    temp_pattern = str(out_dir / "frame_temp_%06d.jpg")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps=1/{interval}",
        "-q:v", "2",
        temp_pattern, "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    temp_frames = sorted(out_dir.glob("frame_temp_*.jpg"))
    final_frames = []
    for i, frame in enumerate(temp_frames):
        timestamp_s = (i + 1) * interval
        new_name = out_dir / f"frame_{timestamp_s:05d}s.jpg"
        frame.rename(new_name)
        final_frames.append(new_name)

    return final_frames


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run watch_yt.py <youtube-url>")
        sys.exit(1)

    url = sys.argv[1]

    print(f"Fetching video info: {url}")
    info = get_video_info(url)
    raw_title = info.get("title", "untitled")
    safe_title = sanitize_title(raw_title)

    out_dir = RESOURCES_DIR / safe_title
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading video and transcript...")
    video_path, transcript_path = download_video_and_transcript(url, out_dir)

    print("Extracting frames...")
    frames = extract_frames(video_path, out_dir, interval=FRAME_INTERVAL_SECONDS)

    print(f"\nREADY_FOR_ANALYSIS")
    print(f"TITLE: {raw_title}")
    print(f"OUT_DIR: {out_dir}")
    print(f"FRAMES: {len(frames)}")
    print(f"TRANSCRIPT: {transcript_path or 'none'}")
    for f in frames:
        print(f"FRAME: {f}")


if __name__ == "__main__":
    main()
