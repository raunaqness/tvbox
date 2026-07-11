# tvbox

Your personal, self-hosted media library. Search for a movie or TV show in the browser, let tvbox find and download a suitable release, and move the completed file to Google Drive for playback through Infuse.

> Use tvbox only to download and stream media that you are legally allowed to access. Check your local laws and your VPS provider's acceptable-use policy before enabling torrent traffic.

## How it works

![tvbox architecture diagram](docs/images/tvbox-architecture.png)

- **FastAPI and Jinja2** provide the web interface and API.
- **TMDB** supplies titles, posters, and other metadata.
- **Prowlarr and direct search providers** collect torrent candidates.
- **aria2c** downloads the selected release.
- **SQLite and SQLAlchemy** persist download history and status.
- **rclone** moves completed downloads to Google Drive and removes the local copy.
- **Cloudflare Tunnel** can expose the password-protected app without opening the web port publicly.
- **Infuse** connects to Google Drive and provides the final browsing and playback experience.

## Features

- Movie and TV autocomplete powered by TMDB
- Concurrent torrent search, deduplication, and seeder-aware ranking
- Preference for healthy 4K releases with automatic 1080p fallback
- Automatic retry with another candidate when a download remains stalled
- Live progress, speed, history, retry, and deletion controls
- Asynchronous Google Drive uploads
- Automatic VPS storage cleanup after a successful upload
- Password-protected browser access
- Docker Compose deployment

## Requirements

- A Linux VPS with Docker and Docker Compose
- A domain managed by Cloudflare
- A Cloudflare account with access to Cloudflare Tunnel
- A Google Drive account with enough storage
- An Infuse account and a supported playback device
- TMDB and Prowlarr API keys
- `rclone` configured on the VPS with a remote named `gdrive`

VPS disks are often small. Leave enough free space for the largest file you expect to download because tvbox stores each download locally before uploading it.

## Quick start

1. Clone the repository on the VPS:

   ```bash
   git clone <repository-url> tvbox
   cd tvbox
   ```

2. Configure Google Drive and name the rclone remote `gdrive`:

   ```bash
   rclone config
   ```

3. Create `.env` in the project root:

   ```dotenv
   TMDB_API_KEY=your_tmdb_api_key
   PROWLARR_API_KEY=your_prowlarr_api_key
   APP_PASSWORD=use_a_long_unique_password
   SECRET_KEY=generate_a_long_random_value
   RCLONE_REMOTE=gdrive:/Media
   ```

4. Review `docker-compose.yml`, especially its ports, aria2 RPC secret, rclone configuration path, and Cloudflare Tunnel token. Do not commit real credentials.

5. Build and start the stack:

   ```bash
   docker compose up -d --build
   ```

6. Configure indexers in Prowlarr at `http://<vps-ip>:9696`. If you obtained the Prowlarr API key after starting the stack, add it to `.env` and restart the app:

   ```bash
   docker compose restart app
   ```

7. Point a Cloudflare Tunnel hostname at `http://app:8000`, then open that hostname and sign in with `APP_PASSWORD`.

8. Add the same Google Drive account to Infuse and select the folder configured by `RCLONE_REMOTE`.

The stack also includes FlareSolverr for indexers that require it. Prowlarr, aria2 RPC, and FlareSolverr are administrative services; restrict their ports with your VPS firewall rather than exposing them to the public internet.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `TMDB_API_KEY` | TMDB search and metadata | None |
| `PROWLARR_API_KEY` | Prowlarr API access | None |
| `PROWLARR_URL` | Internal Prowlarr URL | `http://localhost:9696` |
| `ARIA2C_HOST` | aria2 RPC host | `http://localhost` |
| `ARIA2C_PORT` | aria2 RPC port | `6800` |
| `ARIA2C_SECRET` | aria2 RPC secret | None |
| `APP_PASSWORD` | Web login password | `admin` |
| `SECRET_KEY` | Session-signing key | `fallback_secret` |
| `RCLONE_REMOTE` | Upload destination | `gdrive:/Media` |
| `DOWNLOADS_DIR` | Local download directory | `./downloads` |

Always override the default password and session secret in production.

## Services

| Service | Role | Default port |
| --- | --- | --- |
| `app` | tvbox web app and API | `8000` |
| `aria2c` | Download engine and RPC server | `6800` |
| `prowlarr` | Indexer manager | `9696` |
| `flaresolverr` | Optional anti-bot helper for Prowlarr | `8191` |
| `cloudflared` | Private remote access tunnel | None |

## Development and tests

Install the Python dependencies and run the test suite:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. pytest tests/
```

## Troubleshooting

- **Downloads remain at 0 B/s:** Verify that the torrent has active seeders and that TCP/UDP port `6888` is allowed by the VPS firewall. Some providers block torrent traffic entirely.
- **Prowlarr returns no results:** Confirm that its indexers pass their built-in tests and that `PROWLARR_API_KEY` is correct.
- **Uploads fail:** Run `rclone lsd gdrive:` on the VPS and confirm that the configuration is mounted inside the app container.
- **The app is unreachable remotely:** Check the Cloudflare Tunnel route and confirm that its origin points to `http://app:8000`.
- **Infuse cannot see new files:** Confirm the upload folder in `RCLONE_REMOTE`, then refresh the matching Google Drive share in Infuse.

## Security notes

- Keep all API keys, tunnel tokens, RPC secrets, and passwords out of Git.
- Expose the app through Cloudflare Tunnel; do not publicly expose its origin port.
- Restrict ports `6800`, `8191`, and `9696` to trusted administrators.
- Rotate any credential that has previously been committed.
