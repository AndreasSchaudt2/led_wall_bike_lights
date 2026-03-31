# LED Bike Wall Lights

Raspberry Pi Zero 2 WH based LED neon wall installation for highlighting a road bike.

## Features
- Addressable LED strip effects (static, breathing, rainbow)
- Two-button GPIO control
- Proven Wi-Fi provisioning using balena wifi-connect (captive portal)
- Config-driven runtime behavior through `config.yaml`
- Systemd service with restart policy
- Future Wahoo KICKR Core BLE power-zone integration

## Install
### Quick Start
1. Flash Raspberry Pi OS Lite.
2. Boot the Pi and ensure internet connectivity.
3. Clone this repository on the Pi:
```bash
git clone https://github.com/AndreasSchaudt2/led_wall_bike_lights
cd led_wall_bike_lights
```
4. Run:
```bash
sudo bash install.sh
```

The installer will:
1. Install dependencies and NetworkManager.
2. Install `wifi-connect` provisioning service.
3. Copy app files to `/opt/led_bike_lights`.
4. Install/enable `led-bike-lights.service`.

## Deploy Updates
After pulling new code, run one command:
```bash
sudo bash start-service.sh
```

This script:
1. Copies latest `src/` into `/opt/led_bike_lights`.
2. Preserves existing `/opt/led_bike_lights/config.yaml`.
3. Updates systemd unit from `systemd/led-bike-lights.service`.
4. Reloads and restarts the service.

## Configuration
Main runtime config file:
- `/opt/led_bike_lights/config.yaml`

Template source in repo:
- `config.yaml`

## Runtime Controls
- Button 1 short press: next light mode.
- Button 2 long press: start `wifi-connect` provisioning mode.

## Wi-Fi Provisioning Flow
1. Hold button 2.
2. Device starts `wifi-connect` portal.
3. Connect phone/laptop to provisioning SSID.
4. Captive portal opens automatically.
5. Choose home Wi-Fi + enter password.
6. Device reconnects to home Wi-Fi.

## Service Commands
```bash
sudo systemctl status led-bike-lights.service --no-pager
sudo systemctl restart led-bike-lights.service
sudo journalctl -u led-bike-lights.service -f
```

## Troubleshooting
### wifi-connect not starting
```bash
sudo systemctl status wifi-connect.service --no-pager
sudo journalctl -u wifi-connect.service -n 120 --no-pager
```

### Main service not starting
```bash
sudo systemctl status led-bike-lights.service --no-pager
sudo journalctl -u led-bike-lights.service -n 120 --no-pager
```

### NetworkManager issues
```bash
sudo systemctl status NetworkManager --no-pager
nmcli device status
```

## Project Layout
```text
src/
  app.py
  config_manager.py
  led/
  input/
  network/
  web/
  integrations/
systemd/
  led-bike-lights.service
install.sh
start-service.sh
config.yaml
```

For detailed product/design notes see:
- `docs/requirements.md`
- `docs/design.md`
