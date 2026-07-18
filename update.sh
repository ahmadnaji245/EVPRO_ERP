#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${SERVICE_NAME:-evpro-erp}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5003}"

cd "$PROJECT_DIR"

echo "Project directory: ${PROJECT_DIR}"
echo "Checking Git status..."
git status --short

echo "Pulling latest changes from origin/main..."
if ! git pull origin main; then
    echo "ERROR: git pull failed."
    echo "If this failed because of local changes, review them manually on the VPS."
    echo "This script will not stash, reset, discard changes, or restart ${SERVICE_NAME}."
    exit 1
fi

if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
elif [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
else
    echo "No virtualenv found. Creating venv/..."
    python3 -m venv venv
    # shellcheck disable=SC1091
    source "venv/bin/activate"
fi

python -m pip install -r requirements.txt
if [ -f "requirements-prod.txt" ]; then
    python -m pip install -r requirements-prod.txt
fi

echo "Restarting ${SERVICE_NAME}..."
sudo systemctl restart evpro-erp
sudo systemctl --no-pager status evpro-erp

echo "Running health check: ${HEALTH_URL}"
if ! curl -f "$HEALTH_URL"; then
    echo "ERROR: health check failed."
    echo "Last ${SERVICE_NAME} logs:"
    sudo journalctl -u evpro-erp -n 50 --no-pager
    exit 1
fi
