# Drop audio here (gitignored)

| file | what | notes |
|------|------|-------|
| `music.mp3` | background bed | looped automatically to video length, ducked to ~-18 dB |
| `pop.wav` | bubble appear | played at each bubble's start; keep it <300 ms |
| `impact.wav` | punchline hit | played at t=0 of clip 3 |

Filenames are configurable in `config.yaml` → `audio:`. Any missing file is simply
skipped (the video still renders, just without that layer). Use royalty-free / licensed
audio only — this pipeline can upload to YouTube.
