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
# Note: libjasper-dev and libjasper1 are not available on recent Raspberry Pi OS — removed.
# libwebp6/libtiff5 replaced by libwebp7/libtiff6 on bookworm — use generic names.
apt-get install -y \
  python3 python3-pip python3-venv \
  git curl wget \
  gcc python3-dev \
  network-manager \
  || { echo -e "${RED}Failed to install system packages${NC}"; exit 1; }

echo -e "${YELLOW}[2b/8] Installing wifi-connect (proven provisioning service)...${NC}"
WFC_VERSION="v4.11.84"
WFC_BASE_URL="https://github.com/balena-os/wifi-connect/releases/download/${WFC_VERSION}"
WFC_ARCH="$(uname -m)"

case "$WFC_ARCH" in
  armv7l)
    WFC_ASSET="wifi-connect-armv7-unknown-linux-gnueabihf.tar.gz"
    ;;
  aarch64)
    WFC_ASSET="wifi-connect-aarch64-unknown-linux-gnu.tar.gz"
    ;;
  *)
    echo -e "${RED}Unsupported architecture for wifi-connect: ${WFC_ARCH}${NC}"
    exit 1
    ;;
esac

WFC_TMP_DIR="$(mktemp -d)"
echo "Downloading ${WFC_ASSET}..."
curl -fL "${WFC_BASE_URL}/${WFC_ASSET}" | tar -xz -C "$WFC_TMP_DIR"
echo "Downloading wifi-connect UI..."
curl -fL "${WFC_BASE_URL}/wifi-connect-ui.tar.gz" | tar -xz -C "$WFC_TMP_DIR"

install -m 0755 "$WFC_TMP_DIR/wifi-connect" /usr/local/bin/wifi-connect
mkdir -p /usr/local/share/wifi-connect
rm -rf /usr/local/share/wifi-connect/ui

# UI archive layout changed over releases; detect extracted directory robustly.
if [ -d "$WFC_TMP_DIR/ui" ]; then
  UI_SRC_DIR="$WFC_TMP_DIR/ui"
elif [ -d "$WFC_TMP_DIR/wifi-connect-ui" ]; then
  UI_SRC_DIR="$WFC_TMP_DIR/wifi-connect-ui"
else
  UI_SRC_DIR="$(find "$WFC_TMP_DIR" -maxdepth 2 -type d \( -name ui -o -name wifi-connect-ui \) | head -n1)"
fi

if [ -z "$UI_SRC_DIR" ] || [ ! -d "$UI_SRC_DIR" ]; then
  echo -e "${RED}Could not locate extracted wifi-connect UI directory${NC}"
  exit 1
fi

mv "$UI_SRC_DIR" /usr/local/share/wifi-connect/ui
rm -rf "$WFC_TMP_DIR"

cat > /etc/systemd/system/wifi-connect.service <<'WFC_EOF'
[Unit]
Description=WiFi Connect provisioning portal
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStart=/usr/local/bin/wifi-connect
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
WFC_EOF

systemctl daemon-reload
echo "wifi-connect installed: $(/usr/local/bin/wifi-connect --version || echo unknown-version)"

echo -e "${YELLOW}[3/8] Setting up NetworkManager (disabling old networking)...${NC}"
# On Raspberry Pi OS Bookworm, dhcpcd is still the default Wi-Fi manager.
# We must stop it BEFORE disabling to avoid leaving wlan0 in a broken state.
systemctl stop dhcpcd.service 2>/dev/null || true
systemctl disable dhcpcd.service 2>/dev/null || true
systemctl stop networking.service 2>/dev/null || true
systemctl disable networking.service 2>/dev/null || true

# Ensure NetworkManager manages wlan0 (not unmanaged)
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/99-unmanaged-devices.conf <<'NMEOF'
[keyfile]
unmanaged-devices=none
NMEOF

# Make sure wlan0 is not listed as unmanaged in any interface file
sed -i '/wlan0/d' /etc/network/interfaces 2>/dev/null || true

systemctl enable NetworkManager
systemctl restart NetworkManager
sleep 3

# Bring up wlan0 explicitly
nmcli radio wifi on 2>/dev/null || true
ip link set wlan0 up 2>/dev/null || true
sleep 2

echo -e "${YELLOW}[4/8] Creating application directory and Python venv...${NC}"
INSTALL_DIR="/opt/led_bike_lights"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Copy source code if running from source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/src" ]; then
  SRC_PATH="$(readlink -f "$SCRIPT_DIR/src")"
  DST_PATH="$(readlink -f "$INSTALL_DIR/src")"

  if [ "$SRC_PATH" = "$DST_PATH" ]; then
    echo "Source already in $INSTALL_DIR/src, skipping copy."
  else
    echo "Copying source from $SCRIPT_DIR..."
    rm -rf "$INSTALL_DIR/src"
    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
  fi

  if [ -f "$SCRIPT_DIR/config.yaml" ]; then
    CONFIG_SRC="$(readlink -f "$SCRIPT_DIR/config.yaml")"
    CONFIG_DST="$(readlink -f "$INSTALL_DIR/config.yaml" 2>/dev/null || true)"
    if [ "$CONFIG_SRC" = "$CONFIG_DST" ]; then
      echo "config.yaml already in place, skipping copy."
    else
      cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR/"
      echo "config.yaml copied."
    fi
  else
    echo -e "${YELLOW}Warning: config.yaml not found in $SCRIPT_DIR — copy it manually:${NC}"
    echo "  sudo cp <path>/config.yaml $INSTALL_DIR/"
  fi
else
  echo -e "${YELLOW}Note: src/ not found. Copy manually:${NC}"
  echo "  sudo cp -r <repo>/src $INSTALL_DIR/"
  echo "  sudo cp <repo>/config.yaml $INSTALL_DIR/"
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

echo -e "${YELLOW}[5/8] Enabling PWM for LED data pin (GPIO 21)...${NC}"
# Pi Zero 2 uses /boot/firmware/config.txt on Bookworm
BOOT_CONFIG="/boot/firmware/config.txt"
if [ ! -f "$BOOT_CONFIG" ]; then
  BOOT_CONFIG="/boot/config.txt"  # Fallback for older OS
fi

if ! grep -q "^dtparam=spi=on" "$BOOT_CONFIG" 2>/dev/null; then
  echo "dtparam=spi=on" >> "$BOOT_CONFIG"
fi
if ! grep -q "^dtparam=i2c_arm=on" "$BOOT_CONFIG" 2>/dev/null; then
  echo "dtparam=i2c_arm=on" >> "$BOOT_CONFIG"
fi
# Enable audio off / PWM needed for WS281x on GPIO21
if ! grep -q "^dtparam=audio=off" "$BOOT_CONFIG" 2>/dev/null; then
  echo "dtparam=audio=off" >> "$BOOT_CONFIG"
  echo "# Disable onboard audio to free PWM for WS281x LEDs" >> "$BOOT_CONFIG"
fi

# Determine the runtime user for service ownership and execution.
# Priority: sudo invoker -> pi -> ppi -> first normal user.
ACTUAL_USER="${SUDO_USER:-}"
if [ -z "$ACTUAL_USER" ] || ! id "$ACTUAL_USER" >/dev/null 2>&1; then
  if id pi >/dev/null 2>&1; then
    ACTUAL_USER="pi"
  elif id ppi >/dev/null 2>&1; then
    ACTUAL_USER="ppi"
  else
    ACTUAL_USER="$(awk -F: '$3 >= 1000 && $3 < 65534 {print $1; exit}' /etc/passwd)"
  fi
fi

if [ -z "$ACTUAL_USER" ] || ! id "$ACTUAL_USER" >/dev/null 2>&1; then
  echo -e "${RED}Error: could not determine a valid non-root runtime user${NC}"
  exit 1
fi

echo "Using runtime user: $ACTUAL_USER"
for grp in gpio spi i2c; do
  getent group "$grp" &>/dev/null && usermod -aG "$grp" "$ACTUAL_USER" || true
done

echo -e "${YELLOW}[6/8] Installing systemd service...${NC}"
SERVICE_SRC="$SCRIPT_DIR/systemd/led-bike-lights.service"
SERVICE_DST="/etc/systemd/system/led-bike-lights.service"

if [ -f "$SERVICE_SRC" ]; then
  echo "Installing service unit from repository: $SERVICE_SRC"
  cp "$SERVICE_SRC" "$SERVICE_DST"
else
  echo "Repository service file not found, generating default unit"
  cat > "$SERVICE_DST" <<EOF
[Unit]
Description=LED Bike Wall Lights Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
# NeoPixel (rpi_ws281x) needs root for DMA/PWM access.
User=root
Group=root
WorkingDirectory=/opt/led_bike_lights
Environment="PATH=/opt/led_bike_lights/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/led_bike_lights/venv/bin/python3 /opt/led_bike_lights/src/app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
fi

# Do NOT chown service unit (must be root-owned)
systemctl daemon-reload
systemctl enable led-bike-lights.service

echo -e "${YELLOW}[7/8] Setting permissions...${NC}"
chown -R "${ACTUAL_USER}:${ACTUAL_USER}" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/src/app.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/start-service.sh" 2>/dev/null || true

echo -e "${YELLOW}[8/8] Creating necessary runtime directories...${NC}"
mkdir -p /run/led_bike_lights
chown "${ACTUAL_USER}:${ACTUAL_USER}" /run/led_bike_lights

# Enable Wi-Fi regulatory domain (adjust country code if not DE)
raspi-config nonint do_wifi_country DE 2>/dev/null || true

# Verify Wi-Fi is up before finishing
echo "Verifying Wi-Fi state..."
nmcli device status || true
ip -br link show wlan0 || true

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
echo "5. Fast redeploy + restart helper:"
echo "   sudo bash $SCRIPT_DIR/start-service.sh"
echo ""
