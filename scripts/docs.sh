#!/usr/bin/env bash
# Сборка сайта документации (MkDocs Material).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -r requirements-docs.txt
"$PYTHON" -m mkdocs build --strict
