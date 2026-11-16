# 🏰 Disney Wait Times Smart Display Box

A retro Disney park wait-times smart clock & tip board web app, designed for Raspberry Pi kiosks, desk displays, Proxmox LXC containers, or home dashboards.

Inspired by physical subscription display boxes, this app brings the magic of Disney parks into your home or office with live wait times, retro physical enclosure finishes, customizable time zones, and auto-cycling attraction timers.

---

## ✨ Features

- **📦 Physical Box Display Mode**:
  - Retro LED / LCD smart-clock aesthetic mimicking physical subscription hardware.
  - Smooth progress bar cycling through attractions.
  - Hardware-style tactile buttons (Next, Previous, Pause/Play, Favorite).
  - Custom bezel finishes: *Dark Walnut Wood*, *Brushed Aluminum*, and *Obsidian Black*.
- **📋 Park Tip Board Mode**:
  - Full park overview grid showing all lands, rides, operational statuses, and wait times.
  - Instant live search and filtering (*Open Only*, *Favorites Only*, *All*).
- **⏱️ Configurable Time Zones**:
  - Support for Central Time (CST/CDT), Eastern Time (EST/EDT), Mountain Time (MST/MDT), Pacific Time (PST/PDT), Alaska, Hawaii, Park Local Time, or Device Time.
  - Click-to-configure badge right on the clock header.
  - Selections persisted across browser reloads via `localStorage`.
- **🌐 Supported Parks**:
  - **Walt Disney World**: Magic Kingdom, EPCOT, Disney's Hollywood Studios, Disney's Animal Kingdom.
  - **Disneyland Resort**: Disneyland Park, Disney California Adventure.
  - **International**: Disneyland Paris, Tokyo Disneyland, Tokyo DisneySea.
- **⚡ Lightweight Backend**:
  - Python standard library server (zero external pip dependencies).
  - 60-second caching proxy to `queue-times.com` to prevent rate limits.
  - Integrated health check endpoint (`/api/health`).
- **🖥️ Kiosk & Fullscreen Ready**:
  - One-click fullscreen kiosk toggle.
  - Complete Raspberry Pi startup automation guide included.

---

## 🚀 Quick Start (Standalone Python)

Run directly with Python 3 (no pip install required):

```bash
python3 server.py
```

Open your browser to `http://localhost:8088`.

To run on a custom port:
```bash
PORT=9000 python3 server.py
```

---

## 🐳 Docker / Docker Compose

### Run with Docker Compose:
```bash
docker compose up -d
```

### Build & Run Manually:
```bash
docker build -t disney-wait-times .
docker run -d --name disney-wait-times -p 8088:8088 disney-wait-times
```

---

## 📟 Raspberry Pi Kiosk Setup

Want to turn a Raspberry Pi and small display into a dedicated desk clock?
Check out the step-by-step [Raspberry Pi Kiosk Setup Guide](RASPBERRY_PI_KIOSK_GUIDE.md) for automated booting, cursor hiding, and display scheduling.

---

## 🐧 Proxmox LXC / Systemd Service

To run as a systemd service on Linux or inside an LXC container:

1. Copy files to `/opt/disney-wait-times/`
2. Copy `disney-wait-times.service` to `/etc/systemd/system/`
3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now disney-wait-times.service
   ```

---

## 📡 API Endpoints

- `GET /api/parks` - Returns list of supported parks and metadata.
- `GET /api/parks/<id>/waits` - Returns cached live wait times and summary stats for a park.
- `GET /api/health` - Health check status.

---

## 🧪 Testing

Run the full automated test suite locally:

```bash
python3 -m unittest discover -s tests -v
```

This validates:
- API endpoint responses (`/api/health`, `/api/parks`, `/api/parks/<id>/waits`).
- Queue-times data parser, stats calculations, and TTL caching.
- Fallback to stale cache on upstream timeouts.
- Frontend DOM elements and JavaScript syntax integrity.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
