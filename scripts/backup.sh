#!/usr/bin/env bash
# =============================================================================
# Ghost Blog — Daily Backup Script
# Backs up: MySQL DB dump + content directory + config files
# Uploads to: Google Drive via rclone
# =============================================================================

set -euo pipefail

# --- Config ------------------------------------------------------------------
BLOG_DIR="/home/kalp/git/blog"
BACKUP_DIR="${BLOG_DIR}/backups"
RCLONE_REMOTE="gdrive"                        # rclone remote name (set during rclone config)
RCLONE_PATH="blog backups"                    # folder in your Google Drive
KEEP_LOCAL_DAYS=7                             # how many days of local backups to keep
DB_CONTAINER="blog-db-1"
DB_NAME="ghost_db"
DB_USER="ghost"
DB_PASSWORD="${MYSQL_PASSWORD:-ghostpassword}"
# -----------------------------------------------------------------------------

# Load DB password from .env if present
if [[ -f "${BLOG_DIR}/.env" ]]; then
    ENV_PASS=$(grep -E '^MYSQL_PASSWORD=' "${BLOG_DIR}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    if [[ -n "${ENV_PASS}" ]]; then
        DB_PASSWORD="${ENV_PASS}"
    fi
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
ARCHIVE_NAME="blog-backup-${TIMESTAMP}.tar.gz"
TMP_DIR=$(mktemp -d)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

log "Starting Ghost blog backup: ${ARCHIVE_NAME}"

# 1. Dump MySQL databases from inside the container
log "Dumping MySQL database (${DB_NAME})..."
docker exec "${DB_CONTAINER}" \
    mysqldump -u "${DB_USER}" -p"${DB_PASSWORD}" --default-character-set=utf8mb4 --no-tablespaces "${DB_NAME}" \
    > "${TMP_DIR}/ghost_db.sql"
log "ghost_db dump complete ($(du -sh "${TMP_DIR}/ghost_db.sql" | cut -f1))"

log "Dumping MySQL database (ghost_poetry_db)..."
docker exec "${DB_CONTAINER}" \
    mysqldump -u "${DB_USER}" -p"${DB_PASSWORD}" --default-character-set=utf8mb4 --no-tablespaces ghost_poetry_db \
    > "${TMP_DIR}/ghost_poetry_db.sql"
log "ghost_poetry_db dump complete ($(du -sh "${TMP_DIR}/ghost_poetry_db.sql" | cut -f1))"

log "Dumping MySQL database (ghost_blog_db)..."
docker exec "${DB_CONTAINER}" \
    mysqldump -u "${DB_USER}" -p"${DB_PASSWORD}" --default-character-set=utf8mb4 --no-tablespaces ghost_blog_db \
    > "${TMP_DIR}/ghost_blog_db.sql"
log "ghost_blog_db dump complete ($(du -sh "${TMP_DIR}/ghost_blog_db.sql" | cut -f1))"

# 2. Copy content folders (images, media, themes, settings) and config files
log "Copying Ghost content directories..."
cp -r "${BLOG_DIR}/content" "${TMP_DIR}/"
if [[ -d "${BLOG_DIR}/poetry-content" ]]; then
    cp -r "${BLOG_DIR}/poetry-content" "${TMP_DIR}/"
fi
if [[ -d "${BLOG_DIR}/blog-content" ]]; then
    cp -r "${BLOG_DIR}/blog-content" "${TMP_DIR}/"
fi

log "Copying configuration files..."
cp "${BLOG_DIR}/docker-compose.yml" "${TMP_DIR}/"
if [[ -f "${BLOG_DIR}/.env" ]]; then
    cp "${BLOG_DIR}/.env" "${TMP_DIR}/"
fi

# 3. Create compressed archive
log "Creating archive..."
mkdir -p "${BACKUP_DIR}"
tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "${TMP_DIR}" .
log "Archive created: ${BACKUP_DIR}/${ARCHIVE_NAME} ($(du -sh "${BACKUP_DIR}/${ARCHIVE_NAME}" | cut -f1))"

# 4. Upload to Google Drive
log "Uploading to Google Drive (${RCLONE_REMOTE}:${RCLONE_PATH})..."
rclone copy "${BACKUP_DIR}/${ARCHIVE_NAME}" "${RCLONE_REMOTE}:${RCLONE_PATH}" \
    --progress \
    --stats-one-line
log "Upload complete."

# 5. Prune local backups older than KEEP_LOCAL_DAYS
log "Pruning local backups older than ${KEEP_LOCAL_DAYS} days..."
find "${BACKUP_DIR}" -name "blog-backup-*.tar.gz" \
    -mtime "+${KEEP_LOCAL_DAYS}" -delete
log "Local cleanup done. Current backups:"
ls -lh "${BACKUP_DIR}/" | tail -10

log "Backup finished successfully: ${ARCHIVE_NAME}"
