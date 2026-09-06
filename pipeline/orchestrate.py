"""End-to-end: topic -> script -> 3 clips -> composited MP4 -> (optional) YouTube.

Every stage caches into output/<episode_id>/ so re-running resumes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .compositor import build as composite
from .higgsfield_client import HiggsfieldClient, HiggsfieldSettings
from .schema import Episode
from .script_writer import write_episode

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, val = line.partition("=")
            import os

            os.environ.setdefault(k.strip(), val.strip())


def run(topic: str, *, dry_run: bool, force_script: bool,
        publish: bool, publish_at: str | None) -> Path:
    _load_dotenv()
    cfg = load_config()

    # 1. script -------------------------------------------------------------
    stub_id = "".join(c if c.isalnum() else "-" for c in topic.lower())[:40].strip("-")
    ep_dir = ROOT / "output" / (stub_id or "episode")
    ep_dir.mkdir(parents=True, exist_ok=True)
    script_path = ep_dir / "episode.json"

    if dry_run and not script_path.exists() and "ANTHROPIC_API_KEY" not in _env():
        episode = _demo_episode(topic, stub_id)
        script_path.write_text(json.dumps(episode.to_json(), indent=2))
        print(f"[script] no API key — wrote demo episode to {script_path}")
    else:
        episode = write_episode(
            topic, script_path,
            model=_env().get("SCRIPT_MODEL"), force=force_script,
        )
        print(f"[script] '{episode.title}' -> {script_path}")

    # episode_id may differ from the stub; keep everything in one dir anyway
    clips_dir = ep_dir / "clips"

    # 2. clips ------------------------------------------------------------
    hs = HiggsfieldSettings(
        video_model=cfg["higgsfield"]["video_model"],
        poll_interval_seconds=cfg["higgsfield"]["poll_interval_seconds"],
        timeout_seconds=cfg["higgsfield"]["timeout_seconds"],
        max_retries=cfg["higgsfield"]["max_retries"],
        width=cfg["video"]["width"],
        height=cfg["video"]["height"],
        fps=cfg["video"]["fps"],
        soul_character=cfg["soul"]["character"],
        soul_fallback=cfg["soul"]["fallback_description"],
        environment=cfg["environment"],
    )
    client = HiggsfieldClient(hs, dry_run=dry_run)
    for clip in episode.clips:
        print(f"[clip] {clip.role}: {clip.id}")
        client.generate_clip(clip, clips_dir)

    # 3. composite ------------------------------------------------------
    final = ep_dir / f"{episode.episode_id}.mp4"
    print("[composite] stitching + bubbles + audio...")
    composite(episode, clips_dir, cfg, final)
    print(f"[composite] -> {final}")

    # 4. publish ------------------------------------------------------
    if publish:
        if dry_run:
            print("[publish] skipped (--dry-run)")
        else:
            from .publisher import upload

            upload(final, title=episode.title, description=episode.description,
                   config=cfg, publish_at=publish_at)
    return final


def _env() -> dict:
    import os

    return os.environ


def _demo_episode(topic: str, stub_id: str) -> Episode:
    return Episode.from_json({
        "episode_id": stub_id or "demo",
        "topic": topic,
        "title": f"When {topic} drops...",
        "description": f"A little Roblox skit about {topic}. #roblox #meme #shorts",
        "clips": [
            {
                "id": "setup", "role": "setup", "duration": 4,
                "motion": "slow dolly-in",
                "prompt": "A blocky avatar strolls past a glass exhibition panel in a "
                          "quiet grey hall, hands in pockets.",
                "bubbles": [{"speaker": "Blocky", "text": "big update today huh",
                             "start": 1.2, "side": "left"}],
                "sfx": [{"name": "pop", "at": 1.2}],
            },
            {
                "id": "conversation", "role": "conversation", "duration": 4,
                "motion": "static two-shot",
                "prompt": "Two blocky avatars face each other in the grey hall, one "
                          "shrugs, the other tilts its head.",
                "bubbles": [
                    {"speaker": "Guest", "text": "they added weather", "start": 0.6, "side": "right"},
                    {"speaker": "Blocky", "text": "wait real weather", "start": 2.2, "side": "left"},
                ],
                "sfx": [{"name": "pop", "at": 0.6}, {"name": "pop", "at": 2.2}],
            },
            {
                "id": "punchline", "role": "punchline", "duration": 3,
                "motion": "quick zoom-out",
                "prompt": "A sudden cartoon thunderstorm erupts indoors, both blocky "
                          "avatars get soaked and freeze mid-pose.",
                "bubbles": [{"speaker": "Blocky", "text": "i was not ready", "start": 1.0, "side": "left"}],
                "sfx": [{"name": "impact", "at": 0.0}, {"name": "pop", "at": 1.0}],
            },
        ],
    })


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True)
    p.add_argument("--dry-run", action="store_true",
                   help="grey placeholder clips, no Higgsfield calls, $0")
    p.add_argument("--force-script", action="store_true",
                   help="re-ask Claude even if episode.json is cached")
    p.add_argument("--publish", action="store_true", help="upload to YouTube (private)")
    p.add_argument("--publish-at", default=None,
                   help="RFC3339 UTC, e.g. 2026-09-10T17:00:00Z")
    args = p.parse_args(argv)

    final = run(
        args.topic,
        dry_run=args.dry_run,
        force_script=args.force_script,
        publish=args.publish,
        publish_at=args.publish_at,
    )
    print(f"\nDone: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
