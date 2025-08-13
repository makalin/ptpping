"""
PTPPing - Network-wide Audio Latency Probe

A passive-measurement toolkit that pinpoints how much each network hop adds 
to real-time audio latency by shipping actual audio through production VLANs 
and timestamping against the PTP grandmaster clock.
"""

__version__ = "1.0.0"
__author__ = "PTPing Authors"
__license__ = "MIT"

from .core.config import Config
from .core.logger import setup_logging

__all__ = ["Config", "setup_logging"]
