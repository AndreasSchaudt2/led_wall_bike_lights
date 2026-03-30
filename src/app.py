#!/usr/bin/env python3
"""
LED Bike Wall Lights - Main Application
Orchestrates LED engine, button input, Wi-Fi, and future trainer integration.
"""

import os
import sys
import logging
import logging.handlers
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from led.engine import LEDEngine
from led.modes import create_mode
from input.buttons import ButtonService, ButtonEvent
from network.wifi import WiFiService
from web.server import WebServer

# Setup logging to file and console
log_dir = Path("/var/log/led_bike_lights")
log_dir.mkdir(exist_ok=True, parents=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console.setFormatter(console_format)
logger.addHandler(console)

# File handler
try:
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=1024*1024,
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not set up file logging: {e}")


class ModeController:
    """Manage LED modes and transitions."""
    
    def __init__(self, config, led_engine):
        """
        Initialize mode controller.
        
        Args:
            config: ConfigManager instance
            led_engine: LEDEngine instance
        """
        self.config = config
        self.led_engine = led_engine
        self.current_mode = None
        self.current_mode_obj = None
        self.animation_thread = None
        self.stop_animation = False
        
        # Get list of available modes
        modes_config = config.get('modes', {})
        self.available_modes = [m for m in modes_config.keys() if m != 'startup_mode']
        self.mode_index = 0
        
        logger.info(f"Available modes: {self.available_modes}")
    
    def startup(self):
        """Activate startup mode from config."""
        startup_mode = self.config.get('modes', {}).get('startup_mode', 'static')
        self.set_mode(startup_mode)
    
    def set_mode(self, mode_name):
        """
        Switch to a new mode.
        
        Args:
            mode_name: Mode name ('static', 'breathing', 'rainbow', 'kickr', 'off')
        """
        # Validate mode exists
        if mode_name not in self.available_modes and mode_name != 'off':
            logger.warning(f"Mode '{mode_name}' not available, using 'static'")
            mode_name = 'static'
        
        # Stop current animation
        self.stop_animation = True
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1)
        
        # Create new mode
        mode_config = self.config.get('modes', {}).get(mode_name, {})
        self.current_mode_obj = create_mode(mode_name, self.led_engine, mode_config)
        self.current_mode = mode_name
        
        # Start animation thread
        self.stop_animation = False
        self.animation_thread = threading.Thread(
            target=self._animate,
            daemon=True,
            name=f"Animation-{mode_name}"
        )
        self.animation_thread.start()
        
        logger.info(f"Mode changed to: {mode_name}")
    
    def _animate(self):
        """Animation render loop."""
        last_frame = time.time()
        
        while not self.stop_animation:
            try:
                now = time.time()
                dt = now - last_frame
                self.current_mode_obj.render(dt)
                last_frame = now
                time.sleep(0.02)  # ~50 FPS
            except Exception as e:
                logger.error(f"Animation error: {e}")
                break
    
    def next_mode(self):
        """Switch to next available mode."""
        self.mode_index = (self.mode_index + 1) % len(self.available_modes)
        next_mode = self.available_modes[self.mode_index]
        self.set_mode(next_mode)
    
    def previous_mode(self):
        """Switch to previous available mode."""
        self.mode_index = (self.mode_index - 1) % len(self.available_modes)
        prev_mode = self.available_modes[self.mode_index]
        self.set_mode(prev_mode)
    
    def shutdown(self):
        """Clean up animation."""
        self.stop_animation = True
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=2)


class Application:
    """Main application controller."""
    
    def __init__(self):
        """Initialize application."""
        logger.info("=" * 60)
        logger.info("LED Bike Wall Lights - Starting")
        logger.info("=" * 60)
        
        self.config = None
        self.led_engine = None
        self.mode_controller = None
        self.button_service = None
        self.wifi_service = None
        self.web_server = None
        
        try:
            self._initialize()
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            sys.exit(1)
    
    def _initialize(self):
        """Initialize all components."""
        # Load configuration
        config_path = Path("/opt/led_bike_lights/config.yaml")
        self.config = ConfigManager(str(config_path))
        logger.info("Configuration loaded and validated")
        
        # Initialize LED engine
        led_cfg = self.config.get('led', {})
        self.led_engine = LEDEngine(
            pin=led_cfg.get('pin', 21),
            count=led_cfg.get('count', 60),
            brightness=led_cfg.get('brightness', 100)
        )
        logger.info("LED engine initialized")
        
        # Initialize mode controller
        self.mode_controller = ModeController(self.config, self.led_engine)
        
        # Initialize button service
        btn_cfg = self.config.get('buttons', {})
        self.button_service = ButtonService(
            btn1_pin=btn_cfg.get('btn1_pin', 20),
            btn2_pin=btn_cfg.get('btn2_pin', 22),
            long_press_ms=btn_cfg.get('long_press_ms', 3000)
        )
        self._setup_button_callbacks()
        logger.info("Button service initialized")
        
        # Initialize Wi-Fi service
        wifi_cfg = self.config.get('wifi', {})
        self.wifi_service = WiFiService(
            ap_ssid=wifi_cfg.get('ap_ssid', 'BikeLights-Setup')
        )
        logger.info("Wi-Fi service initialized")
        
        # Initialize web server
        self.web_server = WebServer(self.config, self.wifi_service)
        logger.info("Web server initialized")
    
    def _setup_button_callbacks(self):
        """Register button event handlers."""
        self.button_service.on_action('btn1_short', self.on_btn1_short)
        self.button_service.on_action('btn1_long', self.on_btn1_long)
        self.button_service.on_action('btn2_short', self.on_btn2_short)
        self.button_service.on_action('btn2_long', self.on_btn2_long)
    
    def on_btn1_short(self):
        """Button 1 short press: next mode."""
        logger.info("Button 1 short press - next mode")
        self.mode_controller.next_mode()
    
    def on_btn1_long(self):
        """Button 1 long press: previous mode (or other action)."""
        logger.info("Button 1 long press")
        # TODO: implement reserved action
    
    def on_btn2_short(self):
        """Button 2 short press: reserved."""
        logger.info("Button 2 short press")
        # TODO: implement reserved action
    
    def on_btn2_long(self):
        """Button 2 long press: enter AP setup mode."""
        logger.info("Button 2 long press - entering AP mode")
        # TODO: implement AP mode entry
    
    def run(self):
        """Main event loop."""
        try:
            logger.info("Entering main loop")
            self.mode_controller.startup()
            
            # Main loop
            while True:
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Runtime error: {e}", exc_info=True)
            sys.exit(1)
    
    def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down...")
        
        try:
            if self.mode_controller:
                self.mode_controller.shutdown()
            
            if self.button_service:
                self.button_service.cleanup()
            
            if self.led_engine:
                self.led_engine.shutdown()
            
            logger.info("Shutdown complete")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == '__main__':
    app = Application()
    try:
        app.run()
    finally:
        app.shutdown()
