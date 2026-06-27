# kalp.dev — Personal Blog

Self-hosted [Ghost](https://ghost.org) blog running via Docker Compose on a local Ubuntu machine, exposed publicly through a Cloudflare Tunnel at [kalp.dev](https://kalp.dev).

## Stack

| Component | Details |
|---|---|
| **CMS** | Ghost 5 (Alpine) |
| **Database** | MySQL 8.0 |
| **Theme** | Custom `kalp-dev` theme |
| **Reverse proxy / TLS** | Cloudflare Tunnel (`cloudflared`) |
| **Public URL** | `https://kalp.dev` |

## Prerequisites

- Docker + Docker Compose
- [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) configured with a tunnel routing `kalp.dev → localhost:2368`

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Kalp-S/personal-website.git
cd personal-website
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Fill in your values:

```env
# Ghost
database__client=mysql
database__connection__host=db
database__connection__user=ghost
database__connection__password=your-db-password
database__connection__database=ghost_db
url=https://kalp.dev
NODE_ENV=production

# MySQL
MYSQL_ROOT_PASSWORD=your-root-password
MYSQL_USER=ghost
MYSQL_PASSWORD=your-db-password
MYSQL_DATABASE=ghost_db
```

### 3. Start the server

```bash
docker compose up -d
docker compose logs -f   # watch startup
```

Ghost will be live at **https://kalp.dev**.  
Admin panel: **https://kalp.dev/ghost**

## Custom Theme (`kalp-dev`)

The theme lives in [`content/themes/kalp-dev/`](./content/themes/kalp-dev/).

After making changes, either:
- Restart Ghost: `docker compose restart ghost`
- Or upload via the Ghost admin panel: **Settings → Design → Upload theme**

## Cloudflare Tunnel Config

Managed in `/etc/cloudflared/config.yml` on the host machine:

```yaml
tunnel: <tunnel-id>
credentials-file: /home/kalp/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: kalp.dev
    service: http://localhost:2368   # Ghost blog
  - hostname: joplin.kalp.dev
    service: http://localhost:22300  # Joplin Server
  - service: http_status:404
```

```bash
# Restart tunnel after config changes
sudo systemctl restart cloudflared
```

## Useful Commands

```bash
# View live logs
docker compose logs -f

# Restart Ghost only
docker compose restart ghost

# Stop everything
docker compose down

# Update to latest Ghost version
docker compose pull && docker compose up -d
```

## File Structure

```
.
├── docker-compose.yml            # Ghost + MySQL service definitions
├── .env                          # Secrets & config (gitignored)
├── .env.example                  # Safe config template
└── content/
    └── themes/
        └── kalp-dev/             # Custom Ghost theme (tracked)
            ├── package.json
            ├── default.hbs
            ├── home.hbs
            ├── index.hbs
            ├── post.hbs
            ├── page.hbs
            ├── tag.hbs
            ├── error.hbs
            ├── assets/
            └── partials/
```
