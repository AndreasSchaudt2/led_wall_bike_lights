"""
Wi-Fi management using NetworkManager.
Handles AP setup mode and STA client connection.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WiFiService:
    """
    Manage Wi-Fi connectivity and AP setup mode.
    """
    
    def __init__(self, ap_ssid: str = "BikeLights-Setup"):
        """
        Initialize Wi-Fi service.
        
        Args:
            ap_ssid: SSID to advertise in AP mode
        """
        self.ap_ssid = ap_ssid
        self.is_ap_mode = False
        logger.info("Wi-Fi service initialized")
    
    def enter_ap_mode(self) -> bool:
        """
        Enter AP (access point) setup mode.
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Entering AP mode, SSID: {self.ap_ssid}")
            
            # Create AP connection profile
            cmd = [
                "nmcli", "con", "add", "type", "wifi", "ifname", "wlan0",
                "con-name", "BikeLights-AP", "autoconnect", "no",
                "ssid", self.ap_ssid
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Set to AP mode
            cmd = [
                "nmcli", "con", "modify", "BikeLights-AP",
                "802-11-wireless.mode", "ap"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Activate AP
            cmd = ["nmcli", "con", "up", "BikeLights-AP"]
            subprocess.run(cmd, check=True, capture_output=True)
            
            self.is_ap_mode = True
            logger.info("AP mode activated")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to enter AP mode: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting up AP mode: {e}")
            return False
    
    def exit_ap_mode(self) -> bool:
        """
        Exit AP mode and return to normal operation.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Exiting AP mode")
            
            # Disconnect AP
            cmd = ["nmcli", "con", "down", "BikeLights-AP"]
            subprocess.run(cmd, capture_output=True)
            
            # Remove AP connection
            cmd = ["nmcli", "con", "delete", "BikeLights-AP"]
            subprocess.run(cmd, capture_output=True)
            
            self.is_ap_mode = False
            logger.info("AP mode deactivated")
            return True
        
        except Exception as e:
            logger.error(f"Error exiting AP mode: {e}")
            return False
    
    def connect_to_network(self, ssid: str, password: str) -> bool:
        """
        Connect to a Wi-Fi network.
        
        Args:
            ssid: Network SSID
            password: Network password
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to network: {ssid}")
            
            # Create connection
            cmd = [
                "nmcli", "dev", "wifi", "connect", ssid,
                "password", password
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Connection failed: {result.stderr}")
                return False
            
            # Wait for IP assignment
            time.sleep(2)
            
            # Verify connection
            if self.is_connected():
                logger.info("Connected successfully")
                return True
            else:
                logger.error("Connection verification failed")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("Connection attempt timed out")
            return False
        except Exception as e:
            logger.error(f"Error connecting to network: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if device is connected to a network.
        
        Returns:
            True if connected
        """
        try:
            result = subprocess.run(
                ["nmcli", "device", "status"],
                capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'wlan0' in line and 'connected' in line:
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            return False
    
    def get_connection_info(self) -> Optional[dict]:
        """
        Get current connection details.
        
        Returns:
            Dict with connection info or None
        """
        try:
            result = subprocess.run(
                ["nmcli", "con", "show", "--active"],
                capture_output=True, text=True
            )
            
            info = {}
            for line in result.stdout.split('\n'):
                if 'connection.id' in line:
                    info['ssid'] = line.split()[-1]
                if 'ipv4.addresses' in line:
                    info['ip'] = line.split()[-1].split('/')[0]
            
            return info if info else None
        
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return None
    
    def disconnect(self) -> bool:
        """
        Disconnect from current network.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Disconnecting from network")
            cmd = ["nmcli", "device", "disconnect", "wlan0"]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False
