#!/usr/bin/env python3
import json, time, os, http.client, ssl, urllib.request
from urllib.parse import urlparse

DEVICE_ID  = os.environ.get("DEVICE_ID", "unknown")
DEVICE_KEY = os.environ.get("DEVICE_KEY", "")
CLOUD_BASE = os.environ.get("CLOUD_BASE", "").rstrip("/")
DEFAULT_INTERVAL = 3600

REGIONS = [
    { "region": "Northeast US",  "city": "New York, NY",    "url": "https://nyc.speedtest.clouvider.net/backend" },
    { "region": "Southeast US",  "city": "Atlanta, GA",     "url": "https://atl.speedtest.clouvider.net/backend" },
    { "region": "Midwest US",    "city": "Chicago, IL",     "url": "https://chispeed.sharktech.net/backend"      },
    { "region": "West Coast US", "city": "Los Angeles, CA", "url": "https://la.speedtest.clouvider.net/backend"  },
    { "region": "Europe",        "city": "London, UK",      "url": "https://lon.speedtest.clouvider.net/backend" },
    { "region": "Asia Pacific",  "city": "Tokyo, Japan",    "url": "https://librespeed.a573.net/backend"         },
]

state = { "interval_seconds": DEFAULT_INTERVAL }

def post_json(url, payload, timeout=30):
    parsed = urlparse(url)
    data = json.dumps(payload).encode("utf-8")
    hdrs = { "Content-Type": "application/json", "Content-Length": str(len(data)), "x-device-id": DEVICE_ID }
    for _ in range(3):
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout, context=ctx)
        conn.request("POST", parsed.path, body=data, headers=hdrs)
        resp = conn.getresponse()
        location = resp.getheader("Location", "")
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        if resp.status in (200, 201): return body
        elif resp.status in (301,302,307,308) and location:
            url = location if location.startswith("http") else f"https://{parsed.netloc}{location}"
            parsed = urlparse(url)
        else: raise Exception(f"HTTP {resp.status}: {body[:200]}")
    raise Exception("Too many redirects")

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"x-device-id": DEVICE_ID})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def load_config():
    url = f"{CLOUD_BASE}/api/speedrunner/config?device_id={DEVICE_ID}&_t={int(time.time())}"
    try:
        cfg = fetch_json(url)
        if cfg.get("ok") and cfg.get("config"):
            state["interval_seconds"] = int(cfg["config"].get("interval_seconds") or DEFAULT_INTERVAL)
            print(f"[CFG] interval={state['interval_seconds']}s")
    except Exception as e:
        print(f"[CFG] failed: {e}")

def measure_download(base_url, chunk_mb=20, timeout=20):
    ctx = ssl.create_default_context()
    url = f"{base_url}/garbage.php?ckSize={chunk_mb}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    start = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        data = r.read()
    elapsed = time.time() - start
    return round((len(data) * 8) / elapsed / 1_000_000, 2), elapsed

def measure_ping(base_url, count=5, timeout=5):
    ctx = ssl.create_default_context()
    url = f"{base_url}/empty.php"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    times = []
    for _ in range(count):
        try:
            start = time.time()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                r.read()
            times.append((time.time() - start) * 1000)
        except: pass
        time.sleep(0.1)
    if not times: return None, None
    avg = round(sum(times) / len(times), 2)
    jitter = round(max(times) - min(times), 2) if len(times) > 1 else 0
    return avg, jitter

def measure_upload(base_url, chunk_mb=1, timeout=20):
    ctx = ssl.create_default_context()
    url = f"{base_url}/empty.php"
    data = os.urandom(chunk_mb * 1024 * 1024)
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(data)),
    })
    start = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        r.read()
    elapsed = time.time() - start
    return round((len(data) * 8) / elapsed / 1_000_000, 2)

def run_librespeed_test(region_cfg):
    region   = region_cfg["region"]
    city     = region_cfg["city"]
    base_url = region_cfg["url"]
    print(f"  [SPEED] Testing {region} ({city})...")
    result = { "engine": "librespeed", "server_name": base_url.split("/")[2], "server_city": city, "server_country": "" }
    try:
        ping_ms, jitter_ms = measure_ping(base_url)
        result["ping_ms"]   = ping_ms
        result["jitter_ms"] = jitter_ms
        print(f"    ping={ping_ms}ms jitter={jitter_ms}ms")
    except Exception as e:
        print(f"    ping error: {e}")
        result["ping_ms"] = None
        result["jitter_ms"] = None

    try:
        dl_mbps, _ = measure_download(base_url)
        result["download_mbps"] = dl_mbps
        print(f"    download={dl_mbps} Mbps")
    except Exception as e:
        print(f"    download error: {e}")
        result["download_mbps"] = None

    try:
        ul_mbps = measure_upload(base_url)
        result["upload_mbps"] = ul_mbps
        print(f"    upload={ul_mbps} Mbps")
    except Exception as e:
        print(f"    upload error: {e}")
        result["upload_mbps"] = None

    result["error"] = None
    return result

def run():
    ingest_url = f"{CLOUD_BASE}/api/speedrunner/ingest"
    print(f"[BOOT] SpeedRunner (LibreSpeed) — device={DEVICE_ID}")
    while True:
        load_config()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"\n[CYCLE] Starting @{ts}")
        for r in REGIONS:
            try:
                result = run_librespeed_test(r)
                ts_test = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                payload = {
                    "device_id":   DEVICE_ID,
                    "ts_utc":      ts_test,
                    "engine":      "librespeed",
                    "region":      r["region"],
                    "region_city": r["city"],
                    **result,
                }
                post_json(ingest_url, payload)
                print(f"  [INGEST] ✓ {r['region']}")
            except Exception as e:
                print(f"  [INGEST] ✗ {r['region']}: {e}")
            time.sleep(3)
        print(f"\n[SLEEP] {state['interval_seconds']}s")
        time.sleep(state["interval_seconds"])

if __name__ == "__main__":
    run()
