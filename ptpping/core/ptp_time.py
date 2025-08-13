"""
PTP time management for PTPPing.
"""

import logging
import subprocess
import time
from typing import Optional, Tuple

from .config import PTPConfig


class PTPTimeManager:
    """Manages PTP time synchronization and provides timestamping functions."""
    
    def __init__(self, config: PTPConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._ptp_sync = False
        self._last_sync_check = 0
        self._sync_check_interval = 60  # Check sync status every 60 seconds
        
    def get_ptp_time(self) -> Optional[float]:
        """Get current PTP time in seconds since epoch."""
        try:
            # Check if we need to verify PTP sync status
            current_time = time.time()
            if current_time - self._last_sync_check > self._sync_check_interval:
                self._check_ptp_sync()
                self._last_sync_check = current_time
            
            if not self._ptp_sync:
                self.logger.warning("PTP not synchronized, using system time")
                return time.time()
            
            # Get PTP time from system
            result = subprocess.run(
                ['phc_ctl', '-d', self.config.interface, 'get'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse PTP time from output
                # Expected format: "phc_ctl: clock time is 1234567890.123456789"
                for line in result.stdout.splitlines():
                    if 'clock time is' in line:
                        try:
                            ptp_time_str = line.split('clock time is')[-1].strip()
                            ptp_time = float(ptp_time_str)
                            return ptp_time
                        except ValueError:
                            self.logger.error(f"Failed to parse PTP time: {line}")
                            break
            
            # Fallback to system time if PTP time unavailable
            self.logger.warning("Failed to get PTP time, using system time")
            return time.time()
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout getting PTP time")
            return time.time()
        except Exception as e:
            self.logger.error(f"Error getting PTP time: {e}")
            return time.time()
    
    def _check_ptp_sync(self) -> None:
        """Check PTP synchronization status."""
        try:
            # Check if PTP daemon is running
            result = subprocess.run(
                ['pgrep', 'ptp4l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self.logger.warning("PTP daemon (ptp4l) not running")
                self._ptp_sync = False
                return
            
            # Check PTP sync status
            result = subprocess.run(
                ['pmc', '-d', self.config.interface, 'get', 'CLOCK_CLASS'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse clock class from output
                # Clock class 6 = synchronized, 7 = holdover, 52 = unsynchronized
                for line in result.stdout.splitlines():
                    if 'CLOCK_CLASS' in line:
                        try:
                            clock_class = int(line.split()[-1])
                            self._ptp_sync = clock_class in [6, 7]  # 6=sync, 7=holdover
                            if self._ptp_sync:
                                self.logger.debug(f"PTP synchronized (clock class: {clock_class})")
                            else:
                                self.logger.warning(f"PTP not synchronized (clock class: {clock_class})")
                            return
                        except ValueError:
                            self.logger.error(f"Failed to parse clock class: {line}")
                            break
            
            self.logger.warning("Could not determine PTP sync status")
            self._ptp_sync = False
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout checking PTP sync status")
            self._ptp_sync = False
        except Exception as e:
            self.logger.error(f"Error checking PTP sync status: {e}")
            self._ptp_sync = False
    
    def get_timestamp(self) -> Tuple[float, float]:
        """Get both PTP and system timestamps."""
        ptp_time = self.get_ptp_time()
        system_time = time.time()
        return ptp_time, system_time
    
    def calculate_offset(self) -> Optional[float]:
        """Calculate offset between PTP and system time."""
        ptp_time, system_time = self.get_timestamp()
        if ptp_time is not None:
            return ptp_time - system_time
        return None
    
    def is_synchronized(self) -> bool:
        """Check if PTP is currently synchronized."""
        current_time = time.time()
        if current_time - self._last_sync_check > self._sync_check_interval:
            self._check_ptp_sync()
            self._last_sync_check = current_time
        return self._ptp_sync
