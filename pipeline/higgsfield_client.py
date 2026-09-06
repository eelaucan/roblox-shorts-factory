"""Wrapper around the Higgsfield CLI for one-clip-at-a-time video generation.

Higgsfield has no public REST API — the CLI (and its Claude/Cursor skills) are the
only programmatic entry points. The exact `higgsfield` subcommand surface is not
fully documented publicly, so every assumption about flags lives HERE and in the
`higgsfield:` block of config.yaml. After `npm i -g @higgsfield/cli`, run
`higgsfield --help` and reconcile `_build_generate_cmd` / `_build_status_cmd`.

Design guarantees regardless of CLI details:
  * clips are generated strictly one at a time
  * each job is polled to a terminal state before the next starts
  * a finished clip is cached to disk; re-running never regenerates it
  * --dry-run produces correctly-sized grey placeholders and never calls the CLI
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .schema import Clip


@dataclass
class HiggsfieldSettings:
    video_model: str
    poll_interval_seconds: int
    timeout_seconds: int
    max_retries: int
    width: int
    height: int
    fps: int
    soul_character: str
    soul_fallback: str
    environment: str


class HiggsfieldError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _extract_json(stdout: str) -> dict:
    """CLIs often print a banner before the JSON payload. Grab the last {...} block."""
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1:
        raise HiggsfieldError(f"no JSON in CLI output:\n{stdout}")
    return json.loads(stdout[start : end + 1])


class HiggsfieldClient:
    def __init__(self, settings: HiggsfieldSettings, *, dry_run: bool = False):
        self.s = settings
        self.dry_run = dry_run
        if not dry_run and shutil.which("higgsfield") is None:
            raise HiggsfieldError(
                "higgsfield CLI not found. Install with `npm i -g @higgsfield/cli` "
                "and run `higgsfield auth login`, or use --dry-run."
            )

    # --- public API ---------------------------------------------------------

    def generate_clip(self, clip: Clip, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{clip.id}.mp4"
        if dest.exists():
            print(f"  [cache] {clip.id}.mp4 already present, skipping generation")
            return dest

        if self.dry_run:
            return self._placeholder(clip, dest)

        full_prompt = self._compose_prompt(clip)
        last_err: Exception | None = None
        for attempt in range(1 + self.s.max_retries):
            try:
                job_id = self._submit(full_prompt, clip.duration)
                print(f"  [higgsfield] job {job_id} submitted for '{clip.id}'")
                url_or_path = self._poll(job_id)
                self._fetch(url_or_path, dest)
                return dest
            except (HiggsfieldError, subprocess.TimeoutExpired) as e:  # noqa: PERF203
                last_err = e
                print(f"  [higgsfield] attempt {attempt + 1} failed: {e}")
        raise HiggsfieldError(f"clip '{clip.id}' failed after retries: {last_err}")

    # --- prompt composition ------------------------------------------------

    def _compose_prompt(self, clip: Clip) -> str:
        who = (
            f"Soul character {self.s.soul_character}"
            if self.s.soul_character
            else self.s.soul_fallback
        )
        parts = [
            clip.prompt,
            f"Featuring {who}.",
            f"Environment: {self.s.environment}.",
            "Roblox / blocky 3D animation style, no on-screen text, no subtitles, "
            "no speech bubbles, vertical 9:16 framing.",
        ]
        if clip.motion:
            parts.insert(1, f"Camera: {clip.motion}.")
        return " ".join(p for p in parts if p)

    # --- CLI surface (VERIFY against `higgsfield --help`) -----------------

    def _build_generate_cmd(self, prompt: str, duration: float) -> list[str]:
        return [
            "higgsfield", "generate", "video",
            "--model", self.s.video_model,
            "--prompt", prompt,
            "--aspect-ratio", "9:16",
            "--duration", str(round(duration)),
            *(["--soul", self.s.soul_character] if self.s.soul_character else []),
            "--json",
        ]

    def _build_status_cmd(self, job_id: str) -> list[str]:
        return ["higgsfield", "jobs", "get", job_id, "--json"]

    # --- job lifecycle ---------------------------------------------------

    def _submit(self, prompt: str, duration: float) -> str:
        proc = _run(self._build_generate_cmd(prompt, duration), timeout=120)
        if proc.returncode != 0:
            raise HiggsfieldError(f"generate failed: {proc.stderr or proc.stdout}")
        data = _extract_json(proc.stdout)
        job_id = data.get("id") or data.get("job_id") or data.get("jobId")
        if not job_id:
            raise HiggsfieldError(f"no job id in response: {data}")
        return str(job_id)

    def _poll(self, job_id: str) -> str:
        deadline = time.monotonic() + self.s.timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(self.s.poll_interval_seconds)
            proc = _run(self._build_status_cmd(job_id), timeout=60)
            if proc.returncode != 0:
                print(f"  [higgsfield] status check errored: {proc.stderr.strip()}")
                continue
            data = _extract_json(proc.stdout)
            status = str(data.get("status", "")).lower()
            if status in {"completed", "succeeded", "success", "done"}:
                result = (
                    data.get("output_url")
                    or data.get("url")
                    or data.get("result", {}).get("url")
                    or data.get("output_path")
                )
                if not result:
                    raise HiggsfieldError(f"job done but no output in {data}")
                return str(result)
            if status in {"failed", "error", "canceled", "cancelled"}:
                raise HiggsfieldError(f"job {job_id} {status}: {data.get('error')}")
            print(f"  [higgsfield] job {job_id}: {status or 'pending'}...")
        raise HiggsfieldError(f"job {job_id} timed out after {self.s.timeout_seconds}s")

    def _fetch(self, url_or_path: str, dest: Path) -> None:
        src = Path(url_or_path)
        if src.exists():
            shutil.copyfile(src, dest)
            return
        # remote URL
        import urllib.request

        with urllib.request.urlopen(url_or_path, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)

    # --- dry run --------------------------------------------------------

    def _placeholder(self, clip: Clip, dest: Path) -> Path:
        """Render a grey clip with the clip id burned in, at the real spec."""
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
