# Installation Guide

## Goal
Set up LED Bike Wall Lights on a fresh Raspberry Pi OS image with stable Wi-Fi provisioning via `wifi-connect`.

## Prerequisites
- Raspberry Pi Zero 2 WH
- Raspberry Pi OS Lite (recommended)
- Internet connection during install
- Repository cloned on the Pi

## 1) Prepare OS
1. Flash Raspberry Pi OS Lite.
2. Boot the Pi.
3. Connect to network (Ethernet, temporary hotspot, or preconfigured Wi-Fi).
4. SSH into the Pi.

## 2) Clone Project
```bash
git clone https://github.com/AndreasSchaudt2/led_wall_bike_lights
cd led_wall_bike_lights
```

## 3) Run Installer
```bash
sudo bash install.sh
```

Installer behavior:
1. Installs system dependencies.
2. Enables NetworkManager.
3. Installs `wifi-connect`.
4. Deploys app to `/opt/led_bike_lights`.
5. Installs and enables `led-bike-lights.service`.

## 4) Verify Service
```bash
sudo systemctl status led-bike-lights.service --no-pager
sudo journalctl -u led-bike-lights.service -n 120 --no-pager
```

## 5) Provision Wi-Fi (Phone/Laptop)
1. Long-press button 2 on the device.
2. Connect phone/laptop to provisioning SSID shown by `wifi-connect`.
3. Complete captive portal flow to enter home Wi-Fi credentials.

Check provisioning service if needed:
```bash
sudo systemctl status wifi-connect.service --no-pager
sudo journalctl -u wifi-connect.service -n 120 --no-pager
```

## 6) Deploy Future Code Updates
After making code changes and pulling updates:
```bash
cd ~/led_wall_bike_lights
git pull
sudo bash start-service.sh
```

This safely redeploys code and restarts the service.

## 7) Useful Operations
```bash
# main service logs
sudo journalctl -u led-bike-lights.service -f

# restart main service
sudo systemctl restart led-bike-lights.service

# check Wi-Fi devices
nmcli device status

# check saved connections
nmcli con show
```

## Troubleshooting
### `nmcli` cannot find network
- Ensure hotspot/AP mode is down.
- Confirm router has 2.4 GHz enabled (Pi Zero 2 WH needs 2.4 GHz).

### Service runs but button 2 does nothing
```bash
sudo journalctl -u led-bike-lights.service -n 120 --no-pager
sudo systemctl status wifi-connect.service --no-pager
```

### Re-run full installation on same device
```bash
cd ~/led_wall_bike_lights
git pull
sudo bash install.sh
```
