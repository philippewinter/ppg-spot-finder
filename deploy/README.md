# Deploying PPG Spot Finder

The app is a single static file (`PPG-Spot-Finder.html`) with all data inlined.
It needs no backend or database — just a web server. These files wrap it in a
tiny nginx container.

## Files
- `Dockerfile` — nginx:alpine serving the HTML as `index.html`
- `nginx.conf` — gzip + cache headers (2.2 MB raw → ~650 KB gzipped)
- `docker-compose.yml` — one-command run, restarts automatically

## Option A — docker compose (simplest)
From the **project root** (the folder containing `PPG-Spot-Finder.html`):

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

The site is now live on the server at `http://<server-ip>:8085`.

Update after rebuilding the app (`scripts/build_app.py`):
```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

Stop it:
```bash
docker compose -f deploy/docker-compose.yml down
```

## Option B — plain docker
```bash
# from project root
docker build -t ppg-spot-finder -f deploy/Dockerfile .
docker run -d --name ppg-spot-finder --restart unless-stopped -p 8085:80 ppg-spot-finder
```

## Making it a public website (domain + HTTPS)
The container serves plain HTTP on a port. To expose it at a real domain with
a TLS certificate, put a reverse proxy in front — do NOT expose port 8085 raw.

1. Point a DNS A record (e.g. `ppg.yourdomain.com`) at your Hostinger VPS IP.
2. Route it to `127.0.0.1:8085` with one of:
   - **Coolify** (Hostinger's default VPS panel): New Resource → Docker Compose →
     paste this repo → set the domain → Coolify issues Let's Encrypt TLS automatically.
   - **Nginx Proxy Manager**: add a Proxy Host → domain → forward to
     `<host>:8085` → enable SSL (Let's Encrypt).
   - **Caddy / Traefik**: add a route to the container with automatic HTTPS.

## Notes
- Map tiles (Carto/Esri) and Leaflet load from public CDNs, so the server needs
  outbound internet — normal for any VPS.
- Everything is read-only static content: nothing to secure server-side, no
  secrets, no user data.
