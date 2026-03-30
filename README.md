# LED Bike Wall Lights

Raspberry Pi Zero 2 WH based LED neon wall installation for highlighting a road bike.

## Features

- 🎨 Addressable 2m silicone-encased LED strip with multiple effects
- 🔘 Two-button GPIO control (mode switching, AP setup mode)
- 📱 Web-based Wi-Fi onboarding (AP/host setup mode)
- ⚙️ YAML config-driven behavior
- 🚴 Future Wahoo KICKR Core BLE power-zone integration
- 🔄 Auto-start systemd service with restart on crash

## Installation

### Quick Start
1. Flash [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/) to SD card
2. Configure Wi-Fi during imaging
3. SSH into Pi: `ssh pi@<IP_OR_HOSTNAME>`
4. Clone or copy this repository
5. Run: `sudo bash install.sh`
6. Start service: `sudo systemctl start led-bike-lights.service`

For detailed instructions, see [INSTALL.md](INSTALL.md).

### Requirements

**Hardware:**
- Raspberry Pi Zero 2 WH
- Addressable WS281x LED strip (2m+)
- External PSU (5V, rated for LED strip power draw)
- Two push buttons (GPIO wired)
- 330-470Ω resistor on LED data line
- Large electrolytic capacitor across LED power rails

**Software:**
- Raspberry Pi OS Lite (latest)
- Python 3.9+
- Network access during installation

## Configuration

Edit `config.yaml` to customize:

```yaml
led:
  pin: 21                    # GPIO data pin
  count: 60                  # Number of LEDs
  brightness: 100           # 0-255

buttons:
  btn1_pin: 20              # GPIO for mode button
  btn2_pin: 22              # GPIO for setup button
  long_press_ms: 3000       # Long-press threshold

modes:
  startup_mode: "static"    # Default mode on boot
  static:
    color: [255, 80, 0]     # RGB orange
  breathing:
    color: [255, 80, 0]
    speed: 1.5              # Seconds per cycle
  rainbow:
    speed: 0.05             # Seconds per step

kickr:
  enabled: false            # Enable KICKR trainer integration
  ftp: 250                  # Your FTP in watts
  zones:                    # Power zones (color by FTP %)
    - name: Z1_Recovery
      pct_ftp_max: 55
      color: [0, 0, 255]    # Blue
```

See [config.yaml](config.yaml) for full reference.

## Usage

### Normal Operation
1. Device boots in ~60 seconds
2. LED strip displays startup mode (e.g., static orange)
3. Button 1 short press: cycle through modes
4. Button 1 long press: (reserved for future expansion)
5. Button 2 short press: (reserved)
6. Button 2 long press (3s): enter Wi-Fi setup (AP) mode

### Wi-Fi Setup (AP Mode)
1. Hold Button 2 for 3+ seconds
2. Device enters AP mode, advertises `BikeLights-Setup` SSID
3. From phone/laptop, connect to `BikeLights-Setup`
4. Open browser to `http://192.168.4.1:5000`
5. Enter home Wi-Fi credentials
6. Device saves credentials and reconnects
7. Setup UI can be accessed on any network for control/monitoring

### Service Management

```bash
# Start service
sudo systemctl start led-bike-lights.service

# Enable auto-start on boot
sudo systemctl enable led-bike-lights.service

# View status
sudo systemctl status led-bike-lights.service

# View logs
journalctl -u led-bike-lights.service -f

# Stop service
sudo systemctl stop led-bike-lights.service
```

## Architecture

Modular design with clear separation of concerns:

```
src/
  app.py                  # Main entrypoint & orchestration
  config_manager.py       # YAML config loading & validation
  led/
    engine.py            # LED hardware abstraction
    modes.py             # Effect renderers (static, breathing, etc)
  input/
    buttons.py           # GPIO button handling & debounce  
  network/
    wifi.py              # NetworkManager Wi-Fi control
  web/
    server.py            # Flask setup UI
    templates/
      setup.html         # Web UI for config
  integrations/
    kickr.py             # Wahoo KICKR BLE trainer
```

See [docs/design.md](docs/design.md) for full architecture details.

## Troubleshooting

### LEDs don't light up
- Check GPIO pin matches config.yaml
- Verify power to LED strip (separate PSU)
- Confirm data line has resistor and common ground to Pi
- Check for error logs: `journalctl -u led-bike-lights.service`

### Wi-Fi connection fails
- Boot with fresh Raspberry Pi OS (run `install.sh` to fix NetworkManager)
- Check SSID/password in config.yaml
- Verify Pi can reach gateway: `ping 1.1.1.1`
- See [INSTALL.md](INSTALL.md#troubleshooting) for detailed Wi-Fi fixes

### Service won't start
- Check Python syntax: `/opt/led_bike_lights/venv/bin/python3 -m py_compile src/app.py`
- Verify dependencies: `/opt/led_bike_lights/venv/bin/pip list`
- Check permissions: `ls -la /opt/led_bike_lights`

## Development

### Local testing
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 src/app.py
```

### Adding new modes
1. Create mode class in `src/led/modes.py` extending `Mode`
2. Implement `render(dt)` method
3. Register in `create_mode()` factory
4. Add config section to `config.yaml`
5. Test with button 1

### Adding KICKR power zones
Edit `config.yaml` kickr section with zones:
```yaml
kickr:
  zones:
    - name: MyZone
      pct_ftp_max: 100
      color: [R, G, B]
```

## Project Timeline

- **M1**: Core lighting + config + button cycling ✓
- **M2**: AP setup + web UI + Wi-Fi provisioning
- **M3**: Service hardening & systemd integration
- **M4**: KICKR BLE integration (power-zone colors)
- **M5**: UX polish & field testing

## License

[Choose your license]

## Support

Issues & feature requests: [GitHub Issues]

For detailed requirements, see [docs/requirements.md](docs/requirements.md).
