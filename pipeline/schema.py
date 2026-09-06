"""Episode spec: the JSON contract between the script writer and everything downstream.

Keep this small and strict. If the LLM returns something that doesn't validate,
we want a loud error before spending a cent on Higgsfield.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ClipRole = Literal["setup", "conversation", "punchline"]
BubbleSide = Literal["left", "right"]


@dataclass
class Bubble:
    speaker: str
    text: str
    start: float          # seconds from the start of this clip
    end: float            # seconds; bubble disappears at the cut if omitted
    side: BubbleSide = "left"

    @staticmethod
    def from_json(d: dict[str, Any], clip_duration: float) -> "Bubble":
        start = float(d["start"])
        end = float(d.get("end", clip_duration))
        return Bubble(
            speaker=str(d["speaker"]),
            text=str(d["text"]).strip(),
            start=start,
            end=min(end, clip_duration),
            side=d.get("side", "left"),
        )


@dataclass
class Sfx:
    name: Literal["pop", "impact"]
    at: float             # seconds from the start of this clip

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Sfx":
        return Sfx(name=d["name"], at=float(d["at"]))


@dataclass
class Clip:
    id: str
    role: ClipRole
    prompt: str           # textless visual prompt for Higgsfield
    duration: float       # seconds
    motion: str = ""
    bubbles: list[Bubble] = field(default_factory=list)
    sfx: list[Sfx] = field(default_factory=list)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Clip":
        duration = float(d["duration"])
        return Clip(
            id=str(d["id"]),
            role=d["role"],
            prompt=str(d["prompt"]).strip(),
            duration=duration,
            motion=str(d.get("motion", "")),
            bubbles=[Bubble.from_json(b, duration) for b in d.get("bubbles", [])],
            sfx=[Sfx.from_json(s) for s in d.get("sfx", [])],
        )


@dataclass
class Episode:
    episode_id: str
    topic: str
    title: str            # YouTube title
    description: str       # YouTube description
    clips: list[Clip]

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Episode":
        clips = [Clip.from_json(c) for c in d["clips"]]
        ep = Episode(
            episode_id=str(d["episode_id"]).strip(),
            topic=str(d["topic"]).strip(),
            title=str(d["title"]).strip(),
            description=str(d["description"]).strip(),
            clips=clips,
        )
        ep.validate()
        return ep

    def validate(self) -> None:
        if not self.episode_id or "/" in self.episode_id or " " in self.episode_id:
            raise ValueError(f"episode_id must be a safe slug, got {self.episode_id!r}")
        roles = [c.role for c in self.clips]
        if roles != ["setup", "conversation", "punchline"]:
            raise ValueError(
                "expected exactly 3 clips with roles "
                f"[setup, conversation, punchline], got {roles}"
            )
        for c in self.clips:
            if not 1.0 <= c.duration <= 15.0:
                raise ValueError(f"clip {c.id}: duration {c.duration}s out of 1-15s range")
            for b in c.bubbles:
                if b.start < 0 or b.start >= c.duration:
                    raise ValueError(f"clip {c.id}: bubble start {b.start} outside clip")
            for s in c.sfx:
                if not 0 <= s.at <= c.duration:
                    raise ValueError(f"clip {c.id}: sfx at {s.at} outside clip")

    def to_json(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "topic": self.topic,
            "title": self.title,
            "description": self.description,
            "clips": [
                {
                    "id": c.id,
                    "role": c.role,
                    "prompt": c.prompt,
                    "duration": c.duration,
                    "motion": c.motion,
                    "bubbles": [vars(b) for b in c.bubbles],
                    "sfx": [vars(s) for s in c.sfx],
                }
                for c in self.clips
            ],
        }


# JSON Schema handed to the model via tool use so it returns valid structure.
EPISODE_TOOL_SCHEMA: dict[str, Any] = {
    "name": "emit_episode",
    "description": "Return the full episode specification for one vertical Roblox meme short.",
    "input_schema": {
        "type": "object",
        "required": ["episode_id", "topic", "title", "description", "clips"],
        "properties": {
            "episode_id": {
                "type": "string",
                "description": "kebab-case slug, no spaces/slashes, e.g. '2026-update-elevator'",
            },
            "topic": {"type": "string"},
            "title": {"type": "string", "description": "YouTube title, <= 90 chars, punchy"},
            "description": {"type": "string", "description": "2-4 sentences + hashtags"},
            "clips": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["id", "role", "prompt", "duration"],
                    "properties": {
                        "id": {"type": "string"},
                        "role": {"enum": ["setup", "conversation", "punchline"]},
                        "prompt": {
                            "type": "string",
                            "description": (
                                "TEXTLESS cinematic visual prompt. Describe camera, action, "
                                "environment. NEVER ask for on-screen text or speech bubbles "
                                "— those are added later."
                            ),
                        },
                        "duration": {"type": "number", "minimum": 2, "maximum": 8},
                        "motion": {"type": "string"},
                        "bubbles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["speaker", "text", "start"],
                                "properties": {
                                    "speaker": {"type": "string"},
                                    "text": {"type": "string", "description": "<= 60 chars"},
                                    "start": {"type": "number"},
                                    "end": {"type": "number"},
                                    "side": {"enum": ["left", "right"]},
                                },
                            },
                        },
                        "sfx": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "at"],
                                "properties": {
                                    "name": {"enum": ["pop", "impact"]},
                                    "at": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}
