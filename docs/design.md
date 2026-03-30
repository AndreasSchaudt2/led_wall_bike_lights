# LED Bike Wall Installation - Technical Design

## 1. System Overview
The system is an event-driven controller running on Raspberry Pi Zero 2 WH.

High-level functions:
- Render LED effects in a real-time loop.
- Read two GPIO buttons and emit user actions.
- Manage networking state (normal client mode vs AP setup mode).
- Serve a lightweight local web UI for Wi-Fi onboarding and basic control.
- Load and validate YAML configuration.
- (Future) Read BLE power from Wahoo KICKR Core and map to LED zones.

## 2. Architecture
Suggested runtime modules:
- `config_manager`: parse/validate `config.yaml`, expose typed config.
- `led_engine`: hardware abstraction + effect renderer.
- `mode_controller`: active mode state and transitions.
- `button_service`: GPIO interrupts/polling, debounce, short/long press events.
- `wifi_service`: AP mode orchestration + credential apply.
- `web_service`: setup pages and simple API endpoints.
- `kickr_service` (future): BLE scan/connect/read power and publish values.
- `main`: startup orchestration and supervisor loop.

Data/event flow:
1. `main` loads config.
2. `led_engine` starts with startup mode.
3. `button_service` emits events -> `mode_controller` updates mode.
4. `wifi_service` decides STA/AP mode and informs `web_service`.
5. `kickr_service` (if enabled + mode active) publishes power -> mapped to color.

## 3. State Machine
Top-level runtime states:
- `BOOT`
- `NORMAL`
- `AP_SETUP`
- `ERROR_FALLBACK`

Transitions:
- `BOOT -> NORMAL` when config and core services init successfully.
- `BOOT -> AP_SETUP` when Wi-Fi credentials missing/invalid (policy-based).
- `NORMAL -> AP_SETUP` on Button 2 long press.
- `AP_SETUP -> NORMAL` after credentials saved and STA connection succeeds.
- `ANY -> ERROR_FALLBACK` on unrecoverable failures.

Mode sub-state in `NORMAL`:
- `off`, `static`, `breathing`, `rainbow`, `kickr`

## 4. Button Behavior Design
Two inputs with pull-up logic recommended (active low).

Event interpretation:
- Debounce window: 30-60 ms.
- Press duration < `long_press_ms`: short press.
- Press duration >= `long_press_ms`: long press.

Proposed mapping:
- BTN1 short: next LED mode.
- BTN1 long: optional brightness step or previous mode.
- BTN2 short: reserved/no-op (v1).
- BTN2 long: enter AP setup mode.

## 5. Wi-Fi Setup (AP/Host Mode)
Implementation approach:
- Use NetworkManager + `nmcli` (or hostapd/dnsmasq if preferred).
- In AP mode, advertise `wifi.ap_ssid` from config.
- Run local web server (e.g., Flask/FastAPI) bound to AP interface.
- Web form posts target SSID/password.
- Validate input, persist config, attempt STA connection.
- On success, disable AP mode and continue normal runtime.

Security considerations:
- Mask password in UI.
- CSRF not critical in isolated AP mode, but still recommended if practical.
- Restrict setup UI to local interface.

## 6. LED Rendering Design
Core loop:
- Frame interval fixed (e.g., 20-50 FPS depending on mode).
- Each mode implements `render(dt, state) -> pixel buffer`.
- Push frame to LED driver.

Mode specifics:
- `static`: constant RGB.
- `breathing`: sinusoidal intensity scaling over cycle.
- `rainbow`: hue offset increments with speed factor.
- `kickr`: color from trainer zone with optional smoothing.

Power safety:
- Apply global brightness cap.
- Optionally estimate current draw and clamp for PSU protection.

## 7. KICKR Core BLE Integration (Future)
Service contract:
- Discover trainer by configured name or manufacturer pattern.
- Connect using BLE client library (e.g., Bleak).
- Read Cycling Power Measurement characteristic.
- Publish instantaneous power in watts.

Zone mapping:
- Compute `pct_ftp = power / ftp * 100`.
- Select first zone where `pct_ftp <= pct_ftp_max`.
- Set target color to zone color.
- Smooth transitions (linear interpolation + min update interval).

Failure behavior:
- On disconnect: retry with backoff.
- After timeout, set fallback LED mode/color and log warning.

## 8. Configuration Schema (Proposed)
This extends your existing `config.yaml` style.

- `led.pin`: BCM GPIO data pin.
- `led.count`: number of pixels.
- `led.brightness`: 0-255 cap.
- `buttons.btn1_pin`, `buttons.btn2_pin`, `buttons.long_press_ms`.
- `wifi.ssid`, `wifi.password`, `wifi.ap_ssid`.
- `modes.startup_mode`, per-mode settings.
- `kickr.enabled`, `kickr.ftp`, `kickr.device_name`, `kickr.zones[]`.

Validation rules:
- GPIO pins must be unique and valid.
- `led.count > 0`, brightness within range.
- `startup_mode` must exist in enabled modes.
- `kickr.ftp > 0` when kickr enabled.
- `zones` sorted by ascending `pct_ftp_max`.

## 9. File/Project Layout Suggestion
Suggested source tree:

```text
src/
  app.py
  config_manager.py
  led/
    engine.py
    modes.py
  input/
    buttons.py
  network/
    wifi.py
  web/
    server.py
    templates/
      setup.html
  integrations/
    kickr.py
```

## 10. Systemd Design
Service goals:
- Start after network stack init where needed.
- Restart on failure.
- Log to journal.

Example service behavior:
- `Restart=on-failure`
- `RestartSec=2`
- `WantedBy=multi-user.target`

## 11. Testing Strategy
Minimum tests:
- Unit tests for config validation and zone mapping.
- Button event timing/debounce tests (simulated).
- Mode renderer tests for bounds and frame generation.
- Manual integration test: AP setup flow from phone.
- Manual BLE test with KICKR power simulation or live trainer.

## 12. Deployment Steps
1. Flash Raspberry Pi OS Lite.
2. Install dependencies and enable service.
3. Wire LED + buttons with shared ground.
4. Copy config and tune LED count/brightness.
5. Boot and validate button + AP setup behavior.
6. Enable KICKR mode once BLE integration is implemented.

## 13. Risks and Mitigations
- GPIO noise/button bounce: robust debounce + pull resistors.
- LED power instability: dedicated PSU + capacitor + wiring gauge.
- BLE instability: reconnect backoff and fallback mode.
- Config corruption: keep startup defaults and backup last-known-good.
