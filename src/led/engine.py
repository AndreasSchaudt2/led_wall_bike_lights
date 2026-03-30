"""
LED hardware abstraction layer.
Provides interface to addressable LED strips (NeoPixel/WS281x).
"""

import logging
from typing import List, Tuple, Optional
import time

logger = logging.getLogger(__name__)

# Type alias for RGB color tuples
RGB = Tuple[int, int, int]


class LEDEngine:
    """
    Hardware abstraction for addressable LED strips.
    Implements driver initialization and frame rendering.
    """
    
    def __init__(self, pin: int, count: int, brightness: int = 100):
        """
        Initialize LED engine.
        
        Args:
            pin: GPIO pin number (BCM)
            count: Number of LEDs in strip
            brightness: Global brightness 0-255 (default 100)
        """
        self.pin = pin
        self.count = count
        self.brightness = max(0, min(255, brightness))
        self.frame_buffer: List[RGB] = [(0, 0, 0) for _ in range(count)]
        self.pixels = None
        self.last_render_time = 0
        self.min_frame_interval = 0.02  # ~50 FPS max
        
        logger.info(f"LED Engine init: pin={pin}, count={count}, brightness={brightness}")
        self._initialize_driver()
    
    def _initialize_driver(self) -> None:
        """
        Initialize the LED driver.
        Attempts to load neopixel/WS281x driver (stub for portability).
        """
        try:
            import board
            import neopixel
            
            # Map BCM pin to board pin (this is a simplified mapping)
            # For Pi Zero 2, pin 21 typically maps to GPIO21
            pin_obj = getattr(board, f'D{self.pin}', None)
            if pin_obj is None:
                logger.warning(f"Board pin D{self.pin} not found, using GPIO object")
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.OUT)
            
            self.pixels = neopixel.NeoPixel(
                pin_obj or self.pin,
                self.count,
                brightness=self.brightness / 255.0,
                auto_write=True
            )
            logger.info("NeoPixel driver initialized successfully")
        except ImportError as e:
            logger.warning(f"NeoPixel driver not available: {e}. Using mock mode.")
            self.pixels = None
        except Exception as e:
            logger.error(f"Failed to initialize LED driver: {e}")
            self.pixels = None
    
    def set_pixel(self, index: int, color: RGB) -> None:
        """
        Set individual pixel color (does not render immediately).
        
        Args:
            index: Pixel index
            color: RGB tuple (0-255, 0-255, 0-255)
        """
        if 0 <= index < self.count:
            r, g, b = [max(0, min(255, int(c * self.brightness / 255))) for c in color]
            self.frame_buffer[index] = (r, g, b)
    
    def set_all(self, color: RGB) -> None:
        """
        Set all pixels to same color.
        
        Args:
            color: RGB tuple
        """
        for i in range(self.count):
            self.set_pixel(i, color)
    
    def clear(self) -> None:
        """Clear all pixels (set to black)."""
        self.set_all((0, 0, 0))
    
    def render(self) -> None:
        """
        Render current frame buffer to hardware.
        Rate-limited to prevent excessive I2C/SPI traffic.
        """
        now = time.time()
        elapsed = now - self.last_render_time
        
        if elapsed < self.min_frame_interval:
            return  # Skip frame to maintain max FPS
        
        if self.pixels is None:
            logger.debug(f"Mock render: {len(self.frame_buffer)} pixels")
            return
        
        try:
            for i, (r, g, b) in enumerate(self.frame_buffer):
                self.pixels[i] = (r, g, b)
            self.pixels.show()
            self.last_render_time = now
        except Exception as e:
            logger.error(f"Failed to render frame: {e}")
    
    def set_brightness(self, brightness: int) -> None:
        """
        Set global brightness (0-255).
        
        Args:
            brightness: Brightness value
        """
        self.brightness = max(0, min(255, brightness))
        if self.pixels:
            self.pixels.brightness = self.brightness / 255.0
        logger.info(f"LED brightness set to {self.brightness}")
    
    def shutdown(self) -> None:
        """Clean shutdown of LED driver."""
        try:
            self.clear()
            self.render()
            logger.info("LED engine shut down")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
