# AyoGaming-style Shorts — 4 scripts

A different lane from `../troll-revenge/`. These are **20–35 second** silent
emote-stories and engagement-bait, built for the YouTube Shorts algorithm the way
channels like AyoGamingRoblox run it: no mic, big readable text, sad piano that
flips to a hype drop, and an ending that *forces* a like/comment/follow.

| # | Title | Format | Length | Primary trigger |
|---|-------|--------|--------|-----------------|
| A1 | The Poorest Bacon Got a GLOW UP 🥹✨ | Emotional underdog glow-up | ~33 s | parasocial protectiveness + music-switch dopamine |
| A2 | Your Roblox Glow Up If You… ✨👀 | "Your [X] if you…" wheel | ~22 s | forced comment ("comment what you got") |
| A3 | Which Bacon Do You SAVE?! 😥💔 | "Choose One" dilemma | ~20 s | binary like-vs-comment vote + cliffhanger |
| A4 | Mom Can You Send Me 4 Robux 🤑 (Lyric Prank) | Lyric prank on a stranger | ~25 s | in-group payoff ("what song is this") |

## The formula (what these 4 are built on)

**Themes that always work**
- **Underdog:** innocent Bacon Hair vs. edgy rich "Slender". Viewers auto-root for the Bacon.
- **High emotion:** loss, loneliness, being ignored — told in 30 seconds with emotes + text + sad piano.
- **Wholesomeness:** someone stands up for the victim; kindness after cruelty. This beat is what gets *shared*.

**Aesthetic**
- Bright colors, **zoomed-in on faces** for every reaction.
- On-screen text is huge, high-contrast, bottom third — never rely on Roblox chat bubbles.
- Titles: short, curiosity-gap, **2–3 emojis**. "Bacons are being DELETED 😥💔", "She COPIED my art.. 😥❤️".

**Sound design (no mic needed)**
- Sad piano for the emotional stretch (YouTube Audio Library "Sad Piano", or Kevin MacLeod *"Reflections"* / *"Doh De Oh"* for lighter beats).
- Upbeat trending phonk/pop for the glow-up / reveal — switch on the exact drop frame.
- Meme punctuation: classic **Oof**, **Vine Boom** — but only for comedy beats; the sad beats get a soft thud, not an Oof.

**Editing (CapCut / Premiere)**
- If nothing interesting happens in the first **3 seconds**, they scroll. Frame 1 = the emotional image or the hook question.
- Cut every dead second — no walking, no typing delays. Reaction shots 0.4–0.8 s.
- Loop-bait: last frame mirrors the first (same framing, changed outcome).

**Production**
- Film in **Roblox Studio** or a **private server** (Brookhaven, Catalog Avatar Creator, Natural Disaster Survival) for camera + lighting control.
- Actors = **a friend or an alt account on your phone** while you record on PC. One plays the Slender/bully, one the Bacon.
- Emotes do the acting: `laugh`, `point`, `sit`, `cry` (sad pose), `surprised`, `wave`, `stop`.

**Cadence**
- Batch-record ~10 mini-stories on a Saturday → edit Sunday → schedule **1–2/day**. The Shorts algorithm rewards daily high-retention uploads.

## Folding into the pipeline

Each beat's **Visual** line condenses into a textless Higgsfield prompt for
`episodes/*.json`; the **Text** and **Editing** lanes become the compositor's
caption + SFX track. The music-switch timestamp is the one hard sync point.
