# Installation Guide

## Overview
This guide covers setting up the LED Bike Wall Lights project on a fresh Raspberry Pi Zero 2 WH.

## Prerequisites
- **Hardware**: Raspberry Pi Zero 2 WH, 4GB microSD card, power adapter (USB-C), addressable LED strip, 2 GPIO buttons
- **Computer**: Linux, macOS, or Windows with SD card reader
- **OS**: Fresh Raspberry Pi OS Lite (latest) flashed to SD card

## Pre-Installation: OS Setup

### 1. Flash Raspberry Pi OS
Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

1. Download and open Imager
2. Select Device: **Raspberry Pi Zero 2 W**
3. Select OS: **Raspberry Pi OS** (or Lite for minimal footprint)
4. Select Storage: your SD card
5. Advanced Options (⚙️ icon):
   - Hostname: `bikelights` (or your preferred name)
   - Enable SSH: YES
   - Username: `pi` (default)
   - Password: your chosen password
   - Configure Wi-Fi:
     - SSID: your home network
     - Password: your Wi-Fi password
     - Country: DE (or your region)
6. Click **Write** and wait for completion (~5 min)

### 2. First Boot & SSH Connection
1. Insert flashed SD card into Pi and power on
2. Wait ~60 seconds for first boot configuration
3. On your computer, open a terminal:
   ```bash
   ssh pi@bikelights
   # or if hostname doesn't resolve:
   ssh pi@<IP_ADDRESS>
   ```
4. Verify internet connectivity:
   ```bash
   ip route
   ping -c 3 1.1.1.1
   ```

### 3. Verify NetworkManager is Working
Before running the install script, ensure NetworkManager is the active manager and Wi-Fi is stable:

```bash
nmcli device status
```

Expected output:
```
NAME      TYPE      STATE
wlan0     wifi      connected     # must say "connected", not "unavailable"
eth0      ethernet  unavailable
lo        loopback  unmanaged
```

**If wlan0 shows "unavailable"**, run:
```bash
sudo systemctl restart NetworkManager
sleep 2
nmcli device status
```

Still unavailable? See troubleshooting section below.

## Installation

### 1. Download/Pull Latest Code
```bash
# If you're using git:
git clone https://github.com/YOUR_USERNAME/led_wall_bike_lights.git
cd led_wall_bike_lights

# Or copy files via SCP:
scp -r src/ config.yaml install.sh pi@bikelights:~/led_wall_bike_lights/
ssh pi@bikelights
cd led_wall_bike_lights
```

### 2. Run Installation Script
```bash
# The script must run with sudo
sudo bash install.sh
```

The script will:
1. Update system packages
2. Install Python 3, pip, required libraries
3. Fix NetworkManager conflicts (disable old dhcpcd/networking)
4. Create `/opt/led_bike_lights` with Python venv
5. Install systemd service unit
6. Set GPIO permissions for the `pi` user
7. Configure Wi-Fi regulatory domain

**Expected output**: All 8 steps complete with "Installation Complete" message.

### 3. Verify Installation
```bash
# Check service is enabled
sudo systemctl status led-bike-lights.service

# Check venv and dependencies
/opt/led_bike_lights/venv/bin/pip list

# Verify config.yaml is in place
cat /opt/led_bike_lights/config.yaml
```

### 4. Deploy Your Application Code
Copy your main application file to the installation directory:

```bash
# From your dev machine:
scp src/app.py pi@bikelights:/opt/led_bike_lights/

# Or on the Pi:
sudo cp ~/led_wall_bike_lights/src/app.py /opt/led_bike_lights/
sudo chown pi:pi /opt/led_bike_lights/app.py
```

### 5. Start the Service
```bash
# Start the service immediately
sudo systemctl start led-bike-lights.service

# Check status
sudo systemctl status led-bike-lights.service

# View logs in real-time
journalctl -u led-bike-lights.service -f
```

Press Ctrl+C to stop following logs.

### 6. Verify LEDs Light Up
Monitor the log output for startup messages. If your `app.py` is correctly implemented, the LEDs should start in the configured startup mode (see `config.yaml`).

## Post-Installation Verification

```bash
# Test Wi-Fi persistence (reboot and verify reconnect)
sudo reboot
# Wait 2 min, then SSH again
ssh pi@bikelights
ip route
ping 1.1.1.1

# Service auto-start test
sudo systemctl is-enabled led-bike-lights.service  # should print "enabled"

# Log from boot
sudo journalctl -u led-bike-lights.service -n 20
```

## Troubleshooting

### Issue: "wlan0 unavailable" / "Scanning not allowed while unavailable"

This means NetworkManager isn't controlling Wi-Fi. Run:

```bash
# Verify NetworkManager is running
sudo systemctl status NetworkManager

# Force interface up
sudo ip link set wlan0 up
sudo nmcli radio wifi on

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Test scan
sudo nmcli dev wifi rescan
sudo nmcli dev wifi list
```

If still unavailable, check if legacy networking is interfering:
```bash
sudo systemctl status dhcpcd.service
sudo systemctl status networking.service
```

Both should show `inactive`. If active, stop them:
```bash
sudo systemctl disable dhcpcd.service networking.service
sudo systemctl stop dhcpcd.service networking.service
sudo systemctl restart NetworkManager
```

If Wi-Fi still stuck, reload the driver:
```bash
sudo modprobe -r brcmfmac
sudo modprobe brcmfmac
sudo ip link set wlan0 up
nmcli device status
```

### Issue: Service fails to start (journalctl shows errors)

Check for Python import or syntax errors:
```bash
/opt/led_bike_lights/venv/bin/python3 -m py_compile /opt/led_bike_lights/app.py
```

Check if dependencies are missing:
```bash
/opt/led_bike_lights/venv/bin/pip list | grep -E "pyyaml|flask|bleak|RPi|neopixel"
```

Missing package? Install it:
```bash
/opt/led_bike_lights/venv/bin/pip install <package_name>
```

### Issue: GPIO permission denied

Ensure `pi` user is in GPIO groups:
```bash
groups pi  # should include `gpio`, `spi`, `i2c`

# If not, add them:
sudo usermod -aG gpio,spi,i2c pi

# Then log out and SSH back in
```

### Issue: LED strip doesn't light up

1. Check GPIO pin in `config.yaml` matches your wiring
2. Verify power to LED strip (separate PSU for long runs)
3. Check data line has 330-470 Ω resistor and common ground to Pi
4. Test with a minimal script:
   ```bash
   /opt/led_bike_lights/venv/bin/python3 -c \
     "import board; import neopixel; \
      pixels = neopixel.NeoPixel(board.D21, 60, brightness=0.1); \
      pixels[0] = (255, 0, 0); print('Red LED set')"
   ```

## Rolling Back / Uninstalling

To cleanly remove:
```bash
sudo systemctl stop led-bike-lights.service
sudo systemctl disable led-bike-lights.service
sudo rm /etc/systemd/system/led-bike-lights.service
sudo systemctl daemon-reload
sudo rm -rf /opt/led_bike_lights
```

## Next Steps

Once installation and service are running:
1. **Configure lighting**: Edit `/opt/led_bike_lights/config.yaml` and restart service
2. **Implement modes**: Expand `app.py` with breathing, rainbow, and other effects
3. **Button control**: Implement GPIO button interrupt handlers
4. **AP setup mode**: Add Wi-Fi onboarding web server
5. **KICKR integration**: Add Bluetooth trainer power reading

See [docs/design.md](../docs/design.md) for architecture details.
