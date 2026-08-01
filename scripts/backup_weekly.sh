#!/usr/bin/env bash

set -Eeuo pipefail
umask 077
export TZ="Asia/Jakarta"

APP_DIR="/home/evpro/EVPRO_ERP"
DB_PATH="$APP_DIR/instance/erp.db"
BACKUP_DIR="/home/evpro/backups/EVPRO_ERP"

TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_NAME="evpro_weekly_${TIMESTAMP}"
ARCHIVE_PATH="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"
LOG_PATH="$BACKUP_DIR/backup.log"
WORK_DIR="$(mktemp -d "$BACKUP_DIR/.backup_work_XXXXXX")"

cleanup() {
    rm -rf "$WORK_DIR"
}

trap cleanup EXIT

exec >>"$LOG_PATH" 2>&1

echo
echo "===================================================="
echo "Backup dimulai: $(date '+%d/%m/%Y %H:%M:%S')"
echo "===================================================="

if [[ ! -d "$APP_DIR" ]]; then
    echo "ERROR: Folder aplikasi tidak ditemukan: $APP_DIR"
    exit 1
fi

if [[ ! -f "$DB_PATH" ]]; then
    echo "ERROR: Database tidak ditemukan: $DB_PATH"
    exit 1
fi

mkdir -p \
    "$WORK_DIR/database" \
    "$WORK_DIR/config" \
    "$WORK_DIR/metadata"

echo "Membuat backup database SQLite..."

python3 - "$DB_PATH" "$WORK_DIR/database/erp.db" <<'PYTHON'
import os
import sqlite3
import sys

source_path = sys.argv[1]
backup_path = sys.argv[2]

os.makedirs(os.path.dirname(backup_path), exist_ok=True)

source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
destination = sqlite3.connect(backup_path)

try:
    source.backup(destination)

    integrity = destination.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(
            f"SQLite integrity check gagal: {integrity}"
        )
finally:
    destination.close()
    source.close()

print("Backup SQLite berhasil dan integrity_check = ok")
PYTHON

echo "Membuat snapshot folder project..."

tar \
    --exclude='./.git' \
    --exclude='./venv' \
    --exclude='./.venv' \
    --exclude='./__pycache__' \
    --exclude='./.pytest_cache' \
    --exclude='./backups' \
    --exclude='./instance/erp.db' \
    --exclude='./instance/erp.db-wal' \
    --exclude='./instance/erp.db-shm' \
    --exclude='./*.pyc' \
    --exclude='./logs' \
    -czf "$WORK_DIR/project.tar.gz" \
    -C "$APP_DIR" .

echo "Menyimpan informasi Git..."

git -C "$APP_DIR" rev-parse HEAD \
    > "$WORK_DIR/metadata/git_commit.txt" 2>/dev/null || true

git -C "$APP_DIR" branch --show-current \
    > "$WORK_DIR/metadata/git_branch.txt" 2>/dev/null || true

git -C "$APP_DIR" status --short \
    > "$WORK_DIR/metadata/git_status.txt" 2>/dev/null || true

date '+%d/%m/%Y %H:%M:%S %Z' \
    > "$WORK_DIR/metadata/backup_time.txt"

hostname \
    > "$WORK_DIR/metadata/hostname.txt"

if [[ -x "$APP_DIR/venv/bin/pip" ]]; then
    "$APP_DIR/venv/bin/pip" freeze \
        > "$WORK_DIR/metadata/pip_freeze.txt" 2>/dev/null || true
fi

echo "Menyimpan konfigurasi server..."

for CONFIG_FILE in \
    "/etc/systemd/system/evpro-erp.service" \
    "/etc/nginx/sites-available/erp.evprotextile.com" \
    "/etc/nginx/sites-enabled/erp.evprotextile.com"
do
    if [[ -r "$CONFIG_FILE" ]]; then
        cp -L "$CONFIG_FILE" "$WORK_DIR/config/" 2>/dev/null || true
    fi
done

echo "Membuat arsip akhir..."

tar -czf "$ARCHIVE_PATH" -C "$WORK_DIR" .

echo "Memeriksa arsip..."

tar -tzf "$ARCHIVE_PATH" >/dev/null

sha256sum "$ARCHIVE_PATH" > "$CHECKSUM_PATH"

chmod 600 "$ARCHIVE_PATH" "$CHECKSUM_PATH" "$LOG_PATH"

echo "Menghapus backup lama dan menyimpan 8 backup terbaru..."

ls -1t "$BACKUP_DIR"/evpro_weekly_*.tar.gz 2>/dev/null \
    | tail -n +9 \
    | while read -r OLD_BACKUP
do
    rm -f "$OLD_BACKUP" "${OLD_BACKUP}.sha256"
done

BACKUP_SIZE="$(du -h "$ARCHIVE_PATH" | cut -f1)"

echo "Backup berhasil."
echo "File: $ARCHIVE_PATH"
echo "Ukuran: $BACKUP_SIZE"
echo "Selesai: $(date '+%d/%m/%Y %H:%M:%S')"
