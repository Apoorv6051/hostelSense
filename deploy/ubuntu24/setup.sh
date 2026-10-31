#!/usr/bin/env bash
set -Eeuo pipefail

APP_USER="hostelsense"
APP_DIR="${APP_DIR:-/opt/hostelsense}"
CONFIG_DIR="/etc/hostelsense"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root: sudo bash deploy/ubuntu24/setup.sh" >&2
    exit 1
fi

if [[ ! -f "${REPO_DIR}/app.py" || ! -f "${REPO_DIR}/face-service/app.py" ]]; then
    echo "Run this script from a checked-out HostelSense repository." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    build-essential \
    ca-certificates \
    cmake \
    git \
    libboost-all-dev \
    libgtk-3-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    nginx \
    postgresql \
    postgresql-contrib \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    rsync \
    sudo

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    useradd --system --home-dir "${APP_DIR}" --create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}" "${CONFIG_DIR}"
rsync -a --delete \
    --exclude ".git/" \
    --exclude ".venv/" \
    --exclude "venv/" \
    --exclude "instance/*.db" \
    "${REPO_DIR}/" "${APP_DIR}/"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}/instance"

if [[ ! -d "${APP_DIR}/.venv" ]]; then
    sudo -u "${APP_USER}" python3.12 -m venv "${APP_DIR}/.venv"
fi
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/face-service/requirements.txt"

systemctl enable --now postgresql.service
INITIAL_INSTALL=0
if [[ ! -f "${CONFIG_DIR}/hostelsense.env" ]]; then
    INITIAL_INSTALL=1
    DB_PASSWORD="$(openssl rand -hex 24)"
    FACE_TOKEN="$(openssl rand -hex 32)"
    SECRET_KEY="$(openssl rand -hex 32)"
    ADMIN_SETUP_KEY="$(openssl rand -hex 24)"
fi

install -m 0644 "${REPO_DIR}/deploy/ubuntu24/hostelsense.service" /etc/systemd/system/hostelsense.service
install -m 0644 "${REPO_DIR}/deploy/ubuntu24/hostelsense-face.service" /etc/systemd/system/hostelsense-face.service
install -m 0644 "${REPO_DIR}/deploy/ubuntu24/nginx-hostelsense.conf" /etc/nginx/sites-available/hostelsense
ln -sfn /etc/nginx/sites-available/hostelsense /etc/nginx/sites-enabled/hostelsense
rm -f /etc/nginx/sites-enabled/default

if [[ ! -f "${CONFIG_DIR}/hostelsense.env" ]]; then
    cat > "${CONFIG_DIR}/hostelsense.env" <<EOF
APP_ENV=production
FLASK_DEBUG=0
SECRET_KEY=${SECRET_KEY}
SESSION_COOKIE_SECURE=1
DATABASE_URL=postgresql://hostelsense:${DB_PASSWORD}@127.0.0.1:5432/hostelsense
FACE_SERVICE_URL=http://127.0.0.1:5001
FACE_SERVICE_TOKEN=${FACE_TOKEN}
ADMIN_SETUP_KEY=${ADMIN_SETUP_KEY}
MAIL_FROM=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=1
EOF
    chmod 0600 "${CONFIG_DIR}/hostelsense.env"
fi
if [[ ! -f "${CONFIG_DIR}/hostelsense-face.env" ]]; then
    if [[ "${INITIAL_INSTALL}" -eq 0 ]]; then
        FACE_TOKEN="$(sed -n 's/^FACE_SERVICE_TOKEN=//p' "${CONFIG_DIR}/hostelsense.env")"
    fi
    cat > "${CONFIG_DIR}/hostelsense-face.env" <<EOF
HOST=127.0.0.1
PORT=5001
FLASK_DEBUG=0
FACE_SERVICE_TOKEN=${FACE_TOKEN}
ALLOWED_ORIGINS=https://your-domain.example
EOF
    chmod 0600 "${CONFIG_DIR}/hostelsense-face.env"
fi

if [[ "${INITIAL_INSTALL}" -eq 0 ]]; then
    DB_PASSWORD="$(sed -n 's#^DATABASE_URL=postgresql://hostelsense:\([^@]*\)@.*#\1#p' "${CONFIG_DIR}/hostelsense.env")"
fi
if [[ -z "${DB_PASSWORD:-}" ]]; then
    echo "DATABASE_URL in ${CONFIG_DIR}/hostelsense.env does not contain a database password." >&2
    exit 1
fi
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'hostelsense'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 \
        -c "ALTER ROLE hostelsense WITH LOGIN PASSWORD '${DB_PASSWORD}';"
else
    sudo -u postgres psql -v ON_ERROR_STOP=1 \
        -c "CREATE ROLE hostelsense LOGIN PASSWORD '${DB_PASSWORD}';"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'hostelsense'" | grep -q 1; then
    sudo -u postgres createdb -O hostelsense hostelsense
fi

systemctl daemon-reload
nginx -t
systemctl enable hostelsense-face.service hostelsense.service nginx.service
systemctl restart hostelsense-face.service hostelsense.service nginx.service

echo "Deployment installed at ${APP_DIR}."
echo "Configure HTTPS before production use, then verify: curl -fsS http://127.0.0.1/healthz"
