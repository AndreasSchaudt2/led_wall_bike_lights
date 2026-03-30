# LED Bike Wall Installation - Product Requirements

## 1. Goal
Create a Raspberry Pi Zero 2 WH based LED neon wall installation that highlights a road bike on the wall. The system must be controllable with two physical buttons, support Wi-Fi onboarding through host/AP mode, and be configurable from a YAML config file. A future mode should map live cycling power from a Wahoo KICKR Core (BLE) to LED colors.

## 2. Scope
In scope:
- Addressable 2 m silicone-encased LED strip ("neon" effect)
- Raspberry Pi Zero 2 WH as controller
- Two wired push buttons (3-wire harness per button)
- Config-driven behavior in `config.yaml`
- Local web setup page in AP mode for Wi-Fi credentials
- Multiple LED effects/modes
- Future BLE trainer integration (Wahoo KICKR Core power -> color)

Out of scope (initial release):
- Cloud services
- Mobile app (browser-based setup only)
- Multi-room synchronization
- Voice assistant integration

## 3. Users and Primary Use Cases
Users:
- Primary: bike owner setting mood/ambient wall lighting
- Secondary: indoor training rider using trainer power-reactive lighting

Primary use cases:
1. Power on and show preferred startup light mode.
2. Tap button to cycle through modes.
3. Hold button to enter Wi-Fi setup mode (AP/host mode).
4. Connect phone/laptop to device AP and configure home Wi-Fi.
5. System reconnects to home Wi-Fi and resumes normal operation.
6. (Future) In KICKR mode, LEDs change color by live power zone.

## 4. Functional Requirements
### FR-1 LED Control
- Support configurable LED count, GPIO pin, and brightness.
- Support minimum modes:
  - `off`
  - `static`
  - `breathing`
  - `rainbow`
  - `kickr` (future/feature-gated)
- Startup mode is configurable.
- Mode transitions must be smooth (no visible flicker bursts).

### FR-2 Two-Button Input
- Button 1 short press: next mode.
- Button 1 long press (optional): previous mode or brightness cycle (configurable extension).
- Button 2 short press: reserved (optional action; no-op allowed for v1).
- Button 2 long press: force AP setup mode.
- Debounce handling required.
- Long press threshold configurable (`long_press_ms`).

### FR-3 Wi-Fi Provisioning
- If Wi-Fi credentials are missing/invalid, device enters AP setup mode.
- Device advertises setup SSID (from config).
- Setup page allows entering SSID/password.
- Credentials are saved to `config.yaml` or secure runtime config store.
- On save, networking restarts and device attempts STA mode connection.

### FR-4 Config-Driven Behavior
- All key runtime parameters are configured by YAML:
  - LED hardware parameters
  - Button pins/timings
  - Wi-Fi AP details
  - Mode settings
  - KICKR power zones and FTP
- Invalid config must fail gracefully with safe defaults and error logs.

### FR-5 KICKR Core Integration (Future)
- BLE scan/discovery for trainer (name filter optional).
- Subscribe/read cycling power characteristic.
- Convert power (W) to FTP percentage and map to configured zones.
- Update LED color with smoothing/rate limiting to avoid jitter.
- If BLE drops, fallback to a safe mode (e.g., static amber).

### FR-6 Local Web UI
- Setup-first UI for Wi-Fi onboarding.
- Optional admin page for mode preview, brightness, and status.
- UI must be lightweight and usable from phone browser.

### FR-7 Reliability & Recovery
- Service auto-start on boot (systemd).
- Auto-restart on crash.
- Boot-time fallback mode if initialization fails.
- Logs available via systemd journal.

## 5. Non-Functional Requirements
- Boot-to-light target: <= 10 seconds after power-on.
- UI response for mode changes: <= 150 ms perceived latency.
- CPU footprint on Pi Zero 2 should remain low under static/breathing/rainbow modes.
- KICKR update loop target: 1-2 Hz LED updates (smoothed).
- Brightness limits to protect PSU and LED strip from overcurrent.
- Safe operation with clear wiring and GPIO level handling.

## 6. Hardware/Interface Requirements
- Raspberry Pi Zero 2 WH.
- Addressable LED strip compatible with chosen software driver (e.g., WS281x family).
- External power supply sized for LED strip current at max brightness.
- Common ground between PSU, LED strip, and Pi.
- Recommended signal integrity components (implementation detail):
  - 330-470 ohm series resistor on data line
  - large electrolytic capacitor across LED power rails
  - optional level shifting if required by strip tolerance

## 7. Safety and Constraints
- Do not power full LED strip current from Pi 5V rail.
- Respect GPIO current limits.
- Enclosure/wiring should prevent shorts and exposed conductors.
- Use conservative default brightness for thermal and power safety.

## 8. Configuration Contract (High-Level)
Required sections:
- `led`
- `buttons`
- `wifi`
- `modes`

Optional/future sections:
- `kickr`
- `web`
- `logging`

## 9. Acceptance Criteria
1. Device boots and displays startup mode from config.
2. Button 1 short press cycles all enabled modes in order.
3. Button 2 long press enters AP mode within configured hold time.
4. User can configure Wi-Fi from phone browser and reconnect successfully.
5. On reboot, stored configuration persists and service resumes.
6. Invalid mode config does not crash service; fallback mode appears.
7. (Future) In KICKR mode, power zone transitions produce corresponding configured colors.

## 10. Milestones
M1 - Core lighting engine + config load + button mode cycling.
M2 - AP setup mode + web onboarding + persistent Wi-Fi credentials.
M3 - Service hardening (systemd, logging, recovery).
M4 - KICKR BLE integration + power-zone color mapping.
M5 - UX polish and field testing.
