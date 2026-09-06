#!/usr/bin/env bash
# What's installed / missing for the pipeline.
set -u
ok(){ printf "  \033[32m✓\033[0m %s\n" "$1"; }
no(){ printf "  \033[31m✗\033[0m %s — %s\n" "$1" "$2"; }

echo "system:"
command -v python3 >/dev/null && ok "python3 ($(python3 --version 2>&1 | awk '{print $2}'))" || no "python3" "install 3.11+"
command -v ffmpeg  >/dev/null && ok "ffmpeg"  || no "ffmpeg"  "brew install ffmpeg"
command -v node    >/dev/null && ok "node ($(node -v 2>/dev/null))" || no "node" "brew install node"
command -v npm     >/dev/null && ok "npm"     || no "npm" "comes with node"
command -v higgsfield >/dev/null && ok "higgsfield CLI" || no "higgsfield CLI" "npm i -g @higgsfield/cli"

echo "python packages:"
for m in anthropic moviepy PIL yaml; do
  python3 -c "import $m" 2>/dev/null && ok "$m" || no "$m" "pip install -r requirements.txt"
done
python3 -c "import googleapiclient" 2>/dev/null && ok "google-api-python-client (YouTube)" \
  || no "google-api-python-client" "optional; needed only for --publish"

echo "config:"
[ -f .env ] && ok ".env present" || no ".env" "cp .env.example .env and add ANTHROPIC_API_KEY"
[ -f assets/fonts/bubble.ttf ] && ok "bubble font" || no "assets/fonts/bubble.ttf" "drop a chunky rounded .ttf (falls back to default)"
for f in music.mp3 pop.wav impact.wav; do
  [ -f "assets/audio/$f" ] && ok "audio/$f" || no "assets/audio/$f" "optional; muted if absent"
done

echo
echo "higgsfield auth: run 'higgsfield auth login' (browser sign-in to your paid plan)"
