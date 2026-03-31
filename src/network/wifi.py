"""
Wi-Fi management using NetworkManager.
Handles AP setup mode and STA client connection.
"""

import logging
import shutil
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
        self.nmcli_cmd = shutil.which("nmcli") or "/usr/bin/nmcli"
        self.systemctl_cmd = shutil.which("systemctl") or "/bin/systemctl"
        logger.info("Wi-Fi service initialized")

    def _run_nmcli(self, args, check: bool = False, text: bool = False, timeout: Optional[int] = None):
        """Run nmcli with a stable absolute path in the systemd environment."""
        cmd = [self.nmcli_cmd, *args]
        return subprocess.run(cmd, check=check, capture_output=True, text=text, timeout=timeout)

    def _run_systemctl(self, args, check: bool = False):
        """Run systemctl with a stable absolute path."""
        cmd = [self.systemctl_cmd, *args]
        return subprocess.run(cmd, check=check, capture_output=True, text=True)

    def has_wifi_connect(self) -> bool:
        """Return True if wifi-connect service exists on this host."""
        try:
            result = self._run_systemctl(["status", "wifi-connect.service"])
            return result.returncode in (0, 3)  # active/inactive but known unit
        except Exception:
            return False

    def start_wifi_connect(self) -> bool:
        """Start proven provisioning service (balena wifi-connect)."""
        try:
            logger.info("Starting wifi-connect provisioning service")
            self._run_systemctl(["start", "wifi-connect.service"], check=True)
            self.is_ap_mode = True
            return True
        except subprocess.CalledProcessError as e:
            logger.error(
                "Failed to start wifi-connect service: rc=%s stdout=%s stderr=%s",
                e.returncode,
                (e.stdout or "").strip(),
                (e.stderr or "").strip(),
            )
            return False
        except Exception as e:
            logger.error(f"Error starting wifi-connect service: {e}")
            return False

    def stop_wifi_connect(self) -> bool:
        """Stop provisioning service if running."""
        try:
            self._run_systemctl(["stop", "wifi-connect.service"])
            return True
        except Exception:
            return False
    
    def enter_ap_mode(self) -> bool:
        """
        Enter AP (access point) setup mode.
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Entering AP mode, SSID: {self.ap_ssid}")

            # Remove any stale AP profile and disconnect wlan0 from current network.
            self._run_nmcli(["con", "down", "BikeLights-AP"])
            self._run_nmcli(["con", "delete", "BikeLights-AP"])
            self._run_nmcli(["device", "disconnect", "wlan0"])
            
            # Create AP connection profile
            self._run_nmcli([
                "con", "add", "type", "wifi", "ifname", "wlan0",
                "con-name", "BikeLights-AP", "autoconnect", "no",
                "ssid", self.ap_ssid
            ], check=True)
            
            # Set to AP mode
            self._run_nmcli([
                "con", "modify", "BikeLights-AP",
                "802-11-wireless.mode", "ap"
            ], check=True)

            # Shared IP mode is required for a functional setup hotspot.
            self._run_nmcli([
                "con", "modify", "BikeLights-AP",
                "ipv4.method", "shared",
                "ipv6.method", "disabled",
                "connection.autoconnect", "no",
                "802-11-wireless.band", "bg"
            ], check=True)
            
            # Activate AP
            self._run_nmcli(["con", "up", "BikeLights-AP"], check=True)
            
            self.is_ap_mode = True
            logger.info("AP mode activated")
            return True
        
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            logger.error(
                "Failed to enter AP mode: returncode=%s stdout=%s stderr=%s",
                e.returncode,
                stdout.strip(),
                stderr.strip(),
            )
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
            self._run_nmcli(["con", "down", "BikeLights-AP"])
            
            # Remove AP connection
            self._run_nmcli(["con", "delete", "BikeLights-AP"])
            
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

            # Leave AP mode before attempting station/client connection.
            if self.is_ap_mode:
                self.exit_ap_mode()

            # Remove stale profile for the target SSID so security settings are rebuilt cleanly.
            self._run_nmcli(["con", "delete", ssid])

            if password:
                result = self._run_nmcli([
                    "dev", "wifi", "connect", ssid,
                    "password", password
                ], text=True, timeout=30)
            else:
                result = self._run_nmcli([
                    "dev", "wifi", "connect", ssid
                ], text=True, timeout=30)
            
            if result.returncode != 0:
                error_text = (result.stderr or result.stdout or "unknown error").strip()
                logger.error(f"Connection failed: {error_text}")
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
            result = self._run_nmcli(["device", "status"], text=True)
            
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
            result = self._run_nmcli(["con", "show", "--active"], text=True)
            
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
            self._run_nmcli(["device", "disconnect", "wlan0"], check=True)
            return True
        
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False

    def connect_result(self, ssid: str, password: str) -> tuple[bool, str]:
        """Connect and return both success state and a human-readable message."""
        try:
            logger.info(f"Connecting to network: {ssid}")

            if self.is_ap_mode:
                self.exit_ap_mode()

            self._run_nmcli(["con", "delete", ssid])

            if password:
                result = self._run_nmcli([
                    "dev", "wifi", "connect", ssid,
                    "password", password
                ], text=True, timeout=30)
            else:
                result = self._run_nmcli([
                    "dev", "wifi", "connect", ssid
                ], text=True, timeout=30)

            if result.returncode != 0:
                error_text = (result.stderr or result.stdout or "unknown error").strip()
                logger.error(f"Connection failed: {error_text}")
                return False, error_text

            time.sleep(2)

            if self.is_connected():
                logger.info("Connected successfully")
                return True, "Connected successfully"

            logger.error("Connection verification failed")
            return False, "Connection verification failed"

        except subprocess.TimeoutExpired:
            logger.error("Connection attempt timed out")
            return False, "Connection attempt timed out"
        except Exception as e:
            logger.error(f"Error connecting to network: {e}")
            return False, str(e)
