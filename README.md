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

## ⚠️ Current Known Issue & Troubleshooting

### **The Problem: Downloads Stuck at 0 B/s**
Torrents are successfully fetched from the indexers and added to the table, but the download speed remains at `0 B/s` and progress stays at `0%`.

### **The Cause: ISP BitTorrent Blocking**
Aggressive Internet Service Providers (ISPs) often use Deep Packet Inspection (DPI) to block DHT (Distributed Hash Table) bootstrap nodes and UDP trackers. While the backend successfully resolves the magnet link, `aria2c` is being actively blocked from connecting to other peers in the swarm by the ISP's firewall.

### **How to Fix It**

1. **Use a VPN (Recommended)**: 
   Running a system-wide VPN (or routing the `aria2c` container through a VPN container like `gluetun`) will encrypt all traffic and instantly bypass the ISP block.

2. **Force BitTorrent Encryption**: 
   You can attempt to bypass basic ISP inspection by forcing `aria2c` to encrypt its traffic. Modify `aria2-config/aria2.conf` to include:
   ```ini
   bt-require-crypto=true
   bt-min-crypto-level=arc4
   ```

3. **Inject Fresh Trackers**: 
   Often, the default trackers embedded in magnet links are blocked. Supplying `aria2c` with a regularly updated list of unblocked trackers (e.g., from `ngosang/trackerslist`) can help it bootstrap the connection to peers.
