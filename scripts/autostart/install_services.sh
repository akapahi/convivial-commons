#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="/etc/systemd/system"
ENV_DIR="/etc/convivial-commons"
ENV_FILE="${ENV_DIR}/convivial.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (e.g. sudo ./scripts/autostart/install_services.sh)"
  exit 1
fi

mkdir -p "${ENV_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  cat > "${ENV_FILE}" <<'ENVEOF'
OPENAI_API_KEY=replace_me
PHYSICAL_SERVER_URL=http://127.0.0.1:9000
ENVEOF
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit it before production use."
fi

install -m 644 "${REPO_DIR}/scripts/autostart/convivial.service" "${SERVICE_DIR}/convivial.service"
install -m 644 "${REPO_DIR}/scripts/autostart/drama.service" "${SERVICE_DIR}/drama.service"

systemctl daemon-reload
systemctl enable drama.service convivial.service
systemctl restart drama.service convivial.service

echo "Installed and started drama.service + convivial.service"
