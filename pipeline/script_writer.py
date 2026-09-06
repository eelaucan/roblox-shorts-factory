"""Ask Claude for an episode spec via tool use, validate it, cache it."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .schema import EPISODE_TOOL_SCHEMA, Episode

SYSTEM = """\
You write short vertical (9:16) Roblox meme videos in the style of viral Roblox
"exhibition hall" / "elevator" shorts. Two blocky avatars, deadpan delivery,
a mundane setup that escalates to one absurd punchline.

Structure — exactly three clips:
  1. setup        (~3-4s) establishing shot, one avatar, a normal beat
  2. conversation (~3-5s) both avatars, a short exchange that plants the joke
  3. punchline    (~2-4s) the absurd payoff — a visual gag, not just a line

Hard rules:
- Clip prompts are TEXTLESS and speechless. Describe only what the camera sees:
  framing, motion, lighting, the blocky characters' actions. Speech bubbles and
  sound are added in post — never request on-screen text.
- Keep the environment identical across all three clips for continuity.
- Dialogue lines <= 60 characters, lowercase, no punctuation flourish — chat-bubble voice.
- Put a "pop" sfx at each bubble's start. Put one "impact" sfx at t=0 of the punchline clip.
- Total runtime 8-14 seconds.
Return the result by calling emit_episode. Do not write prose.
"""


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")[:60]


def write_episode(topic: str, cache_path: Path, *, model: str | None = None,
                  force: bool = False) -> Episode:
    if cache_path.exists() and not force:
        return Episode.from_json(json.loads(cache_path.read_text()))

    from anthropic import Anthropic  # imported lazily so --dry-run works offline-ish

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = model or os.environ.get("SCRIPT_MODEL", "claude-sonnet-5")

    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM,
        tools=[EPISODE_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "emit_episode"},
        messages=[{
            "role": "user",
            "content": f"Write a Roblox meme short about: {topic}",
        }],
    )

    block = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    data = dict(block.input)
    data.setdefault("topic", topic)
    if not data.get("episode_id"):
        data["episode_id"] = _slug(topic)

    episode = Episode.from_json(data)  # raises on bad structure

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(episode.to_json(), indent=2))
    return episode
