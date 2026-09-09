#!/usr/bin/env bash
# Локальный запуск того же контура, что GitHub Actions: тесты + покрытие ≥ 90%.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m pip install -e "gateway[dev]"
"$PYTHON" -m pytest -q \
  --cov=onecmcp \
  --cov-report=term-missing \
  --cov-fail-under=90
