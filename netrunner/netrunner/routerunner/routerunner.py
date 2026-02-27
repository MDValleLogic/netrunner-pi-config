#!/usr/bin/env python3
import json, time, socket, subprocess, re, os
import urllib.request, urllib.error
from urllib.parse import urlparse

DEVICE_ID   = os.environ.get("DEVICE_ID", "unknown")
DEVICE_KEY  = os.environ.get("DEVICE_KEY", "")
CLOUD_BASE  = os.environ.get("CLOUD_BASE", "").rstrip("/")
DEFAULT_INTERVAL = 300
DEFAULT_TARGETS  = ["8.8.8.8", "1.1.1.1"]
HEADERS = {"content-type": "application/json", "x-device-id": DEVICE_ID, "x-device-key": DEVICE_KEY}
state = {"targets": DEFAULT_TARGETS, "interval_seconds": DEFAULT_INTERVAL}

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_json(url, payload, timeout=15):
    import http.client, ssl, json as _json
    data = _json.dumps(payload).encode("utf-8")
    hdrs = {**HEADERS, "Content-Length": str(len(data))}
    for _ in range(3):
        parsed = urlparse(url)
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout, context=ctx)
        conn.request("POST", parsed.path, body=data, headers=hdrs)
        resp = conn.getresponse()
        location = resp.getheader("Location", "")
        print(f"[INGEST] status={resp.status} location={location}")
        conn.close()
        if resp.status in (200, 201):
            return
        elif resp.status in (301, 302, 307, 308) and location:
            url = location if location.startswith("http") else f"https://{parsed.netloc}{location}"
        else:
            raise Exception(f"HTTP {resp.status}")

def load_cloud_config():
    url = f"{CLOUD_BASE}/api/routerunner/config?device_id={DEVICE_ID}&_t={int(time.time())}"
    try:
        cfg = fetch_json(url)
        if isinstance(cfg, dict) and "config" in cfg: cfg = cfg["config"]
        state["targets"] = cfg.get("targets") or DEFAULT_TARGETS
        state["interval_seconds"] = int(cfg.get("interval_seconds") or DEFAULT_INTERVAL)
        print(f"[CFG] {len(state['targets'])} targets, interval={state['interval_seconds']}s")
    except Exception as e:
        print(f"[CFG] failed: {e} — using defaults")

def ptr_lookup(ip):
    try: return socket.gethostbyaddr(ip)[0]
    except: return ""

def asn_lookup(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,org,isp,country,city,as"
        req = urllib.request.Request(url, headers={"User-Agent": "NetRunner/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                return {"org": data.get("org",""), "isp": data.get("isp",""), "country": data.get("country",""), "city": data.get("city",""), "asn": data.get("as","")}
    except: pass
    return {"org":"","isp":"","country":"","city":"","asn":""}

def run_traceroute(target, max_hops=30):
    hops = []
    try:
        result = subprocess.run(["traceroute","-n","-w","2","-m",str(max_hops),target], capture_output=True, text=True, timeout=120)
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if not parts: continue
            try: hop_num = int(parts[0])
            except: continue
            if len(parts) > 1 and parts[1] == "*":
                hops.append({"hop":hop_num,"ip":None,"hostname":None,"rtt_ms":None,"timeout":True,"org":"","isp":"","asn":"","country":"","city":""})
                continue
            ip = None; rtt = None
            for i,p in enumerate(parts):
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", p): ip = p
                if p == "ms" and i > 0:
                    try: rtt = float(parts[i-1])
                    except: pass
            if not ip: continue
            asn_info = asn_lookup(ip)
            hops.append({"hop":hop_num,"ip":ip,"hostname":ptr_lookup(ip) or ip,"rtt_ms":rtt,"timeout":False,**asn_info})
            print(f"  [{hop_num:2d}] {ip:16s}  {str(rtt or '?'):>8} ms  {asn_info.get('org','')[:40]}")
    except Exception as e:
        print(f"[TRACE] error: {e}")
    return hops

def run():
    ingest_url = f"{CLOUD_BASE}/api/routerunner/ingest"
    print(f"[RUN] ingest={ingest_url}")
    while True:
        load_cloud_config()
        for target in state["targets"]:
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            print(f"\n[TRACE] → {target}  @{ts}")
            dest_ip = target
            try: dest_ip = socket.gethostbyname(target)
            except: pass
            hops = run_traceroute(dest_ip)
            payload = {"device_id":DEVICE_ID,"ts_utc":ts,"target":target,"dest_ip":dest_ip,"hop_count":len([h for h in hops if not h["timeout"]]),"total_hops":len(hops),"hops":hops}
            try:
                post_json(ingest_url, payload)
            except Exception as e:
                print(f"[INGEST] failed: {e}")
        print(f"\n[SLEEP] {state['interval_seconds']}s")
        time.sleep(state["interval_seconds"])

if __name__ == "__main__":
    print(f"[BOOT] RouteRunner — device={DEVICE_ID} cloud={CLOUD_BASE}")
    run()
