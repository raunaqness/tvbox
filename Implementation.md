# Auto-Stream Architecture (VPS / Python Edition)

This document outlines the architecture for an automated movie and TV show downloading and streaming system, tailored for deployment on a Virtual Private Server (VPS) using Python and FastAPI.

## User Review Required

> [!IMPORTANT]
> **VPS Storage Constraints**
> VPS instances often have limited disk space (e.g., 20-40GB). The system will download files locally first, then upload them to Google Drive via `rclone`. I have included an aggressive cleanup strategy to ensure the local disk doesn't fill up.

> [!WARNING]
> **Torrenting Legality and VPS Providers**
> Many VPS providers (like DigitalOcean, AWS, Linode) strictly forbid downloading copyrighted material and will terminate your account if they receive DMCA notices. You should either use an "Offshore/DMCA-ignored" VPS provider, or we must route the torrent traffic through a VPN (e.g., WireGuard/OpenVPN) on the VPS itself.

## Proposed Changes

### System Architecture Overview

#### 1. Frontend (Jinja2 Templates + Vanilla JS)
- Served directly by FastAPI using `Jinja2Templates`.
- **Search UI**: Simple HTML input. Vanilla JS will handle debouncing and making AJAX calls to the FastAPI backend for autocomplete.
- **Results View**: Displays posters, titles, and release years.
- **Status Page**: A simple dashboard showing active downloads and `rclone` upload statuses.

#### 2. Backend (FastAPI / Python)
- **`/api/search`**: Receives queries, calls the **TMDB API**, and returns formatted results to the frontend.
- **`/api/fetch`**: Kicks off the search strategies, selects the best torrent, and initiates the download.
- **Background Tasks**: FastAPI's `BackgroundTasks` will be used to monitor the download progress and trigger the `rclone` upload once complete, keeping the web UI non-blocking.

#### 3. Multiple Torrent Search Strategies (Aggregator)
To ensure the best results, the backend will implement a "Strategy Pattern" for searching, running multiple engines concurrently:
- **Strategy A (Prowlarr)**: We will run Prowlarr (a torrent indexer manager) alongside our app. Prowlarr can search dozens of trackers (1337x, TorrentGalaxy, etc.) simultaneously.
- **Strategy B (Direct APIs)**: Python scripts that directly hit public APIs (e.g., YTS API for movies, EZTV API for TV shows) as fallbacks.
- **Aggregator**: The Python backend will pool results from all strategies, deduplicate them based on infohash/magnet, and score them based on:
  - Seeders / Leechers ratio
  - Resolution (preferring 1080p/4k based on your settings)
  - File size (avoiding massive 80GB remuxes unless requested)

#### 4. Torrent Client (`aria2c` + `aria2p`)
- **`aria2c`**: An ultra-lightweight CLI download utility that supports BitTorrent. Perfect for a VPS.
- **`aria2p`**: A Python library to interact with the `aria2c` daemon via RPC. The FastAPI app will send magnet links to `aria2c` and poll for completion status.

#### 5. Cloud Sync (`rclone`)
- Once `aria2c` reports a download is 100% complete, Python will execute `rclone move /downloads/<file> gdrive:/Media/ --delete-empty-src-dirs`.
- This ensures the file is immediately uploaded to Google Drive and deleted from the VPS to save space.

#### 6. Apple TV Streaming
- **Infuse**: Connect Infuse directly to the Google Drive account. It natively streams the files and fetches all necessary metadata (posters, subtitles).

### Containerization & Local Testing (Docker)
The entire system will be containerized to guarantee parity between your local development environment and the VPS.
- **`Dockerfile`**: A multi-stage Dockerfile will be created for the FastAPI app, bundling Python, `rclone`, and any system dependencies.
- **`docker-compose.yml`**: A unified compose file will spin up:
  1. The custom **FastAPI Web App** container.
  2. The **Aria2c Daemon** container.
  3. The **Prowlarr** container.
- **Local Testing**: You can simply run `docker-compose up` on your Mac to test the entire flow locally before pushing code.

### CI/CD Deployment Strategy (GitHub Actions)
To automate the deployment to your VPS, we will implement a GitHub Actions workflow:
- **CI Pipeline**: On push to `main`, GitHub Actions will lint the Python code (e.g., using Ruff/Black) and run any unit tests.
- **CD Pipeline**: Once tests pass, the Action will:
  1. SSH into your VPS (using securely stored GitHub Secrets).
  2. Pull the latest code from the repository.
  3. Run `docker-compose up -d --build` to automatically rebuild the FastAPI image and restart the containers with zero downtime.

### Additional Suggestions
- **Security**: Since your VPS will be accessible via a public IP, I highly recommend adding **HTTP Basic Authentication** to the FastAPI app so randos cannot access your web interface and start downloading things to your Drive.
- **Telegram/Discord Notifications**: We could easily add a Python hook that sends you a message (e.g., "Inception is downloaded and ready to stream on Apple TV!") when the `rclone` upload finishes.

## Verification Plan

### Automated Tests
- Test the Aggregator logic to ensure it correctly parses and ranks torrents from both Prowlarr and direct APIs.
- The GitHub Actions CI pipeline will automatically run these tests on every push.

### Manual Verification
- Run `docker-compose up` locally to verify the stack starts correctly.
- Deploy to the VPS by pushing to GitHub and verifying the Actions workflow succeeds.
- Access the web UI on the VPS.
- Trigger a download, monitor `aria2c` progress in the dashboard.
- Verify the file is moved to Google Drive and deleted from the VPS.
- Stream on Apple TV.
