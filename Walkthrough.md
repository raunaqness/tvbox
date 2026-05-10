# Auto-Stream Walkthrough

I have successfully architected and implemented the entire Auto-Stream system, from the custom Python backend to the beautiful glassmorphic frontend UI.

## What was built

We built a complete, automated movie and TV show downloading and streaming system. It handles the full pipeline:
`Autocomplete -> Search -> Download -> Upload to Google Drive -> Cleanup`

### 1. The Backend (FastAPI)
- **TMDB Integration (`app/services/tmdb.py`)**: Connects to the TMDB API to provide rich metadata and search capabilities for the frontend autocomplete.
- **Search Aggregator (`app/services/search.py`)**: A powerful engine that concurrently queries multiple sources (YTS API directly, and Prowlarr for everything else). It deduplicates the results by magnet hash and ranks them by seeders to ensure you always get the healthiest torrent.
- **Download Manager (`app/services/download.py`)**: Uses `aria2p` to communicate with the `aria2c` daemon. It adds magnets and polls for progress.
- **Upload Manager (`app/services/upload.py`)**: Wraps `rclone move` to securely upload the completed video file straight to your Google Drive and cleans up the local VPS storage.
- **Task Orchestrator (`app/routers/api.py`)**: The brain of the operation. It's a FastAPI Background Task that watches the download progress, triggers the upload when it hits 100%, and updates the frontend dashboard state.

### 2. The Frontend (Jinja2 & Vanilla CSS/JS)
- **Design System (`app/static/style.css`)**: Built a premium, fully custom "Glassmorphism" UI from scratch. It features a dark mode palette, smooth gradients, dynamic blur effects, and the modern 'Outfit' Google Font.
- **Search UI (`app/templates/index.html`)**: A debounced autocomplete search bar that feels instantly responsive.
- **Dashboard (`app/static/app.js`)**: Real-time polling via AJAX updates the progress bars and speeds of your active downloads without needing to refresh the page.

### 3. Infrastructure & Deployment
- **Docker Integration (`docker-compose.yml`, `Dockerfile`)**: The entire stack is containerized. A single `docker-compose up` command spins up the FastAPI app, the Aria2c download engine, and Prowlarr.
- **CI/CD (`.github/workflows/deploy.yml`)**: An automated GitHub Actions pipeline that installs dependencies, runs the Pytest suite, and securely deploys updates to your VPS via SSH on every push to the `main` branch.

## Verification
- Unit tests and mocked integration tests were written for all major components (`tests/test_search.py`, `tests/test_tmdb.py`, `tests/test_download.py`, `tests/test_upload.py`, `tests/test_api.py`).
- All tests pass successfully, confirming that the aggregation logic, the API mocking, and the routing work as expected.

## Next Steps for You
1. **API Keys**: Make sure to update the environment variables or `.env` file on your VPS with your actual `TMDB_API_KEY` and `PROWLARR_API_KEY`.
2. **Rclone Setup**: You must manually run `rclone config` on your VPS once to authenticate your Google Drive account and name the remote `gdrive`.
3. **Apple TV**: Open the Infuse app on your Apple TV, add your Google Drive as a share, and it will automatically scrape the posters and metadata for everything that gets uploaded!
