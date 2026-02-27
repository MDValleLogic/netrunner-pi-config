#!/bin/sh
set -e

# --- Device identity (from /api/devices/register response) ---
DEVICE_ID="pi-e79ce0af-b227-4c91-8e34-3437cadcf95c"
DEVICE_KEY="7JhEtvegJDQvAepiqNhvtbJiofWAd54A"

# --- Cloud endpoint and local config target ---
CLOUD_URL="https://netrunner-dashboard.vercel.app/api/device-config"
CONFIG_FILE="/home/mark/netrunner/webrunner/config.json"
TMP_FILE="/tmp/config.json"

echo "[SYNC] fetching config from cloud..."

# Fetch cloud config (authenticated)
curl -sf "$CLOUD_URL?device_id=$DEVICE_ID" \
  -H "x-device-id: $DEVICE_ID" \
  -H "x-device-key: $DEVICE_KEY" \
  > "$TMP_FILE" || exit 0

# Validate: ensure cloud returned urls under .config.urls
if ! jq -e '.config.urls | length > 0' "$TMP_FILE" >/dev/null 2>&1; then
  echo "[SYNC] no urls in cloud config — skipping"
  exit 0
fi

# Normalize schema for WebRunner:
# WebRunner expects: { device_id, interval_s, urls }
# Cloud currently returns: { config: { device_id, interval_seconds, urls, ... } }
jq '.config | {
  device_id: .device_id,
  interval_s: (.interval_s // (.interval_seconds // 60)),
  urls: .urls
}' "$TMP_FILE" > "$CONFIG_FILE"

echo "[SYNC] config updated from cloud"
