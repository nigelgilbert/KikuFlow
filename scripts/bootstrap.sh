#!/bin/sh
# Install the pinned Python and the sidecar into ~/Library/Application Support/KikuFlow/venv.
# Idempotent: a second run only syncs the venv to uv.lock and reinstalls the sidecar package,
# so an app update with new sidecar source takes effect.
set -eu

# Apps launched from Finder get a minimal PATH; look where uv's installers put it.
PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "Kiku Flow needs uv. Install it with 'brew install uv' or see https://docs.astral.sh/uv/" >&2
    exit 1
fi

sidecar="$(cd "$(dirname "$0")/../sidecar" && pwd)"
export UV_PROJECT_ENVIRONMENT="$HOME/Library/Application Support/KikuFlow/venv"
uv sync --project "$sidecar" --frozen --no-dev --no-editable --python-preference only-managed \
    --reinstall-package kiku-sidecar
