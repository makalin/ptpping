"""
Audio capture for PTPPing.
Captures audio from loopback device and detects tone bursts for latency measurement.
"""

import logging
import threading
import time
from typing import Optional, List, Tuple

import numpy as np
import pyaudio
import scipy.signal as signal
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from ..core.config import Config
from ..core.ptp_time import PTPTimeManager


class AudioCapture:
    """Captures audio and detects tone bursts for latency measurement."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ptp_time = PTPTimeManager(config.ptp)
        
        self._running = False
        self._thread = None
        self._audio = None
        self._stream = None
        
        # InfluxDB client
        self._influx_client = None
        self._write_api = None
        
        # Audio processing parameters
        self._chunk_size = 1024
        self._sample_rate = config.audio.sample_rate
        self._tone_frequency = config.audio.tone_frequency
        self._burst_duration = config.audio.burst_duration
        
        # Detection parameters
        self._detection_threshold = 0.1
        self._min_burst_gap = 0.5  # Minimum time between bursts
        
        # State tracking
        self._last_burst_time = 0
        self._detected_bursts = []
        
        # Initialize InfluxDB connection
        self._init_influxdb()
    
    def _init_influxdb(self) -> None:
        """Initialize InfluxDB connection."""
        try:
            self._influx_client = InfluxDBClient(
                url=self.config.influxdb.url,
                token=self.config.influxdb.token,
                org=self.config.influxdb.organization
            )
            
            # Test connection
            self._influx_client.ping()
            
            self._write_api = self._influx_client.write_api(write_options=SYNCHRONOUS)
            
            self.logger.info("InfluxDB connection established")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to InfluxDB: {e}")
            self._influx_client = None
            self._write_api = None
    
    def start(self) -> None:
        """Start the audio capture."""
        if self._running:
            self.logger.warning("Audio capture already running")
            return
        
        try:
            self._audio = pyaudio.PyAudio()
            self._start_audio_stream()
            
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            
            self.logger.info("Audio capture started")
            
        except Exception as e:
            self.logger.error(f"Failed to start audio capture: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the audio capture."""
        self._running = False
        
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
        
        if self._thread:
            self._thread.join(timeout=5)
        
        if self._influx_client:
            self._influx_client.close()
        
        self.logger.info("Audio capture stopped")
    
    def _start_audio_stream(self) -> None:
        """Start the audio input stream."""
        try:
            # Find the loopback device
            device_index = self._find_loopback_device()
            
            self._stream = self._audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self._sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self._chunk_size,
                stream_callback=self._audio_callback
            )
            
            self._stream.start_stream()
            self.logger.info(f"Audio stream started on device {device_index}")
            
        except Exception as e:
            self.logger.error(f"Failed to start audio stream: {e}")
            raise
    
    def _find_loopback_device(self) -> int:
        """Find the loopback audio device."""
        try:
            for i in range(self._audio.get_device_count()):
                device_info = self._audio.get_device_info_by_index(i)
                if (self.config.audio.loopback_device in device_info['name'] or
                    'loopback' in device_info['name'].lower()):
                    self.logger.info(f"Found loopback device: {device_info['name']}")
                    return i
            
            # Fallback to default input device
            self.logger.warning("Loopback device not found, using default input")
            return self._audio.get_default_input_device_info()['index']
            
        except Exception as e:
            self.logger.error(f"Error finding loopback device: {e}")
            return 0
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback for processing incoming audio data."""
        if not self._running:
            return (None, pyaudio.paComplete)
        
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Process audio chunk for tone detection
            self._process_audio_chunk(audio_data, time_info)
            
        except Exception as e:
            self.logger.error(f"Error in audio callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _process_audio_chunk(self, audio_data: np.ndarray, time_info: dict) -> None:
        """Process audio chunk for tone burst detection."""
        try:
            # Apply FFT to detect tone frequency
            fft_data = np.fft.fft(audio_data)
            freqs = np.fft.fftfreq(len(audio_data), 1.0 / self._sample_rate)
            
            # Find the bin closest to our target frequency
            target_bin = np.argmin(np.abs(freqs - self._tone_frequency))
            magnitude = np.abs(fft_data[target_bin])
            
            # Normalize magnitude
            normalized_magnitude = magnitude / len(audio_data)
            
            # Check if we detected a tone burst
            if normalized_magnitude > self._detection_threshold:
                current_time = time.time()
                
                # Check if enough time has passed since last burst
                if current_time - self._last_burst_time > self._min_burst_gap:
                    self._detect_burst(current_time, normalized_magnitude)
                    self._last_burst_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {e}")
    
    def _detect_burst(self, detection_time: float, magnitude: float) -> None:
        """Handle detected tone burst."""
        try:
            # Get PTP timestamp
            ptp_time, system_time = self.ptp_time.get_timestamp()
            
            # Calculate latency (difference between expected and actual burst time)
            expected_burst_time = self._calculate_expected_burst_time()
            if expected_burst_time is not None:
                latency = (detection_time - expected_burst_time) * 1000  # Convert to ms
                
                # Store burst information
                burst_info = {
                    'ptp_time': ptp_time,
                    'system_time': system_time,
                    'detection_time': detection_time,
                    'expected_time': expected_burst_time,
                    'latency_ms': latency,
                    'magnitude': magnitude
                }
                
                self._detected_bursts.append(burst_info)
                
                # Send to InfluxDB
                self._send_to_influxdb(burst_info)
                
                self.logger.debug(f"Tone burst detected: latency={latency:.2f}ms, magnitude={magnitude:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error handling detected burst: {e}")
    
    def _calculate_expected_burst_time(self) -> Optional[float]:
        """Calculate the expected time of the next burst based on PTP timing."""
        try:
            ptp_time = self.ptp_time.get_ptp_time()
            if ptp_time is None:
                return None
            
            # Calculate next burst time based on interval
            next_burst = (ptp_time // self.config.audio.burst_interval + 1) * self.config.audio.burst_interval
            
            # Convert PTP time to system time
            ptp_offset = self.ptp_time.calculate_offset()
            if ptp_offset is not None:
                return next_burst - ptp_offset
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating expected burst time: {e}")
            return None
    
    def _send_to_influxdb(self, burst_info: dict) -> None:
        """Send burst information to InfluxDB."""
        if not self._write_api:
            return
        
        try:
            # Create InfluxDB point
            point = Point("audio_latency") \
                .field("latency_ms", burst_info['latency_ms']) \
                .field("magnitude", burst_info['magnitude']) \
                .field("ptp_time", burst_info['ptp_time']) \
                .field("system_time", burst_info['system_time']) \
                .tag("switch", self.config.network.switch_name) \
                .tag("host", self.config.network.host_name) \
                .tag("vlan", str(self.config.network.vlan_id)) \
                .tag("ptp_sync", str(self.ptp_time.is_synchronized()))
            
            # Write to InfluxDB
            self._write_api.write(
                bucket=self.config.influxdb.database,
                record=point
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send data to InfluxDB: {e}")
    
    def _run(self) -> None:
        """Main capture loop."""
        try:
            while self._running:
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
        except Exception as e:
            self.logger.error(f"Error in capture loop: {e}")
    
    def get_status(self) -> dict:
        """Get current status of the audio capture."""
        return {
            'running': self._running,
            'ptp_synchronized': self.ptp_time.is_synchronized(),
            'ptp_offset': self.ptp_time.calculate_offset(),
            'influxdb_connected': self._influx_client is not None,
            'bursts_detected': len(self._detected_bursts),
            'audio_stream_active': self._stream is not None and self._stream.is_active()
        }
    
    def get_recent_bursts(self, count: int = 10) -> List[dict]:
        """Get recent burst detection data."""
        return self._detected_bursts[-count:] if self._detected_bursts else []
