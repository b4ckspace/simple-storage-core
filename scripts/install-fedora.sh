#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/lager-mc"
APPLICATIONS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
DESKTOP_FILE="${APPLICATIONS_DIR}/lager-mc.desktop"
ICON_TARGET="${ICONS_DIR}/lager-mc.svg"

echo "Installiere Systemabhaengigkeiten fuer Fedora ..."
sudo dnf install -y \
  python3 \
  python3-devel \
  gcc \
  postgresql-devel \
  redhat-rpm-config

echo "Erzeuge virtuelle Umgebung in ${VENV_DIR} ..."
python3 -m venv "${VENV_DIR}"

echo "Installiere Python-Abhaengigkeiten ..."
"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements.txt"

mkdir -p "${BIN_DIR}"
mkdir -p "${APPLICATIONS_DIR}"
mkdir -p "${ICONS_DIR}"

cat > "${LAUNCHER}" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/python" "${PROJECT_DIR}/lager_mc.py" "\$@"
EOF

chmod +x "${LAUNCHER}"

install -m 0644 "${PROJECT_DIR}/assets/lager-mc.svg" "${ICON_TARGET}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Lager MC
Comment=Terminaloberflaeche fuer Lagerverwaltung
Exec=${LAUNCHER}
Icon=${ICON_TARGET}
Terminal=true
Categories=Office;Utility;
Keywords=Lager;Inventar;Shopify;
StartupNotify=true
EOF

echo
echo "Installation abgeschlossen."
echo "Starten mit:"
echo "  ${LAUNCHER}"
echo
echo "Ein Startmenue-Eintrag wurde angelegt:"
echo "  ${DESKTOP_FILE}"
echo
echo "Falls ~/.local/bin noch nicht im PATH ist, einmal neu einloggen oder manuell aufrufen."
