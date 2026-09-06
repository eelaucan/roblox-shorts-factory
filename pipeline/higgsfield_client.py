"""Generate the textless clips via the real Higgsfield CLI (`@higgsfield/cli`).

Higgsfield has no public REST API — the CLI is the programmatic entry point.
Verified surface (CLI 1.1.24):

    higgsfield --json generate create <job_type> --prompt "..." \
        --aspect-ratio 9:16 --duration 5 --sound false \
        --wait --wait-timeout 20m --wait-interval 10s

`--wait` blocks until the job finishes, so we don't hand-roll polling. The job
JSON is scanned recursively for the output .mp4 URL.

Guarantees:
  * one clip generated at a time
  * a finished clip is cached to disk; re-running never regenerates it
  * --dry-run produces correctly-sized grey placeholders, never calls the CLI
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .schema import Clip

_MP4_RE = re.compile(r"https?://[^\s\"']+\.mp4[^\s\"']*", re.I)


@dataclass
class HiggsfieldSettings:
    video_model: str
    aspect_ratio: str
    duration: int
    sound: bool
    wait_timeout: str
    wait_interval: str
    max_retries: int
    width: int
    height: int
    fps: int
    soul_character: str
    soul_fallback: str
    environment: str


class HiggsfieldError(RuntimeError):
    pass


def _extract_mp4(obj) -> str | None:
    """Find the first .mp4 URL anywhere in a nested JSON structure."""
    if isinstance(obj, str):
        m = _MP4_RE.search(obj)
        return m.group(0) if m else None
    if isinstance(obj, dict):
        for v in obj.values():
            if (found := _extract_mp4(v)):
                return found
    if isinstance(obj, list):
        for v in obj:
            if (found := _extract_mp4(v)):
                return found
    return None


class HiggsfieldClient:
    def __init__(self, settings: HiggsfieldSettings, *, dry_run: bool = False):
        self.s = settings
        self.dry_run = dry_run
        if not dry_run and shutil.which("higgsfield") is None:
            raise HiggsfieldError(
                "higgsfield CLI not found. `npm i -g @higgsfield/cli` then "
                "`higgsfield auth login`, or use --dry-run."
            )

    # --- public API -------------------------------------------------------

    def generate_clip(self, clip: Clip, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{clip.id}.mp4"
        if dest.exists():
            print(f"  [cache] {clip.id}.mp4 present, skipping generation")
            return dest

        if self.dry_run:
            return self._placeholder(clip, dest)

        prompt = self._compose_prompt(clip)
        last_err: Exception | None = None
        for attempt in range(1 + self.s.max_retries):
            try:
                url = self._generate_and_wait(prompt)
                print(f"  [higgsfield] output: {url}")
                self._download(url, dest)
                return dest
            except (HiggsfieldError, subprocess.SubprocessError) as e:
                last_err = e
                print(f"  [higgsfield] attempt {attempt + 1} failed: {e}")
        raise HiggsfieldError(f"clip '{clip.id}' failed after retries: {last_err}")

    def estimate_cost(self, clip: Clip) -> float | None:
        if self.dry_run:
            return 0.0
        cmd = [
            "higgsfield", "--json", "generate", "cost", self.s.video_model,
            "--prompt", self._compose_prompt(clip),
            "--aspect-ratio", self.s.aspect_ratio,
            "--duration", str(self.s.duration),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return None
        try:
            return float(json.loads(proc.stdout).get("credits"))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    # --- prompt ----------------------------------------------------------

    def _compose_prompt(self, clip: Clip) -> str:
        who = self.s.soul_character or self.s.soul_fallback
        parts = [
            clip.prompt,
            f"Consistent main character: {who}." if who else "",
            f"Environment: {self.s.environment}.",
            "Roblox blocky 3D animation style. No on-screen text, no subtitles, "
            "no speech bubbles, no captions. Vertical 9:16 framing.",
        ]
        if clip.motion:
            parts.insert(1, f"Camera: {clip.motion}.")
        return " ".join(p for p in parts if p)

    # --- CLI -----------------------------------------------------------

    def _generate_and_wait(self, prompt: str) -> str:
        cmd = [
            "higgsfield", "--json", "generate", "create", self.s.video_model,
            "--prompt", prompt,
            "--aspect-ratio", self.s.aspect_ratio,
            "--duration", str(self.s.duration),
            "--sound", "true" if self.s.sound else "false",
            "--wait",
            "--wait-timeout", self.s.wait_timeout,
            "--wait-interval", self.s.wait_interval,
        ]
        # generous ceiling above --wait-timeout so the process isn't killed early
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
        blob = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0:
            raise HiggsfieldError(f"generate create failed:\n{blob.strip()}")

        url = _extract_mp4(_safe_json(proc.stdout)) or _extract_mp4(blob)
        if not url:
            raise HiggsfieldError(f"no .mp4 URL in CLI output:\n{blob.strip()}")
        return url

    def _download(self, url: str, dest: Path) -> None:
        tmp = dest.with_suffix(".part")
        req = urllib.request.Request(url, headers={"User-Agent": "roblox-shorts-factory"})
        with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(dest)

    # --- dry run -----------------------------------------------------

    def _placeholder(self, clip: Clip, dest: Path) -> Path:
        import numpy as np
        from moviepy import ImageClip

        shade = {"setup": 90, "conversation": 110, "punchline": 70}[clip.role]
        frame = np.full((self.s.height, self.s.width, 3), shade, dtype="uint8")
        (
            ImageClip(frame)
            .with_duration(clip.duration)
            .with_fps(self.s.fps)
            .write_videofile(str(dest), codec="libx264", audio=False, logger=None)
        )
        print(f"  [dry-run] placeholder {clip.id}.mp4 ({clip.duration}s)")
        return dest


def _safe_json(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}
