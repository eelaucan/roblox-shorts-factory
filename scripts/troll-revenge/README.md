# Troll Revenge — 3 shooting scripts

Format: **Troll Revenge**. A troll wrecks the player in the cold open; the player
comes back with a mechanically clever, escalating payback; the troll rage-quits.
Each script is timed to fill a fast 1:00–2:00 vertical short.

| # | Name | Game / setting | Revenge is executed via |
|---|------|----------------|-------------------------|
| 01 | Sky Jail | Classic Baseplate, unrestricted F3X | **Construction** — box, seal, anchor, weld a rocket, launch |
| 02 | Landlord From Hell | Brookhaven 🏡RP | **Environment / social** — owner door control, house editor, prop-pinning, a roleplay arrest |
| 03 | Ant Farm | Kohl's Admin House (HD Admin) | **Admin + scaling** — `;god`, `;freeze`, `;size 0.2`, `;size me 10`, `;jail` |

The three revenges never repeat a method: 01 builds a machine, 02 weaponizes a
room and other players, 03 abuses command permissions and relative scale.

## Shared production spec

- **Canvas:** 1080×1920, 9:16, export 30 fps min (60 for the montages).
- **Hook:** first frame is peak chaos or the trap already sprung — never an intro card. First spoken word by 0:00.8.
- **Cut discipline:** no shot longer than ~2.0 s except the deliberate "relief holds" (marked). Montage shots 0.3–0.5 s, cut on the beat.
- **Captions:** burned-in, word-by-word, TikTok style — white, 8 px black stroke, slight pop-in scale (1.0→1.08→1.0 over 3 frames). Bottom third, above the UI.
- **Loop-bait:** last frame ≈ first frame so autoplay loop is seamless. Called out per script.
- **Flashing-lights sticker** on any strobe sequence (script 02) — good practice and it reads as a meme.

### Voiceover (TTS)

| Script | Voice (ElevenLabs) | Direction |
|--------|--------------------|-----------|
| 01 Sky Jail | "Brian" | dry, done-with-it, slow burn |
| 02 Landlord | "Sarah" or "Brian" | sarcastic, sing-song "customer service" tone |
| 03 Ant Farm | "Adam" | deep, ominous movie-trailer narrator |

Keep VO under ~14 words per beat. Let SFX carry the rest.

### Music (royalty-free)

- **01:** low phonk bed — YouTube Audio Library "Phonk" tag, or Kevin MacLeod *"Bad Ideas"*. −18 dB under VO, drop to −8 dB on the launch and the "GG" reveal.
- **02:** bright comedic — Kevin MacLeod *"Investigations"* / *"Carefree"*; the troll's in-game radio track doubles as a diegetic gag.
- **03:** hard phonk / hardstyle drop — Audio Library "Phonk", cut to a bare kick for the `;jail` snap, full drop on the walk-away.

### Meme SFX kit (manual, per-cut)

classic Roblox **OOF** · **Vine boom** · record scratch · "bruh" · MLG airhorn ·
slide-whistle down (shrink) · power-up swell (grow) · sad trombone · camera-shutter ·
"W" ding · Minecraft click (for on-screen countdowns) · ice-crack (freeze).

## Turning a script into a pipeline episode

These are human shooting scripts. To auto-generate the b-roll, condense each beat's
**Visual** line into a textless Higgsfield prompt and drop it into an
`episodes/*.json` spec (see `episodes/mom-button.json`), then let the compositor add
the captions + SFX from the **Editing** / **Audio** lanes.
