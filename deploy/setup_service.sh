#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Deploying Children service from: ${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Error: Python binary '${PYTHON_BIN}' not found!"
    exit 1
fi

VENV_DIR="${REPO_ROOT}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    echo "==> Creating virtualenv at ${VENV_DIR}..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

echo "==> Installing requirements..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${REPO_ROOT}/backend/requirements.txt"

# 3. 检查环境配置文件
if [ ! -f "${SCRIPT_DIR}/children.env" ]; then
    if [ -f "${SCRIPT_DIR}/children.env.example" ]; then
        echo "==> Initializing ${SCRIPT_DIR}/children.env from example..."
        cp "${SCRIPT_DIR}/children.env.example" "${SCRIPT_DIR}/children.env"
        SECRET_KEY="$(${PYTHON_BIN} -c 'import secrets; print(secrets.token_hex(32))')"
        sed -i "s|^AUTH_SECRET=.*|AUTH_SECRET=${SECRET_KEY}|" "${SCRIPT_DIR}/children.env"
        echo "Notice: Please configure AUTH_USERNAME and AUTH_PASSWORD_HASH in ${SCRIPT_DIR}/children.env"
    fi
fi

# 4. 生成 systemd service 文件
SERVICE_TARGET="/etc/systemd/system/children.service"
CURRENT_USER="$(id -un)"
CURRENT_GROUP="$(id -gn)"

echo "==> Installing systemd service to ${SERVICE_TARGET}..."
sed -e "s|{{USER}}|${CURRENT_USER}|g" \
    -e "s|{{GROUP}}|${CURRENT_GROUP}|g" \
    -e "s|{{APP_ROOT}}|${REPO_ROOT}|g" \
    -e "s|{{PYTHON_VENV}}|${VENV_DIR}|g" \
    "${SCRIPT_DIR}/children.service.template" | sudo tee "${SERVICE_TARGET}" > /dev/null

echo "==> Reloading and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable children.service
sudo systemctl restart children.service

echo "==> Done! Children service status:"
sudo systemctl status children.service --no-pager
