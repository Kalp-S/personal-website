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

## Backup & Restore

Backups include a full MySQL dump + Ghost content directory (`content/`) + config files, stored in Google Drive (`gdrive:blog backups`). A systemd timer runs `scripts/backup.sh` daily at **2:30 AM**.

### Run a manual backup

```bash
./scripts/backup.sh
```

### Restore from a backup

```bash
./scripts/restore.sh               # interactive — lists Drive backups, you pick one
./scripts/restore.sh ./backups/blog-backup-2026-08-17_03-27-08.tar.gz  # direct file
```

> **Note:** Restore will prompt you to type `YES` before replacing MySQL database and content files.

### Check backup timer status

```bash
systemctl list-timers blog-backup.timer
journalctl -u blog-backup.service -n 50
```

## Running Tests

An automated integration test suite is provided in `tests/test_blog_service.py`:

```bash
./scripts/test_blog.sh
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
├── scripts/
│   ├── backup.sh                 # Daily backup script
│   ├── restore.sh                # Interactive restore script
│   └── test_blog.sh              # Integration test runner
├── tests/
│   └── test_blog_service.py      # Python integration test suite
├── backups/                      # Local backup archives (gitignored)
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

