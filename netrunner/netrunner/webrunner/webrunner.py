#!/usr/bin/env python3
import json
import time
import socket
import urllib.request
import urllib.error
import os
from urllib.parse import urlparse

DEVICE_ID = os.environ.get("DEVICE_ID", "unknown")
DEVICE_KEY = os.environ.get("DEVICE_KEY", "")
CLOUD_BASE = os.environ.get("CLOUD_BASE", "").rstrip("/")
CONFIG_FILE = os.environ.get("CONFIG_FILE", "/app/config.json")
DATA_DIR = os.environ.get("DATA_DIR", "/data")

DEFAULT_INTERVAL = 300

HEADERS = {
    "content-type": "application/json",
    "x-device-id": DEVICE_ID,
    "x-device-key": DEVICE_KEY,
}

state = {
    "urls": [],
    "interval_seconds": DEFAULT_INTERVAL,
}

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_json(url, payload, timeout=10):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout):
        pass

def load_cloud_config():
    url = f"{CLOUD_BASE}/api/device-config?device_id={DEVICE_ID}&_t={int(time.time())}"
    try:
        cfg = fetch_json(url)
        if isinstance(cfg, dict) and "config" in cfg:
            cfg = cfg["config"]

        state["urls"] = cfg.get("urls") or []
        state["interval_seconds"] = int(
            cfg.get("interval_seconds")
            or cfg.get("interval_s")
            or DEFAULT_INTERVAL
        )

        print(f"[CFG] loaded {len(state['urls'])} urls, interval={state['interval_seconds']}s")
    except Exception as e:
        print(f"[CFG] failed to load cloud config: {e}")

def run_checks():
    ingest = f"{CLOUD_BASE}/api/measurements/ingest"

    while True:
        load_cloud_config()

        if not state["urls"]:
            print("[RUN] no urls configured — sleeping 10s")
            time.sleep(10)
            continue

        for url in state["urls"]:
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            dns_ms = 0
            http_ms = 0
            http_err = ""

            try:
                parsed = urlparse(url)
                host = parsed.hostname

                dns_start = time.time()
                socket.getaddrinfo(host, None)
                dns_ms = round((time.time() - dns_start) * 1000, 2)

                http_start = time.time()
                urllib.request.urlopen(url, timeout=10).read()
                http_ms = round((time.time() - http_start) * 1000, 2)

            except Exception as e:
                http_err = str(e)

            payload = {
                "device_id": DEVICE_ID,
                "ts_utc": ts,
                "url": url,
                "dns_ms": dns_ms,
                "http_ms": http_ms,
                "http_err": http_err,
            }

            try:
                post_json(ingest, payload)
            except Exception as e:
                print(f"[INGEST] failed: {e}")

        time.sleep(state["interval_seconds"])

if __name__ == "__main__":
    print(f"[BOOT] NetRunner starting for {DEVICE_ID}")
    run_checks()
