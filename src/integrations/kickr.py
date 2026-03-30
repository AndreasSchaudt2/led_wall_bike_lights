"""
Wahoo KICKR Core BLE integration.
Reads power data and maps to color zones.
(Stub implementation - full BLE support in future)
"""

import logging
import asyncio
from typing import Optional, Callable

logger = logging.getLogger(__name__)

try:
    from bleak import BleakClient, BleakScanner
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False
    logger.warning("Bleak not available, KICKR integration disabled")


class KickrService:
    """
    Connects to Wahoo KICKR trainer via Bluetooth LE.
    Reads cycling power and maps to configured zones.
    """
    
    # GATT UUIDs for power measurement
    CYCLING_POWER_SERVICE_UUID = "180d"  # Cycling Power Service
    CYCLING_POWER_MEASUREMENT_UUID = "2a63"  # Cycling Power Measurement
    
    def __init__(self, device_name: str = "", ftp: int = 250):
        """
        Initialize KICKR service.
        
        Args:
            device_name: Optional exact BLE device name to connect to
            ftp: Functional Threshold Power in watts
        """
        self.device_name = device_name
        self.ftp = ftp
        self.client = None
        self.is_connected = False
        self.current_power = 0
        self.power_callback: Optional[Callable] = None
        logger.info(f"KICKR service initialized (FTP: {ftp}W)")
    
    async def discover_trainer(self) -> Optional[str]:
        """
        Discover KICKR trainer via BLE scan.
        
        Returns:
            Device address if found
        """
        if not HAS_BLEAK:
            logger.error("Bleak not available")
            return None
        
        try:
            logger.info("Scanning for KICKR trainer...")
            scanner = BleakScanner()
            devices = await scanner.discover(timeout=5.0)
            
            for device in devices:
                name = device.name or ""
                if "KICKR" in name.upper() or "Wahoo" in name:
                    logger.info(f"Found trainer: {name} ({device.address})")
                    return device.address
            
            logger.warning("No KICKR trainer found")
            return None
        
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return None
    
    async def connect(self) -> bool:
        """
        Connect to KICKR trainer.
        
        Returns:
            True if connected successfully
        """
        if not HAS_BLEAK:
            logger.error("Bleak not available")
            return False
        
        try:
            # Find device address
            address = None
            if self.device_name:
                logger.info(f"Looking for device: {self.device_name}")
                scanner = BleakScanner()
                devices = await scanner.discover(timeout=5.0)
                for device in devices:
                    if device.name == self.device_name:
                        address = device.address
                        break
            else:
                address = await self.discover_trainer()
            
            if not address:
                logger.error("Could not find trainer")
                return False
            
            # Connect
            self.client = BleakClient(address)
            await self.client.connect()
            self.is_connected = True
            logger.info(f"Connected to {address}")
            
            # Start reading power
            asyncio.create_task(self._read_power_loop())
            return True
        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from trainer."""
        if self.client:
            try:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("Disconnected from trainer")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")
    
    async def _read_power_loop(self) -> None:
        """
        Continuous power data reading loop.
        """
        if not self.client:
            return
        
        try:
            while self.is_connected:
                try:
                    data = await self.client.read_gatt_char(self.CYCLING_POWER_MEASUREMENT_UUID)
                    power = self._parse_power_data(data)
                    self.current_power = power
                    
                    if self.power_callback:
                        self.power_callback(power)
                    
                    await asyncio.sleep(1)  # Read every 1 second
                
                except Exception as e:
                    logger.debug(f"Read error: {e}")
                    await asyncio.sleep(2)
                    break
        
        except Exception as e:
            logger.error(f"Power loop error: {e}")
            self.is_connected = False
    
    def _parse_power_data(self, data: bytes) -> int:
        """
        Parse power from GATT characteristic data.
        
        Args:
            data: Raw BLE characteristic data
        
        Returns:
            Power in watts
        """
        if len(data) < 4:
            return 0
        
        # Cycling Power Measurement format (simplified)
        # Flags: byte 0
        # Instantaneous Power: bytes 2-3 (little-endian, signed)
        power = int.from_bytes(data[2:4], byteorder='little', signed=True)
        return max(0, power)
    
    def on_power(self, callback: Callable) -> None:
        """
        Register power reading callback.
        
        Args:
            callback: Function taking power (int) as argument
        """
        self.power_callback = callback
        logger.debug("Power callback registered")
    
    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.disconnect()
        logger.info("KICKR service shut down")
