#!/usr/bin/env python3
import json, os, urllib.request, ssl, time, subprocess

CLOUD_BASE   = os.environ.get("CLOUD_BASE", "https://netrunner-dashboard.vercel.app")
VLOS_VERSION = os.environ.get("VLOS_VERSION", "1.0.0")
DEVICE_FILE  = os.path.expanduser("~/netrunner/agent/device.json")

def get_cpu_serial():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip().upper()
    except: pass
    return None

def derive_serial(cpu_serial):
    s = cpu_serial.replace(" ","")[:8]
    return f"NR-{s[:4]}-{s[4:8]}"

def get_mac():
    try:
        with open("/sys/class/net/eth0/address") as f: return f.read().strip()
    except: return "unknown"

def get_hostname():
    try: return subprocess.check_output("hostname", text=True).strip()
    except: return "unknown"

def get_ip():
    try:
        r = subprocess.check_output(["hostname","-I"], text=True).strip()
        return r.split()[0] if r else "unknown"
    except: return "unknown"

def load_device():
    try:
        with open(DEVICE_FILE) as f: return json.load(f)
    except: return {}

def phone_home(payload):
    url  = f"{CLOUD_BASE}/api/devices/register"
    data = json.dumps(payload).encode("utf-8")
    ctx  = ssl.create_default_context()
    req  = urllib.request.Request(url, data=data, method="POST",
           headers={"Content-Type":"application/json","Content-Length":str(len(data))})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                print(f"[REGISTER] ✓ status={r.status}")
                return True
        except Exception as e:
            print(f"[REGISTER] attempt {attempt+1}/3 failed: {e}")
            time.sleep(3)
    return False

def main():
    cpu_serial = get_cpu_serial()
    if not cpu_serial:
        print("[REGISTER] ERROR: Could not read CPU serial"); return
    nr_serial = derive_serial(cpu_serial)
    device    = load_device()
    device_id = device.get("device_id", f"pi-{cpu_serial[-8:].lower()}")
    payload   = {
        "device_id":    device_id,
        "nr_serial":    nr_serial,
        "cpu_serial":   cpu_serial,
        "mac_eth0":     get_mac(),
        "hostname":     get_hostname(),
        "ip":           get_ip(),
        "vlos_version": VLOS_VERSION,
        "api_key":      device.get("api_key",""),
    }
    print(f"[REGISTER] NR Serial:  {nr_serial}")
    print(f"[REGISTER] Device ID:  {device_id}")
    print(f"[REGISTER] VLOS:       {VLOS_VERSION}")
    print(f"[REGISTER] IP:         {payload['ip']}")
    print(f"[REGISTER] Phoning home...")
    phone_home(payload)

if __name__ == "__main__":
    main()
