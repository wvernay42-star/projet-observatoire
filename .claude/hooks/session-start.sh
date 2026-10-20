#!/bin/bash
# Prépare l'environnement à chaque session Claude Code cloud.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"
uv sync --python 3.12 --quiet
[ -f .env ] || cp .env.example .env
uv run python -m pipeline.init_db >/dev/null
echo 'source .venv/bin/activate' >> "${CLAUDE_ENV_FILE:-/dev/null}"
