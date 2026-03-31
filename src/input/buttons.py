"""
Button input handling with debounce and long-press detection.
Emits events for mode switching and special actions.
"""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ButtonEvent(Enum):
    """Button event types."""
    SHORT_PRESS = "short_press"
    LONG_PRESS = "long_press"
    DOUBLE_PRESS = "double_press"


class Button:
    """
    Single button handler with debounce and long-press detection.
    """
    
    def __init__(self, pin: int, name: str = "Button", 
                 debounce_ms: int = 50, long_press_ms: int = 1000):
        """
        Initialize button.
        
        Args:
            pin: GPIO pin number (BCM)
            name: Button name for logging
            debounce_ms: Debounce window in milliseconds
            long_press_ms: Long press threshold in milliseconds
        """
        self.pin = pin
        self.name = name
        self.debounce_ms = debounce_ms
        self.long_press_ms = long_press_ms
        self.callbacks = {}
        self.is_pressed = False
        self.press_time = 0
        self.last_event_time = 0
        self.gpio = None
        self.using_polling = False
        self.poll_thread = None
        self.stop_polling = False
        
        logger.info(f"Button {name} initialized on GPIO {pin}")
        self._initialize_gpio()
    
    def _initialize_gpio(self) -> None:
        """Initialize GPIO for button input."""
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            try:
                # Use BOTH edges so we can correctly detect press and release.
                GPIO.add_event_detect(
                    self.pin,
                    GPIO.BOTH,
                    callback=self._on_gpio_change,
                    bouncetime=self.debounce_ms
                )
                logger.info(f"GPIO {self.pin} event detection enabled")
            except Exception as e:
                logger.warning(f"GPIO edge detection unavailable on pin {self.pin}: {e}; using polling fallback")
                self._start_polling()
        except ImportError:
            logger.warning("RPi.GPIO not available, running in mock mode")
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
    
    def _on_gpio_change(self, channel: int) -> None:
        """GPIO change callback."""
        if self.gpio is None:
            return

        current_time = time.time() * 1000  # Convert to ms

        # Active-low button: 0 = pressed, 1 = released.
        pin_state = self.gpio.input(self.pin)

        if pin_state == 0 and not self.is_pressed:
            # Button pressed
            self.is_pressed = True
            self.press_time = current_time
        elif pin_state == 1 and self.is_pressed:
            # Button released
            hold_time = current_time - self.press_time
            self.is_pressed = False
            
            # Determine event type
            if hold_time >= self.long_press_ms:
                self._emit_event(ButtonEvent.LONG_PRESS)
            else:
                self._emit_event(ButtonEvent.SHORT_PRESS)

    def _start_polling(self) -> None:
        """Fallback polling loop when edge detection is not available."""
        if self.gpio is None:
            return

        self.using_polling = True
        self.stop_polling = False

        def _poll_loop():
            last_state = self.gpio.input(self.pin)
            while not self.stop_polling:
                try:
                    state = self.gpio.input(self.pin)
                    if state != last_state:
                        self._on_gpio_change(self.pin)
                        last_state = state
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"Polling error on {self.name}: {e}")
                    time.sleep(0.05)

        self.poll_thread = threading.Thread(target=_poll_loop, daemon=True)
        self.poll_thread.start()
    
    def _emit_event(self, event: ButtonEvent) -> None:
        """Emit button event to registered callbacks."""
        now = time.time()
        
        # Debounce events
        if now - self.last_event_time < 0.1:
            return
        
        self.last_event_time = now
        
        if event in self.callbacks:
            logger.debug(f"{self.name} event: {event.value}")
            for callback in self.callbacks[event]:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in button callback: {e}")
    
    def on(self, event: ButtonEvent, callback: Callable) -> None:
        """
        Register event callback.
        
        Args:
            event: ButtonEvent to listen for
            callback: Callable to invoke on event
        """
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        logger.debug(f"Registered callback for {self.name} {event.value}")
    
    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            self.stop_polling = True
            if self.poll_thread and self.poll_thread.is_alive():
                self.poll_thread.join(timeout=1)

            if self.gpio is not None:
                if not self.using_polling:
                    self.gpio.remove_event_detect(self.pin)
                self.gpio.cleanup(self.pin)

            logger.info(f"Button {self.name} cleaned up")
        except Exception as e:
            logger.error(f"Error during button cleanup: {e}")


class ButtonService:
    """
    Manages multiple buttons and emits high-level actions.
    """
    
    def __init__(self, btn1_pin: int, btn2_pin: int, long_press_ms: int = 3000):
        """
        Initialize button service.
        
        Args:
            btn1_pin: GPIO pin for button 1
            btn2_pin: GPIO pin for button 2
            long_press_ms: Long press threshold
        """
        self.btn1 = Button(btn1_pin, name="Button1", long_press_ms=long_press_ms)
        self.btn2 = Button(btn2_pin, name="Button2", long_press_ms=long_press_ms)
        
        self.action_callbacks = {}
        self._setup_callbacks()
        logger.info("Button service initialized")
    
    def _setup_callbacks(self) -> None:
        """Register button event callbacks."""
        self.btn1.on(ButtonEvent.SHORT_PRESS, lambda: self._emit_action("btn1_short"))
        self.btn1.on(ButtonEvent.LONG_PRESS, lambda: self._emit_action("btn1_long"))
        self.btn2.on(ButtonEvent.SHORT_PRESS, lambda: self._emit_action("btn2_short"))
        self.btn2.on(ButtonEvent.LONG_PRESS, lambda: self._emit_action("btn2_long"))
    
    def _emit_action(self, action: str) -> None:
        """Emit action to registered callbacks."""
        if action in self.action_callbacks:
            for callback in self.action_callbacks[action]:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in action callback: {e}")
    
    def on_action(self, action: str, callback: Callable) -> None:
        """
        Register action callback.
        
        Args:
            action: Action name ('btn1_short', 'btn1_long', 'btn2_short', 'btn2_long')
            callback: Callable to invoke
        """
        if action not in self.action_callbacks:
            self.action_callbacks[action] = []
        self.action_callbacks[action].append(callback)
    
    def cleanup(self) -> None:
        """Clean up all button resources."""
        self.btn1.cleanup()
        self.btn2.cleanup()
