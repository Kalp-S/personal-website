#!/usr/bin/env bash
# =============================================================================
# Ghost Blog — Restore from Backup
#
# Usage:
#   ./scripts/restore.sh                  → interactive: list Drive backups, pick one
#   ./scripts/restore.sh <archive.tar.gz> → restore a specific local file directly
#
# What it restores:
#   - MySQL database (required)
#   - Ghost content directory (images, themes, media)
#   - .env and docker-compose.yml (optional, prompted)
# =============================================================================

set -euo pipefail

# --- Config (must match backup.sh) -------------------------------------------
BLOG_DIR="/home/kalp/git/blog"
BACKUP_DIR="${BLOG_DIR}/backups"
RCLONE_REMOTE="gdrive"
RCLONE_PATH="blog backups"
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

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $*"; }
die()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $*" >&2; exit 1; }

TMP_DIR=$(mktemp -d)
cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

# =============================================================================
# Step 1 — Determine which archive to restore
# =============================================================================
ARCHIVE_PATH=""

if [[ $# -ge 1 ]]; then
    # --- Direct file argument
    ARCHIVE_PATH="$1"
    [[ -f "${ARCHIVE_PATH}" ]] || die "File not found: ${ARCHIVE_PATH}"
    log "Using local archive: ${ARCHIVE_PATH}"
else
    # --- Interactive: list backups from Google Drive
    log "Fetching available backups from Google Drive (${RCLONE_REMOTE}:${RCLONE_PATH})..."
    mapfile -t REMOTE_FILES < <(
        rclone ls "${RCLONE_REMOTE}:${RCLONE_PATH}" 2>/dev/null \
        | grep 'blog-backup-.*\.tar\.gz' \
        | awk '{print $2}' \
        | sort -r
    )

    if [[ ${#REMOTE_FILES[@]} -eq 0 ]]; then
        die "No backups found in ${RCLONE_REMOTE}:${RCLONE_PATH}"
    fi

    echo ""
    echo "Available backups (newest first):"
    echo "-----------------------------------"
    for i in "${!REMOTE_FILES[@]}"; do
        printf "  [%d] %s\n" "$((i+1))" "${REMOTE_FILES[$i]}"
    done
    echo ""

    read -rp "Select backup to restore [1-${#REMOTE_FILES[@]}]: " SELECTION
    [[ "${SELECTION}" =~ ^[0-9]+$ ]] || die "Invalid selection."
    IDX=$((SELECTION - 1))
    [[ ${IDX} -ge 0 && ${IDX} -lt ${#REMOTE_FILES[@]} ]] || die "Selection out of range."

    CHOSEN="${REMOTE_FILES[$IDX]}"
    LOCAL_CACHED="${BACKUP_DIR}/${CHOSEN}"

    if [[ -f "${LOCAL_CACHED}" ]]; then
        log "Found cached locally, skipping download: ${LOCAL_CACHED}"
        ARCHIVE_PATH="${LOCAL_CACHED}"
    else
        log "Downloading ${CHOSEN} from Google Drive..."
        mkdir -p "${BACKUP_DIR}"
        rclone copy "${RCLONE_REMOTE}:${RCLONE_PATH}/${CHOSEN}" "${BACKUP_DIR}" --progress
        ARCHIVE_PATH="${BACKUP_DIR}/${CHOSEN}"
    fi
fi

log "Archive to restore: ${ARCHIVE_PATH} ($(du -sh "${ARCHIVE_PATH}" | cut -f1))"

# =============================================================================
# Step 2 — Safety confirmation
# =============================================================================
echo ""
warn "This will DROP and recreate tables in the '${DB_NAME}' database, replacing current blog posts & settings."
read -rp "Are you sure you want to proceed? Type YES to confirm: " CONFIRM
[[ "${CONFIRM}" == "YES" ]] || die "Aborted by user."

# =============================================================================
# Step 3 — Extract archive
# =============================================================================
log "Extracting archive..."
tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"
log "Contents extracted."

[[ -f "${TMP_DIR}/ghost_db.sql" ]] || die "Archive does not contain ghost_db.sql — invalid backup."

# =============================================================================
# Step 4 — Stop Ghost apps (keep DB running for restore)
# =============================================================================
log "Stopping Ghost containers (keeping MySQL running)..."
cd "${BLOG_DIR}"
docker compose stop ghost ghost-poetry 2>/dev/null || docker compose stop ghost
log "Ghost stopped."

# =============================================================================
# Step 5 — Restore MySQL databases
# =============================================================================
log "Restoring MySQL database '${DB_NAME}' from dump..."
docker exec -i "${DB_CONTAINER}" \
    mysql -u "${DB_USER}" -p"${DB_PASSWORD}" --default-character-set=utf8mb4 "${DB_NAME}" \
    < "${TMP_DIR}/ghost_db.sql"
log "✅ MySQL database '${DB_NAME}' restored."

if [[ -f "${TMP_DIR}/ghost_poetry_db.sql" ]]; then
    log "Restoring MySQL database 'ghost_poetry_db' from dump..."
    docker exec -i "${DB_CONTAINER}" \
        mysql -u "${DB_USER}" -p"${DB_PASSWORD}" --default-character-set=utf8mb4 ghost_poetry_db \
        < "${TMP_DIR}/ghost_poetry_db.sql"
    log "✅ MySQL database 'ghost_poetry_db' restored."
fi

# =============================================================================
# Step 6 — Restore Content Directories
# =============================================================================
if [[ -d "${TMP_DIR}/content" ]]; then
    log "Restoring content directory (themes, media, settings)..."
    cp -r "${TMP_DIR}/content" "${BLOG_DIR}/"
    log "✅ Content directory restored."
fi

if [[ -d "${TMP_DIR}/poetry-content" ]]; then
    log "Restoring poetry content directory..."
    cp -r "${TMP_DIR}/poetry-content" "${BLOG_DIR}/"
    log "✅ Poetry content directory restored."
fi

# =============================================================================
# Step 7 — Optionally restore config files
# =============================================================================
echo ""
read -rp "Restore .env and docker-compose.yml from backup? [y/N]: " RESTORE_CONFIG
if [[ "${RESTORE_CONFIG}" =~ ^[Yy]$ ]]; then
    if [[ -f "${TMP_DIR}/.env" ]]; then
        cp "${BLOG_DIR}/.env" "${BLOG_DIR}/.env.pre-restore.bak"
        cp "${TMP_DIR}/.env" "${BLOG_DIR}/.env"
        log "Restored .env (old version saved as .env.pre-restore.bak)"
    else
        warn ".env not found in archive, skipping."
    fi

    if [[ -f "${TMP_DIR}/docker-compose.yml" ]]; then
        cp "${BLOG_DIR}/docker-compose.yml" "${BLOG_DIR}/docker-compose.yml.pre-restore.bak"
        cp "${TMP_DIR}/docker-compose.yml" "${BLOG_DIR}/docker-compose.yml"
        log "Restored docker-compose.yml (old version saved as .pre-restore.bak)"
    else
        warn "docker-compose.yml not found in archive, skipping."
    fi
else
    log "Skipping config file restore."
fi

# =============================================================================
# Step 8 — Restart Ghost
# =============================================================================
log "Starting Ghost containers..."
docker compose start ghost ghost-poetry 2>/dev/null || docker compose start ghost
log "✅ Ghost started."

echo ""
log "🎉 Restore complete! Ghost blogs are back up at https://kalp.dev and https://poetry.kalp.dev"
log "   Restored from: $(basename "${ARCHIVE_PATH}")"

