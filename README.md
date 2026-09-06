# roblox-meme-pipeline

Zero-touch pipeline: **Claude writes the script → Higgsfield generates clean clips → MoviePy
composites bubbles + SFX → YouTube upload.**

```
script_writer.py     Anthropic API  -> episode spec (JSON, validated)
higgsfield_client.py Higgsfield CLI -> 3 textless .mp4 clips (with polling)
compositor.py        MoviePy+Pillow -> stitch, Roblox chat bubbles, SFX, 9:16 export
publisher.py         YouTube Data API v3 -> upload / schedule (opt-in, never auto-publishes)
orchestrate.py       runs the above end to end
```

## Status of external dependencies on this machine

| Tool | Needed for | Installed? |
|------|------------|-----------|
| Python 3.13 | everything | ✅ |
| Homebrew | installing the below | ✅ |
| ffmpeg | MoviePy encode/decode | ❌ `brew install ffmpeg` |
| Node + npm | Higgsfield CLI | ❌ `brew install node` |
| `@higgsfield/cli` | clip generation | ❌ `npm i -g @higgsfield/cli` |
| Higgsfield paid plan | CLI auth | you handle `higgsfield auth login` (opens browser) |

Run `scripts/check_setup.sh` any time to see what's still missing.

## Setup

```bash
cd ~/roblox-meme-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# system deps (asks for nothing sensitive, but review first)
brew install ffmpeg node
npm i -g @higgsfield/cli
higgsfield auth login          # <- you do this; browser sign-in to your paid account
npx skills add higgsfield-ai/skills

cp .env.example .env           # then fill in ANTHROPIC_API_KEY
```

Drop audio into `assets/audio/` (see `assets/audio/README.md`) and a `.ttf` into
`assets/fonts/` (a chunky rounded font reads most "Roblox"; config points at it).

## Run

```bash
# 1. dry run — writes a script + fake clips, exercises the compositor, spends $0
python -m pipeline.orchestrate --topic "the 2026 Roblox update" --dry-run

# 2. real clips, no upload
python -m pipeline.orchestrate --topic "the 2026 Roblox update"

# 3. real clips + schedule the upload (private until the scheduled time)
python -m pipeline.orchestrate --topic "the 2026 Roblox update" \
    --publish --publish-at 2026-09-10T17:00:00Z
```

Every stage caches to `output/<episode_id>/`, so a failed run resumes instead of
re-generating clips you already paid for.

## The credit-safety model

- `--dry-run` never touches Higgsfield. It synthesises grey placeholder clips at the
  right resolution/duration so you can iterate on bubbles, timing and audio for free.
- Real runs generate one clip at a time and **poll** the CLI job to completion before
  starting the next, so a crash mid-run wastes at most one clip.
- `publisher.py` uploads as `private` and only sets `publishAt`. Nothing ever goes
  public without you flipping it in YouTube Studio.
