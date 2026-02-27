#!/usr/bin/env bash
set -euo pipefail

DASH="http://10.10.10.154:3000"
KEY_FILE="/home/mark/netrunner/device_key.txt"

# IMPORTANT: write directly to WebRunner's config file
OUT="/home/mark/netrunner/webrunner/config.json"

TMP="$(mktemp)"
KEY="$(cat "$KEY_FILE")"

# Fetch + extract only .config
curl -fsS "$DASH/api/device/config" -H "x-device-key: $KEY" \
  | jq -e '.config' > "$TMP"

# Replace only if changed
if [ -f "$OUT" ] && cmp -s "$TMP" "$OUT"; then
  echo "No config change."
  rm -f "$TMP"
  exit 0
fi

mv "$TMP" "$OUT"
echo "Updated $OUT"

# Restart WebRunner container (compose in the webrunner directory)
cd /home/mark/netrunner/webrunner
docker compose restart || docker-compose restart
