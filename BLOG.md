# tvbox: How My Self-Hosted Personal Netflix Works

How many times have you searched for a movie only to discover that it is unavailable on every OTT platform in your country? You end up searching Reddit, online forums, and the wider web just to find out where it can be watched.

Sometimes Google even shows a result from a service such as MUBI or Amazon Prime, but clicking it reveals that the title is unavailable in your region. I found this fragmented and frustrating, so I built **tvbox** to solve my own problem: one private interface where I can search for something, send it to my own server, and watch it later from any of my devices.

tvbox is a complete, self-hosted application that searches for media, downloads a selected release to a VPS, moves the completed file to Google Drive, and makes it available in Infuse. Cloudflare Tunnel provides secure browser access without requiring the web app to be exposed directly to the internet.

The complete project is available on GitHub at [github.com/raunaqness/tvbox](https://github.com/raunaqness/tvbox), and this post explains how it works and how to deploy your own instance.

> **Disclaimer:** This project and article are provided for educational purposes only. You are responsible for complying with all applicable copyright, privacy, internet, and local laws, as well as the acceptable-use policies of your VPS provider, Google Drive, Cloudflare, indexers, and other services. Only download, store, and stream content that you are legally authorized to access.

tvbox can run entirely on a local computer, so a VPS, domain, and Cloudflare account are only needed when you want the service available 24×7 and accessible remotely.

## Deployment at a Glance

- Choose between running tvbox locally or deploying it to an always-on VPS.
- Get a Cloudflare-managed domain only if you want secure remote browser access.
- Prepare Google Drive storage, an Infuse account, and the required API keys.
- Install Git, Docker, Docker Compose, and rclone on the chosen computer or VPS.
- Clone `https://github.com/raunaqness/tvbox` onto the chosen host.
- Add the tvbox secrets and service settings to `.env`.
- Authenticate rclone with Google Drive and create the `gdrive:/Media` destination.
- Start tvbox, Prowlarr, aria2c, and FlareSolverr with Docker Compose.
- Configure Prowlarr indexers and add its API key to tvbox.
- Route a Cloudflare Tunnel hostname to the tvbox container.
- Connect Infuse to Google Drive and select the `Media` folder.
- Run one end-to-end download, upload, cleanup, and playback test.

## 1. How tvbox Works

The day-to-day workflow looks like this:

1. Open tvbox from any browser.
2. Search for a movie or TV show.
3. Let tvbox gather metadata and find available releases.
4. Download the selected release to the VPS with aria2c.
5. Move the completed file to Google Drive with rclone.
6. Browse and play the file through Infuse.

The VPS is only temporary storage. After a successful upload, tvbox removes the local copy so that a small server disk does not gradually fill up.

The stack consists of:

- **FastAPI and Jinja2** for the web application
- **TMDB** for titles, posters, and metadata
- **Prowlarr** and direct providers for search
- **aria2c** for downloads
- **SQLite** for job history and status
- **rclone** for Google Drive uploads
- **Cloudflare Tunnel** for remote browser access
- **Infuse** for the final media library and playback experience

## 2. What You Need

Before starting, prepare the following:

- A local computer with Docker or a Linux VPS with enough temporary storage for one complete download
- An optional domain whose DNS is managed by Cloudflare for remote access
- An optional Cloudflare account with access to Cloudflare Zero Trust for remote access
- A Google Drive account with enough storage for your library
- An Infuse account and a supported Apple device
- A free TMDB API key
- Docker, Docker Compose, Git, and rclone

A local installation is available at `http://localhost:8000` and does not require a domain or Cloudflare Tunnel.

A modest VPS is enough for a 24×7 deployment. Disk space and network transfer are more important than CPU power. Remember that the full file exists on the host until its Google Drive upload completes.

Also check the VPS provider's rules. Some providers prohibit BitTorrent traffic regardless of whether the content itself is legal.

## 3. Prepare the Local Computer or VPS

- For a local setup, install Git, rclone, and Docker Desktop or Docker Engine, then run the remaining commands in a local terminal.
- For a VPS setup, connect to the remote server over SSH before continuing.

Connect to the server:

```bash
ssh your-user@your-vps-ip
```

Install the required packages on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y git rclone
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and reconnect so the new Docker group membership takes effect. Then confirm the installation:

```bash
docker --version
docker compose version
rclone version
```

Clone the existing tvbox project from GitHub:

```bash
git clone https://github.com/raunaqness/tvbox
cd tvbox
```

Create an environment file:

```bash
nano .env
```

Add the initial configuration:

```dotenv
TMDB_API_KEY=your_tmdb_api_key
PROWLARR_API_KEY=
APP_PASSWORD=use_a_long_unique_password
SECRET_KEY=use_a_long_random_session_secret
ARIA2C_SECRET=use_a_different_random_rpc_secret
RCLONE_REMOTE=gdrive:/Media
CLOUDFLARE_TUNNEL_TOKEN=
```

You can generate strong random values with:

```bash
openssl rand -hex 32
```

Never commit `.env` or paste its contents into an issue, screenshot, or blog post.

Before deployment, review `docker-compose.yml`. Replace hardcoded credentials with environment-variable references:

```yaml
services:
  app:
    environment:
      - ARIA2C_SECRET=${ARIA2C_SECRET}

  aria2c:
    environment:
      - RPC_SECRET=${ARIA2C_SECRET}

  cloudflared:
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
```

The same aria2 secret must be used by the app and the aria2c container.

## 4. Connect the Services

### Get a TMDB API key

Create a TMDB account, open the API section of your account settings, and request an API key. Add the key to `TMDB_API_KEY` in `.env`.

TMDB provides search metadata only. It does not host or download the media.

### Configure Google Drive with rclone

- Install rclone on a computer with a web browser as well as on the VPS.
- Run `rclone config` on the VPS and choose `n` to create a new remote.
- Name the remote `gdrive` and select Google Drive as its storage type.
- Leave the client ID and client secret empty unless you have created your own Google OAuth application.
- Select the standard full-access Drive scope and leave the service-account file empty.
- Choose `n` when rclone asks whether to use automatic browser authentication on the headless VPS.
- Copy the complete `rclone authorize "drive" ...` command displayed by the VPS.
- Run the copied authorization command on the computer with a browser and sign in to the Google account that will store the media.
- Copy the authorization token printed by the local computer and paste it into the waiting VPS prompt.
- Choose `n` for Shared Drive unless the destination is a Google Shared Drive.
- Confirm the remote configuration and choose `q` to leave the rclone configuration menu.
- Run `rclone lsd gdrive:` on the VPS to verify that Google Drive authentication works.
- Run `rclone mkdir gdrive:/Media` to create the tvbox destination folder.
- Run `docker compose exec app rclone lsd gdrive:` after deployment to verify that the container can use the same credentials.
- Confirm that Docker mounts the configuring user's `~/.config/rclone/rclone.conf` into the app container.

### Start and configure Prowlarr

Start the services for the first time:

```bash
docker compose up -d --build
```

Prowlarr listens on port `9696`. Instead of exposing its administration page publicly, open an SSH tunnel from your computer:

```bash
ssh -L 9696:localhost:9696 your-user@your-vps-ip
```

Visit `http://localhost:9696`, complete Prowlarr's initial setup, and add the indexers you are legally permitted to use. Test every indexer from within Prowlarr.

Copy the API key from **Settings → General**, add it to `PROWLARR_API_KEY` in `.env`, and restart tvbox:

```bash
docker compose restart app
```

Prowlarr may use FlareSolverr for compatible indexers that require a browser-like challenge solver. Configure its internal URL as:

```text
http://flaresolverr:8191
```

## 5. Deploy tvbox

Start the complete stack from the cloned repository:

```bash
docker compose up -d --build
```

The `--build` flag creates the local app image from the included Dockerfile; it does not mean writing or assembling the tvbox application yourself.

Check that every container is running:

```bash
docker compose ps
```

Test the health endpoint from the VPS:

```bash
curl http://localhost:8000/api/health
```

The expected response is:

```json
{"status":"ok"}
```

If a service fails, inspect its logs:

```bash
docker compose logs app
docker compose logs aria2c
docker compose logs prowlarr
```

At this stage, a local installation is available at `http://localhost:8000`, while a VPS installation is available at `http://your-vps-ip:8000` for a quick test.

## 6. Add Secure Remote Access with Cloudflare

Cloudflare Tunnel creates an outbound connection from the VPS to Cloudflare. This means visitors can reach tvbox through your domain without opening port `8000` to the public internet.

Skip this section when tvbox will only be used on the local machine.

In the Cloudflare dashboard:

1. Open **Zero Trust**.
2. Go to **Networks → Tunnels**.
3. Create a Cloudflared tunnel.
4. Choose Docker as the connector type.
5. Copy the generated tunnel token.
6. Add the token to `CLOUDFLARE_TUNNEL_TOKEN` in `.env`.

Restart the tunnel:

```bash
docker compose up -d cloudflared
```

Add a public hostname such as:

```text
tvbox.example.com
```

Set its service type to HTTP and its internal URL to:

```text
http://app:8000
```

Because `cloudflared` and `app` share the same Docker network, the tunnel can use the Compose service name instead of the VPS's public IP.

Open the hostname in a browser and sign in with `APP_PASSWORD`.

For another security layer, create a Cloudflare Access policy that only permits your email address.

Do not rely on the VPS firewall alone for Docker-published ports. Bind the app and Prowlarr to localhost, and remove the host mappings for aria2 RPC and FlareSolverr:

```yaml
services:
  app:
    ports:
      - "127.0.0.1:8000:8000"

  aria2c:
    ports:
      - "6888:6888"
      - "6888:6888/udp"

  prowlarr:
    ports:
      - "127.0.0.1:9696:9696"

  flaresolverr:
    ports: []
```

The containers can still communicate over their internal Compose network. Port `6888` remains published because it is the BitTorrent peer port, not an administration interface.

## 7. Set Up Infuse

The final step is connecting Infuse to the same Google Drive account.

In Infuse:

1. Open **Settings** or **Add Files**.
2. Choose **Add Cloud Service**.
3. Select Google Drive.
4. Sign in with the account configured in rclone.
5. Add the `Media` directory as a favorite or library location.
6. Let Infuse scan the folder and fetch metadata.

The exact labels vary slightly between Apple TV, iPhone, iPad, and Mac, but the process is the same. Once the first tvbox upload appears in Google Drive, refresh the share in Infuse.

Infuse handles the viewing side of the system: artwork, descriptions, playback progress, and streaming to supported devices.

## 8. Test and Troubleshoot

Run one complete test before relying on the setup:

1. Sign in to tvbox through the Cloudflare hostname.
2. Search for media that you are allowed to download.
3. Start a small download.
4. Watch its progress on the tvbox dashboard.
5. Confirm that the completed file appears in `gdrive:/Media`.
6. Confirm that the local file is removed after upload.
7. Refresh Infuse and play the file.

### Search returns no results

Open Prowlarr through the SSH tunnel and test its indexers. Confirm that `PROWLARR_API_KEY` in `.env` matches the key shown by Prowlarr.

### A download remains at 0 B/s

The release may have no active peers even if an indexer reports seeders. Try another result. Also confirm that the VPS provider permits the traffic and that TCP/UDP port `6888` is configured correctly.

### Google Drive uploads fail

Test the remote directly:

```bash
rclone lsd gdrive:
```

Then confirm that the configuration is visible in the app container:

```bash
docker compose exec app rclone lsd gdrive:
```

If the first command succeeds and the second fails, the rclone configuration mount is pointing to the wrong host path.

### The Cloudflare hostname shows an origin error

Check the tunnel logs:

```bash
docker compose logs cloudflared
```

Confirm that the hostname's service URL is `http://app:8000` and that the app container is healthy.

### Infuse does not show a new file

Verify the destination configured by `RCLONE_REMOTE`, check that the file exists in Google Drive, and refresh or rescan the relevant Infuse share.

## 9. Operate It Responsibly

A self-hosted service still needs maintenance:

- Install VPS security updates regularly.
- Pull tvbox updates and rebuild the stack when necessary.
- Back up `.env`, the rclone configuration, and any state you cannot recreate.
- Never expose Prowlarr, FlareSolverr, or aria2 RPC directly to the internet.
- Use unique passwords and rotate any credential that has been committed or shared.
- Monitor disk usage so an interrupted upload does not fill the VPS.
- Review Google Drive usage and account limits.
- Keep using the system only with media you have the right to access.

To update tvbox:

```bash
cd tvbox
git pull
docker compose up -d --build
```

To monitor storage and service health:

```bash
df -h
docker compose ps
```

That is the complete tvbox pipeline: search from a private browser interface, process the download on your own VPS, store the result in your Google Drive, and watch it through Infuse.
