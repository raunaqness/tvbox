# Auto-Stream

A fully containerized, automated media streaming system. This application allows you to search for movies and TV shows, automatically find the best torrents across multiple indexers, download them via `aria2c`, and securely sync them to your Google Drive via `rclone`.

## 🏗 Architecture

The system is broken down into highly decoupled, asynchronous components:

- **Frontend UI (Jinja2 & Vanilla JS)**: A responsive, premium "Glassmorphism" interface. It uses debounced AJAX polling to provide a real-time table of all active and historical download jobs.
- **Backend (FastAPI)**: The central orchestrator. It manages the REST APIs and spawns asynchronous background tasks to monitor downloads.
- **Database (SQLite + SQLAlchemy)**: Maintains persistent state for all download jobs (`jobs.db`) so historical data survives container restarts.
- **Search Aggregator (Strategy Pattern)**: Simultaneously queries multiple providers (`YTS`, `Prowlarr`, `ThePirateBay`), deduplicates results by magnet hash, and ranks them by seeders to ensure maximum download speed.
- **Download Engine (Aria2c)**: A lightweight, multi-protocol download utility controlled via the `aria2p` Python wrapper.
- **Cloud Sync (Rclone)**: Automatically executes a subprocess `rclone move` to securely transfer completed downloads directly to Google Drive, cleaning up local storage afterward.

## 🚀 Deployment

The entire stack is containerized and orchestrated via `docker-compose`.

```bash
docker-compose up -d --build
```

This spins up 3 containers:
1. `tvbox-app-1` (FastAPI + UI on port 8000)
2. `aria2c` (Download daemon on port 6800)
3. `prowlarr` (Indexer manager on port 9696)

## ✨ Recent Features & Reliability Upgrades

To maximize system autonomy and download reliability, several advanced features have been implemented:

- **Intelligent Seeder Scaling (4K Prioritization)**: The search engine dynamically prioritizes 4K/2160p torrents over 1080p versions. However, it applies a heavy penalty to any 4K torrent with fewer than 5 seeders, ensuring the system naturally falls back to a healthy 1080p swarm rather than getting stuck on a dead 4K magnet.
- **Auto-Fallback System**: When a search is initiated, the backend quietly saves the top 5 alternative magnet links to the database. If a download remains stuck at exactly `0.00%` for 30 minutes, the orchestrator automatically wipes the stalled task from `aria2c`, pops the next best alternative link from the database, and injects it to seamlessly retry with a different swarm.
- **Task Management**: Fully integrated frontend controls allow users to permanently delete active or stuck tasks, which kills the `aria2c` job and removes it from the database.
- **Asynchronous Cloud Sync & Retry**: The `rclone` upload sequence runs as an asynchronous background subprocess, ensuring the frontend never freezes. If an upload to Google Drive fails (due to network or config errors), a **Retry** button dynamically appears in the UI to manually restart the transfer.
- **Strict Local Cleanup**: Upon a successful `rclone move` transfer to Google Drive (with parent directories preserved), a strict Python teardown sequence forcefully wipes the source directory from local storage to prevent disk bloating.
- **Exposed Peer Connections**: Port `6888` (TCP/UDP) is now fully exposed in the `docker-compose` stack, transforming `aria2c` from a passive leecher into an active node that can accept incoming peer requests, vastly accelerating DHT discovery.

## 🛠 Resolved Issues & Troubleshooting

### **Past Issue: Downloads Stuck at 0 B/s**
Torrents were successfully fetched from the indexers, but the download speed remained at `0 B/s`.

### **The Cause & Resolution: ISP BitTorrent Blocking**
Aggressive Internet Service Providers (ISPs) often use Deep Packet Inspection (DPI) to block DHT bootstrap nodes and UDP trackers. This has been resolved via multiple system configurations:
1. **BitTorrent Encryption**: `aria2c` is now forced to encrypt its traffic (`bt-require-crypto=true` and `bt-min-crypto-level=arc4`) to bypass basic ISP inspection.
2. **Fresh Trackers**: A massive list of healthy, unblocked trackers was manually injected into the configuration to bypass dead default trackers.
3. **Port Forwarding**: The BitTorrent and DHT ports (`6888`) are now correctly exposed to the host network, allowing active peer connections.

*(Note: If issues persist on restricted networks, routing the `aria2c` container through a VPN container like `gluetun` is still the ultimate fallback.)*
