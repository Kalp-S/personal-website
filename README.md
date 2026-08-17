# kalp.dev & poetry.kalp.dev — Personal Blog & Poetry Space

Self-hosted [Ghost](https://ghost.org) instances running via Docker Compose on a local Ubuntu machine, exposed publicly through Cloudflare Tunnels:
- **`https://kalp.dev`** — Software engineering blog, projects, resume, and technical writing.
- **`https://poetry.kalp.dev`** — Dedicated space for poetry, verse, and creative writing.

## Stack

| Component | Details |
|---|---|
| **CMS** | Ghost 5 (Alpine) — `ghost` (kalp.dev) & `ghost-poetry` (poetry.kalp.dev) |
| **Database** | MySQL 8.0 (`ghost_db` & `ghost_poetry_db`) |
| **Themes** | Custom `kalp-dev` theme & `poetry-theme` |
| **Reverse proxy / TLS** | Cloudflare Tunnel (`cloudflared`) |
| **Public URLs** | `https://kalp.dev` & `https://poetry.kalp.dev` |

## Prerequisites

- Docker + Docker Compose
- [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) configured with tunnel ingress routing:
  - `kalp.dev → localhost:2368`
  - `poetry.kalp.dev → localhost:2369`

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

Ghost sites will be live at:
- **https://kalp.dev** (Admin: `https://kalp.dev/ghost`)
- **https://poetry.kalp.dev** (Admin: `https://poetry.kalp.dev/ghost`)

## Custom Themes

- **Main Theme (`kalp-dev`)**: Lives in [`content/themes/kalp-dev/`](./content/themes/kalp-dev/).
- **Poetry Theme (`poetry-theme`)**: Lives in [`poetry-content/themes/poetry-theme/`](./poetry-content/themes/poetry-theme/).

After making changes, either:
- Restart Ghost: `docker compose restart ghost ghost-poetry`
- Or upload via the Ghost admin panel: **Settings → Design → Upload theme**

## Backup & Restore

Backups include full MySQL dumps for both databases (`ghost_db.sql` & `ghost_poetry_db.sql`) + Ghost content directories (`content/` & `poetry-content/`) + config files, stored in Google Drive (`gdrive:blog backups`). A systemd timer runs `scripts/backup.sh` daily at **2:30 AM**.

### Run a manual backup

```bash
./scripts/backup.sh
```

### Restore from a backup

```bash
./scripts/restore.sh               # interactive — lists Drive backups, you pick one
./scripts/restore.sh ./backups/blog-backup-2026-08-17_04-00-57.tar.gz  # direct file
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

# Restart Ghost instances
docker compose restart ghost ghost-poetry

# Stop everything
docker compose down

# Update to latest Ghost version
docker compose pull && docker compose up -d
```

## File Structure

```
.
├── docker-compose.yml            # Ghost (main & poetry) + MySQL service definitions
├── .env                          # Secrets & config (gitignored)
├── .env.example                  # Safe config template
├── scripts/
│   ├── backup.sh                 # Daily backup script (multi-db & multi-content)
│   ├── restore.sh                # Interactive restore script
│   ├── test_blog.sh              # Integration test runner
│   ├── migrate-poetry-out.sql    # Clean up SQL for kalp.dev
│   └── seed-poetry-db.sql        # Seed SQL for poetry.kalp.dev
├── tests/
│   └── test_blog_service.py      # Python integration test suite
├── backups/                      # Local backup archives (gitignored)
├── content/
│   └── themes/
│       └── kalp-dev/             # Custom Ghost theme for kalp.dev
└── poetry-content/
    └── themes/
        └── poetry-theme/         # Custom Ghost theme for poetry.kalp.dev
```


