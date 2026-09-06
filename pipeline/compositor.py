"""Stitch the Higgsfield clips, overlay chat bubbles, layer audio, export 9:16.

Replaces the manual CapCut step. MoviePy 2.x API.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from .bubbles import BubbleStyle, render_bubble
from .schema import Episode


def _db(factor_db: float) -> float:
    return 10 ** (factor_db / 20)


def _fit(clip: VideoFileClip, w: int, h: int) -> VideoFileClip:
    """Cover-crop the source to exactly w x h."""
    scale = max(w / clip.w, h / clip.h)
    clip = clip.resized(scale)
    x1 = (clip.w - w) / 2
    y1 = (clip.h - h) / 2
    return clip.cropped(x1=x1, y1=y1, x2=x1 + w, y2=y1 + h)


def _bubble_clip(png: np.ndarray, start: float, end: float, y_center: int,
                 vw: int, pop: float) -> ImageClip:
    dur = max(0.1, end - start)
    base = ImageClip(png, transparent=True).with_start(start).with_duration(dur)

    if pop > 0:
        def scale(t: float) -> float:
            if t >= pop:
                return 1.0
            p = t / pop
            # ease-out-back overshoot
            return max(0.05, 1 + 2.7 * (p - 1) ** 3 + 1.7 * (p - 1) ** 2)

        base = base.resized(scale)

    bh = png.shape[0]
    return base.with_position(("center", y_center - bh // 2))


def build(episode: Episode, clips_dir: Path, config: dict, out_path: Path) -> Path:
    v = config["video"]
    vw, vh, fps = v["width"], v["height"], v["fps"]
    bcfg = config["bubbles"]
    acfg = config["audio"]

    style = BubbleStyle(
        font=bcfg["font"],
        font_size=bcfg["font_size"],
        text_color=tuple(bcfg["text_color"]),
        bubble_color=tuple(bcfg["bubble_color"]),
        outline_color=tuple(bcfg["outline_color"]),
        outline_width=bcfg["outline_width"],
        corner_radius=bcfg["corner_radius"],
        padding=tuple(bcfg["padding"]),
        max_width_px=int(vw * bcfg["max_width_frac"]),
    )
    bubble_y = int(vh * (1 - bcfg["margin_bottom_frac"]))
    pop = float(bcfg["pop_in_seconds"])

    segments: list[VideoFileClip] = []
    offsets: list[float] = []
    t = 0.0
    for clip in episode.clips:
        src = clips_dir / f"{clip.id}.mp4"
        if not src.exists():
            raise FileNotFoundError(f"missing generated clip: {src}")
        seg = _fit(VideoFileClip(str(src)), vw, vh)
        segments.append(seg)
        offsets.append(t)
        t += seg.duration
    total = t

    base = concatenate_videoclips(segments, method="compose")

    overlays: list[ImageClip] = []
    pop_events: list[float] = []
    impact_events: list[float] = []
    for clip, off in zip(episode.clips, offsets):
        for b in clip.bubbles:
            png = np.array(render_bubble(b.text, b.speaker, style, b.side))
            overlays.append(
                _bubble_clip(png, off + b.start, off + b.end, bubble_y, vw, pop)
            )
        for s in clip.sfx:
            (pop_events if s.name == "pop" else impact_events).append(off + s.at)

    video = CompositeVideoClip([base, *overlays], size=(vw, vh)).with_duration(total)

    # --- audio -----------------------------------------------------------
    tracks: list = []
    if video.audio is not None:
        tracks.append(video.audio)

    music_path = Path(acfg["music"])
    if music_path.exists():
        music = AudioFileClip(str(music_path))
        music = _loop_audio(music, total).with_volume_scaled(_db(acfg["music_gain_db"]))
        tracks.append(music)

    tracks += _sfx_hits(acfg.get("pop_sfx"), pop_events, total, 1.0)
    tracks += _sfx_hits(acfg.get("impact_sfx"), impact_events, total, _db(acfg["impact_gain_db"]))

    if tracks:
        video = video.with_audio(CompositeAudioClip(tracks))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(out_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
    )
    return out_path


def _loop_audio(clip: AudioFileClip, target: float) -> AudioFileClip:
    if clip.duration >= target:
        return clip.subclipped(0, target)
    reps = math.ceil(target / clip.duration)
    return concatenate_audio([clip] * reps).subclipped(0, target)


def concatenate_audio(clips: list) -> AudioFileClip:
    from moviepy import concatenate_audioclips

    return concatenate_audioclips(clips)


def _sfx_hits(path: str | None, times: list[float], total: float, vol: float) -> list:
    if not path or not Path(path).exists():
        return []
    hits = []
    for at in times:
        if at >= total:
            continue
        one = AudioFileClip(path).with_start(at).with_volume_scaled(vol)
        hits.append(one)
    return hits
