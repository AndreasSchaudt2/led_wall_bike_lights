#!/bin/bash
# LED Bike Wall Installation Script
# For Raspberry Pi Zero 2 WH running Raspberry Pi OS Lite
# Usage: sudo bash install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LED Bike Wall Installation ===${NC}"

# Detect if running as root
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Error: This script must be run with sudo${NC}"
  exit 1
fi

# Detect Raspberry Pi model and OS
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
  echo -e "${YELLOW}Warning: Not running on Raspberry Pi, but continuing...${NC}"
fi

echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
apt-get update || true
apt-get upgrade -y || true

echo -e "${YELLOW}[2/8] Installing Python and dependencies...${NC}"
apt-get install -y \
  python3 python3-pip python3-venv \
  git curl wget \
  gcc python3-dev \
  libatlas-base-dev libjasper-dev libtiff5 libjasper1 libharfbuzz0b libwebp6 libtiff5 \
  NetworkManager \
  || { echo -e "${RED}Failed to install system packages${NC}"; exit 1; }

echo -e "${YELLOW}[3/8] Setting up NetworkManager (disabling old networking)...${NC}"
systemctl disable dhcpcd.service 2>/dev/null || true
systemctl stop dhcpcd.service 2>/dev/null || true
systemctl disable networking.service 2>/dev/null || true
systemctl stop networking.service 2>/dev/null || true
systemctl enable NetworkManager
systemctl restart NetworkManager
sleep 2

echo -e "${YELLOW}[4/8] Creating application directory and Python venv...${NC}"
INSTALL_DIR="/opt/led_bike_lights"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Copy source code if running from source directory
if [ -d "$(pwd -P)/../src" ]; then
  echo "Copying source from local directory..."
  cp -r "$(pwd -P)/../src" .
  cp "$(pwd -P)/../config.yaml" .
else
  echo "Note: Copy your src/ folder and config.yaml to $INSTALL_DIR"
fi

# Create Python virtual environment
if [ ! -d "venv" ]; then
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip setuptools wheel
  
  # Install core dependencies (will be extended as you add modules)
  pip install pyyaml flask bleak adafruit-circuitpython-neopixel RPi.GPIO
  
  deactivate
fi

echo -e "${YELLOW}[5/8] Enabling SPI and I2C (if needed for LED drivers)...${NC}"
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
  echo "dtparam=spi=on" >> /boot/firmware/config.txt
fi
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null; then
  echo "dtparam=i2c_arm=on" >> /boot/firmware/config.txt
fi

# Allow GPIO access
usermod -aG gpio pi 2>/dev/null || true
usermod -aG spi pi 2>/dev/null || true
usermod -aG i2c pi 2>/dev/null || true

echo -e "${YELLOW}[6/8] Installing systemd service...${NC}"
cat > /etc/systemd/system/led-bike-lights.service <<'EOF'
[Unit]
Description=LED Bike Wall Lights Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/led_bike_lights
Environment="PATH=/opt/led_bike_lights/venv/bin"
ExecStart=/opt/led_bike_lights/venv/bin/python3 /opt/led_bike_lights/app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chown pi:pi /etc/systemd/system/led-bike-lights.service
systemctl daemon-reload
systemctl enable led-bike-lights.service

echo -e "${YELLOW}[7/8] Setting permissions...${NC}"
chown -R pi:pi "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/app.py" 2>/dev/null || true

echo -e "${YELLOW}[8/8] Creating necessary runtime directories...${NC}"
mkdir -p /run/led_bike_lights
chown pi:pi /run/led_bike_lights

# Enable Wi-Fi regulatory domain
raspi-config nonint do_wifi_country DE 2>/dev/null || true

echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Verify Wi-Fi connection:"
echo "   nmcli device status"
echo "   ping 1.1.1.1"
echo ""
echo "2. Copy/create your app.py to: $INSTALL_DIR/"
echo ""
echo "3. Test the service:"
echo "   sudo systemctl start led-bike-lights.service"
echo "   journalctl -u led-bike-lights.service -f"
echo ""
echo "4. Once working, enable auto-start:"
echo "   sudo systemctl enable led-bike-lights.service"
echo "   sudo systemctl start led-bike-lights.service"
echo ""
