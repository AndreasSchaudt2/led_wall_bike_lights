"""
LED effect modes (static, breathing, rainbow, etc).
Each mode implements a render() method for animation.
"""

import logging
import math
import time
from abc import ABC, abstractmethod
from typing import List, Tuple

logger = logging.getLogger(__name__)

RGB = Tuple[int, int, int]


class Mode(ABC):
    """Base class for LED modes."""
    
    def __init__(self, led_engine, color: RGB = (255, 0, 0), **kwargs):
        """
        Initialize mode.
        
        Args:
            led_engine: LEDEngine instance
            color: RGB color tuple
            **kwargs: Mode-specific parameters
        """
        self.led_engine = led_engine
        self.color = color
        self.start_time = time.time()
        self.frame_count = 0
    
    @abstractmethod
    def render(self, dt: float) -> None:
        """
        Render one animation frame.
        
        Args:
            dt: Delta time since last frame (seconds)
        """
        pass
    
    def reset(self) -> None:
        """Reset animation state."""
        self.start_time = time.time()
        self.frame_count = 0


class OffMode(Mode):
    """All LEDs off."""
    
    def render(self, dt: float) -> None:
        """Turn off all LEDs."""
        self.led_engine.clear()
        self.led_engine.render()
        self.frame_count += 1


class StaticMode(Mode):
    """Solid static color."""
    
    def render(self, dt: float) -> None:
        """Render static color."""
        self.led_engine.set_all(self.color)
        self.led_engine.render()
        self.frame_count += 1


class BreathingMode(Mode):
    """Pulsing/breathing effect."""
    
    def __init__(self, led_engine, color: RGB = (255, 0, 0), speed: float = 1.5, **kwargs):
        """
        Initialize breathing mode.
        
        Args:
            led_engine: LEDEngine instance
            color: RGB color tuple
            speed: Breathing cycle duration in seconds (default 1.5)
        """
        super().__init__(led_engine, color, **kwargs)
        self.speed = max(0.5, speed)  # Minimum 0.5s cycle
    
    def render(self, dt: float) -> None:
        """Render breathing pulse."""
        elapsed = time.time() - self.start_time
        
        # Sinusoidal brightness 0.0 to 1.0 to 0.0 over one cycle
        phase = (elapsed / self.speed) % 1.0
        brightness_factor = (math.sin(phase * 2 * math.pi - math.pi / 2) + 1) / 2
        
        # Modulate color by brightness
        r = int(self.color[0] * brightness_factor)
        g = int(self.color[1] * brightness_factor)
        b = int(self.color[2] * brightness_factor)
        
        self.led_engine.set_all((r, g, b))
        self.led_engine.render()
        self.frame_count += 1


class RainbowMode(Mode):
    """Rainbow hue sweep."""
    
    def __init__(self, led_engine, color: RGB = None, speed: float = 0.05, **kwargs):
        """
        Initialize rainbow mode.
        
        Args:
            led_engine: LEDEngine instance
            color: Ignored for rainbow mode
            speed: Seconds per animation step (lower = faster, default 0.05)
        """
        super().__init__(led_engine, color or (255, 0, 0), **kwargs)
        self.speed = max(0.01, speed)
    
    def render(self, dt: float) -> None:
        """Render rainbow sweep."""
        elapsed = time.time() - self.start_time
        hue_offset = (elapsed / self.speed) % 360
        
        for i in range(self.led_engine.count):
            # Distribute hue across strip
            hue = (hue_offset + (i / self.led_engine.count) * 360) % 360
            rgb = self._hue_to_rgb(hue)
            self.led_engine.set_pixel(i, rgb)
        
        self.led_engine.render()
        self.frame_count += 1
    
    @staticmethod
    def _hue_to_rgb(hue: float) -> RGB:
        """
        Convert HSV (hue only, full sat/val) to RGB.
        
        Args:
            hue: Hue in degrees (0-360)
        
        Returns:
            RGB tuple
        """
        h = hue / 60.0
        x = int(h)
        f = h - x
        
        p = 0
        q = int(255 * (1 - 1.0 * f))
        t = int(255 * (1 - 1.0 * (1 - f)))
        v = 255
        
        if x % 6 == 0:
            return (v, t, p)
        if x % 6 == 1:
            return (q, v, p)
        if x % 6 == 2:
            return (p, v, t)
        if x % 6 == 3:
            return (p, q, v)
        if x % 6 == 4:
            return (t, p, v)
        return (v, p, q)


class KickrMode(Mode):
    """
    Power-reactive color mode for Wahoo KICKR trainer.
    Color changes based on current power zone.
    (Stub - requires BLE integration)
    """
    
    def __init__(self, led_engine, zones: List[dict] = None, **kwargs):
        """
        Initialize KICKR mode.
        
        Args:
            led_engine: LEDEngine instance
            zones: Power zone definitions
        """
        super().__init__(led_engine, **kwargs)
        self.zones = zones or []
        self.current_zone_color = (100, 100, 100)  # Gray default
    
    def set_power(self, power_watts: int) -> None:
        """
        Update color based on power zone.
        
        Args:
            power_watts: Current power output in watts
        """
        # TODO: Implement zone lookup and color smoothing
        logger.debug(f"KICKR power: {power_watts}W")
    
    def render(self, dt: float) -> None:
        """Render current zone color."""
        self.led_engine.set_all(self.current_zone_color)
        self.led_engine.render()
        self.frame_count += 1


def create_mode(mode_name: str, led_engine, config: dict) -> Mode:
    """
    Factory function to create mode instances.
    
    Args:
        mode_name: Mode name ('static', 'breathing', 'rainbow', 'kickr', 'off')
        led_engine: LEDEngine instance
        config: Mode-specific config parameters
    
    Returns:
        Mode instance
    """
    mode_name = mode_name.lower()
    
    if mode_name == 'off':
        return OffMode(led_engine)
    elif mode_name == 'static':
        color = tuple(config.get('color', [255, 80, 0]))
        return StaticMode(led_engine, color)
    elif mode_name == 'breathing':
        color = tuple(config.get('color', [255, 80, 0]))
        speed = config.get('speed', 1.5)
        return BreathingMode(led_engine, color, speed)
    elif mode_name == 'rainbow':
        speed = config.get('speed', 0.05)
        return RainbowMode(led_engine, speed=speed)
    elif mode_name == 'kickr':
        zones = config.get('zones', [])
        return KickrMode(led_engine, zones)
    else:
        logger.warning(f"Unknown mode: {mode_name}, falling back to static")
        return StaticMode(led_engine, (255, 80, 0))
