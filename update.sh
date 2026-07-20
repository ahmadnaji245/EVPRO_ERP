#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${SERVICE_NAME:-evpro-erp}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5003/}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

cd "$SCRIPT_DIR"
echo "Project directory: $SCRIPT_DIR"
echo "Current commit: $(git rev-parse --short HEAD)"

[[ "$(git branch --show-current)" == "main" ]] || fail "deployment hanya boleh dijalankan dari branch main."
[[ ! -d .git/rebase-merge && ! -d .git/rebase-apply ]] || fail "rebase sedang berjalan; selesaikan secara manual terlebih dahulu."
[[ ! -f .git/MERGE_HEAD ]] || fail "merge sedang berjalan; selesaikan secara manual terlebih dahulu."

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    git status --short
    fail "terdapat perubahan tracked lokal. Script tidak akan stash, reset, atau membuang perubahan tersebut."
fi

echo "Fetching origin/main..."
git fetch origin main

if ! git merge-base --is-ancestor HEAD origin/main; then
    echo "Local HEAD:  $(git rev-parse --short HEAD)" >&2
    echo "Origin main: $(git rev-parse --short origin/main)" >&2
    fail "branch VPS memiliki commit lokal atau divergent. Push/review commit secara manual; merge dan rebase otomatis tidak dilakukan."
fi

echo "Updating source with fast-forward only..."
git pull --ff-only origin main || fail "fast-forward gagal; aplikasi tidak akan di-restart."

if [[ -x "venv/bin/python" ]]; then
    VENV_DIR="venv"
elif [[ -x ".venv/bin/python" ]]; then
    VENV_DIR=".venv"
else
    fail "virtualenv production tidak ditemukan di venv/ atau .venv/."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install -r requirements.txt
if [[ -f requirements-prod.txt ]]; then
    python -m pip install -r requirements-prod.txt
fi
python -m compileall -q -x '(^|/)(venv|\.venv|\.git|backups|static/uploads)(/|$)' .

echo "Restarting $SERVICE_NAME..."
sudo systemctl restart "$SERVICE_NAME"
if ! sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl --no-pager --full status "$SERVICE_NAME" || true
    sudo journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
    fail "$SERVICE_NAME gagal aktif setelah restart."
fi

echo "Waiting for health check: $HEALTH_URL"
healthy=false
for attempt in {1..10}; do
    if curl --max-time 5 -fsSL "$HEALTH_URL" >/dev/null; then
        healthy=true
        break
    fi
    echo "Health check attempt $attempt/10 belum berhasil; menunggu 2 detik..."
    sleep 2
done

if [[ "$healthy" != true ]]; then
    sudo systemctl --no-pager --full status "$SERVICE_NAME" || true
    sudo journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
    fail "health check gagal setelah 10 percobaan."
fi

echo "Deployment successful. Active commit: $(git rev-parse --short HEAD)"
