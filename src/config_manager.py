"""
Configuration manager for LED Bike Wall Lights.
Handles loading, validating, and accessing YAML configuration.
"""

import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Load and validate YAML configuration.
    Provides typed access to all config parameters with sensible defaults.
    """
    
    # Default configuration fallbacks
    DEFAULTS = {
        'led': {
            'pin': 21,
            'count': 60,
            'brightness': 100,
        },
        'buttons': {
            'btn1_pin': 20,
            'btn2_pin': 22,
            'long_press_ms': 3000,
        },
        'wifi': {
            'ssid': '',
            'password': '',
            'ap_ssid': 'BikeLights-Setup',
        },
        'modes': {
            'startup_mode': 'static',
            'static': {'color': [255, 80, 0]},
            'breathing': {'color': [255, 80, 0], 'speed': 1.5},
            'rainbow': {'speed': 0.05},
            'off': {},
        },
        'kickr': {
            'enabled': False,
            'ftp': 250,
            'device_name': '',
            'zones': [
                {'name': 'Z1_Recovery', 'pct_ftp_max': 55, 'color': [0, 0, 255]},
                {'name': 'Z2_Endurance', 'pct_ftp_max': 75, 'color': [0, 200, 0]},
                {'name': 'Z3_Tempo', 'pct_ftp_max': 90, 'color': [255, 255, 0]},
                {'name': 'Z4_Threshold', 'pct_ftp_max': 105, 'color': [255, 128, 0]},
                {'name': 'Z5_VO2Max', 'pct_ftp_max': 120, 'color': [255, 0, 0]},
                {'name': 'Z6_Anaerobic', 'pct_ftp_max': 999, 'color': [180, 0, 255]},
            ]
        },
    }
    
    def __init__(self, config_path: str = "/opt/led_bike_lights/config.yaml"):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load and merge YAML config with defaults.
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        # Start with defaults
        self.config = self._deep_copy_dict(self.DEFAULTS)
        
        # Load and merge user config if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                self._deep_merge(self.config, user_config)
                logger.info(f"Loaded config from {self.config_path}")
            except yaml.YAMLError as e:
                logger.error(f"YAML parse error in {self.config_path}: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                raise
        else:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
        
        self._validate()
    
    def _deep_copy_dict(self, d: Dict) -> Dict:
        """Deep copy a nested dictionary."""
        return {k: (self._deep_copy_dict(v) if isinstance(v, dict) else v) for k, v in d.items()}
    
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Merge override dict into base dict recursively."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _validate(self) -> None:
        """Validate configuration parameters."""
        # Validate LED parameters
        led = self.get('led')
        if led['pin'] < 0 or led['pin'] > 27:
            logger.warning(f"LED pin {led['pin']} out of valid GPIO range, keeping value")
        if led['count'] <= 0:
            logger.error(f"LED count must be > 0, got {led['count']}")
            led['count'] = 60
        if not (0 <= led['brightness'] <= 255):
            logger.warning(f"LED brightness {led['brightness']} out of 0-255 range, clamping")
            led['brightness'] = max(0, min(255, led['brightness']))
        
        # Validate button parameters
        buttons = self.get('buttons')
        if buttons['long_press_ms'] < 100:
            logger.warning(f"Long press threshold too low ({buttons['long_press_ms']}ms), using 500ms")
            buttons['long_press_ms'] = 500
        
        # Validate startup mode exists
        modes = self.get('modes')
        startup_mode = modes.get('startup_mode', 'static')
        valid_modes = [m for m in modes.keys() if m not in ['startup_mode']]
        if startup_mode not in valid_modes:
            logger.error(f"Startup mode '{startup_mode}' not defined, falling back to 'static'")
            modes['startup_mode'] = 'static'
        
        # Validate KICKR parameters if enabled
        kickr = self.get('kickr')
        if kickr.get('enabled'):
            ftp = kickr.get('ftp', 250)
            if ftp <= 0:
                logger.warning(f"KICKR FTP invalid ({ftp}), disabling KICKR mode")
                kickr['enabled'] = False
            zones = kickr.get('zones', [])
            if not zones:
                logger.warning("KICKR enabled but no zones defined")
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            section: Top-level config section (e.g., 'led', 'buttons')
            key: Optional key within section
            default: Default value if not found
        
        Returns:
            Config value or default
        """
        if section not in self.config:
            return default
        
        if key is None:
            return self.config[section]
        
        return self.config[section].get(key, default)
    
    def save(self, config_path: Optional[str] = None) -> None:
        """
        Save current config to YAML file.
        
        Args:
            config_path: Optional path to save to (default: original config_path)
        """
        path = Path(config_path or self.config_path)
        try:
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Config saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
