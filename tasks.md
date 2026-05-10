- `[x]` **Phase 1: Project Initialization & Infrastructure**
  - `[x]` Initialize Python project (e.g., using `venv` and `requirements.txt`).
  - `[x]` Configure `pytest`, `pytest-asyncio`, and `httpx` for unit testing.
  - `[x]` Create a foundational `docker-compose.yml` containing `aria2c` and `prowlarr` for local development.
  - `[x]` Set up the base FastAPI application structure (`main.py`, routers, models).

- `[x]` **Phase 2: Torrent Search Strategies (Aggregator)**
  - `[x]` Define the base `SearchStrategy` interface.
  - `[x]` Implement `YTSStrategy` (Direct API for Movies).
    - `[x]` Write unit test mocking the YTS HTTP response.
  - `[x]` Implement `ProwlarrStrategy` (API integration with Prowlarr).
    - `[x]` Write unit test mocking the Prowlarr API response.
  - `[x]` Implement the `Aggregator` service (runs strategies concurrently, deduplicates, and ranks results by seeders/size).
    - `[x]` Write unit tests for the deduplication and ranking logic.

- `[x]` **Phase 3: Metadata API (TMDB)**
  - `[x]` Implement the TMDB client for autocomplete and metadata fetching.
  - `[x]` Write unit tests mocking the TMDB search responses.

- `[x]` **Phase 4: Download Client (`aria2c`)**
  - `[x]` Implement `DownloadManager` using the `aria2p` package to interface with the `aria2c` daemon.
  - `[x]` Write methods to add magnet links, poll progress, and remove torrents.
  - `[x]` Write unit tests for `DownloadManager` (mocking the `aria2p.Client` to avoid needing a real daemon in tests).

- `[x]` **Phase 5: Cloud Sync (`rclone`)**
  - `[x]` Implement `UploadManager` using Python's `subprocess` to execute `rclone move`.
  - `[x]` Write unit tests mocking the `subprocess.run` calls to ensure correct arguments are passed.

- `[x]` **Phase 6: Backend Endpoints & Orchestration**
  - `[x]` Implement `/api/search` (TMDB autocomplete).
    - `[x]` Write integration test using FastAPI's `TestClient`.
  - `[x]` Implement `/api/fetch` (trigger search strategies, select best, start download).
    - `[x]` Write integration test using `TestClient`.
  - `[x]` Implement the Background Task Orchestrator (Wait for `aria2c` download 100% -> trigger `rclone` -> cleanup).
    - `[x]` Write unit test mocking the download and upload managers.

- `[x]` **Phase 7: Frontend UI (Jinja2)**
  - `[x]` Configure `Jinja2Templates` in FastAPI.
  - `[x]` Build the Search Interface (HTML + Vanilla JS for debounced API calls).
  - `[x]` Build the Dashboard Interface (polling `/api/status` to show progress bars).
  - `[x]` Write simple tests to verify the template endpoints return 200 OK.

- `[x]` **Phase 8: Dockerization & CI/CD**
  - `[x]` Write the `Dockerfile` for the Python/FastAPI app (including system dependencies like `rclone`).
  - `[x]` Finalize the `docker-compose.yml` to link the FastAPI container with `aria2c` and `Prowlarr`.
  - `[x]` Create `.github/workflows/deploy.yml` with linting (Ruff), testing (Pytest), and SSH deployment to the VPS.
