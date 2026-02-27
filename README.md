# NetRunner Pi Config

Backup of all NetRunner appliance scripts, configs, and Docker files.

## Device
- **Hostname:** vallelogic-pi5
- **IP:** 10.10.10.19
- **Device ID:** pi-403c60f1-2557-408f-a3c8-ca7acaf034f5
- **OS:** Raspberry Pi OS 64-bit
- **Hardware:** Raspberry Pi 5

## Services
- **RouteRunner** — `~/netrunner/routerunner/` — traceroute to content targets every 5min
- **SpeedRunner** — `~/netrunner/speedrunner/` — LibreSpeed geo speed tests every 1hr

## Recovery
1. Flash fresh Pi OS to SD card
2. Clone this repo to `~/netrunner/`
3. Set env vars (DEVICE_ID, DEVICE_KEY, CLOUD_BASE)
4. `docker compose up -d` in each service folder

## Full Image Backup
Stored on VALLEdrive: `vallelogic-pi5-YYYYMMDD.img`
Restore: `dd if=vallelogic-pi5.img of=/dev/sdX bs=4M status=progress`
