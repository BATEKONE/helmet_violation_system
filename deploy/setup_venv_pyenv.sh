#!/usr/bin/env bash
# Создание .venv на Python 3.10.14 через pyenv (VPS / Debian без python3.10 в apt).
# Запуск из корня проекта:
#   cd /opt/helmet_violation_system && bash deploy/setup_venv_pyenv.sh

set -euo pipefail

PYENV_VERSION="${PYENV_VERSION:-3.10.14}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi

if ! command -v pyenv >/dev/null 2>&1; then
  echo "ERROR: pyenv not found. Install pyenv first (see deploy/DEPLOY.md)." >&2
  exit 1
fi

if ! pyenv versions --bare | grep -qx "$PYENV_VERSION"; then
  echo "Installing Python $PYENV_VERSION via pyenv (may take several minutes)..."
  pyenv install "$PYENV_VERSION"
fi

pyenv local "$PYENV_VERSION"
echo "pyenv local -> $(cat .python-version)"

PYTHON_BIN="$(pyenv which python)"
echo "Using: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

if [[ -d .venv ]]; then
  VENV_VER="$(.venv/bin/python --version 2>&1 || true)"
  if [[ "$VENV_VER" != *"$PYENV_VERSION"* ]]; then
    echo "Removing .venv (was: $VENV_VER, need $PYENV_VERSION)"
    rm -rf .venv
  fi
fi

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

ACTUAL="$(python --version 2>&1)"
if [[ "$ACTUAL" != *"$PYENV_VERSION"* ]]; then
  echo "ERROR: .venv python is '$ACTUAL', expected $PYENV_VERSION" >&2
  exit 1
fi
echo "venv OK: $(which python) -> $ACTUAL"

pip install -U pip setuptools wheel

if [[ "${INSTALL_TORCH_CPU:-0}" == "1" ]] || [[ "${INSTALL_TORCH_CPU:-}" == "yes" ]]; then
  echo "Installing PyTorch CPU wheels first..."
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

pip install -r requirements.txt

echo ""
echo "Done. Verify:"
echo "  $PROJECT_DIR/.venv/bin/python --version"
echo "  $PROJECT_DIR/.venv/bin/python scripts/init_db.py"
