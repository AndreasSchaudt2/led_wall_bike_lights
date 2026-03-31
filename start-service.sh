#!/bin/bash
# Deploy latest local code to /opt and start/restart service.
# Usage: sudo bash start-service.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: run with sudo${NC}"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/led_bike_lights"
SERVICE_NAME="led-bike-lights.service"
SERVICE_SRC="$SCRIPT_DIR/systemd/led-bike-lights.service"
SERVICE_DST="/etc/systemd/system/led-bike-lights.service"

echo -e "${YELLOW}Deploying project files to ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"

if [ -d "$SCRIPT_DIR/src" ]; then
  rm -rf "$INSTALL_DIR/src"
  cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
  echo "Copied src/"
else
  echo -e "${RED}Error: src/ not found in ${SCRIPT_DIR}${NC}"
  exit 1
fi

# Preserve device-local config by default.
if [ ! -f "$INSTALL_DIR/config.yaml" ] && [ -f "$SCRIPT_DIR/config.yaml" ]; then
  cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR/"
  echo "Copied config.yaml (destination was missing)"
else
  echo "Keeping existing $INSTALL_DIR/config.yaml"
fi

if [ -f "$SERVICE_SRC" ]; then
  cp "$SERVICE_SRC" "$SERVICE_DST"
  echo "Updated systemd service file"
fi

chmod +x "$INSTALL_DIR/src/app.py" 2>/dev/null || true

echo -e "${YELLOW}Reloading and restarting ${SERVICE_NAME}...${NC}"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo -e "${GREEN}Done.${NC}"
echo "Status:"
systemctl status "$SERVICE_NAME" --no-pager -l
