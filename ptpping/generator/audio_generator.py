"""
Audio generator for PTPPing.
Generates 440 Hz tone bursts synchronized to PTP time.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from ..core.config import Config
from ..core.ptp_time import PTPTimeManager


class AudioGenerator:
    """Generates audio tone bursts synchronized to PTP time."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ptp_time = PTPTimeManager(config.ptp)
        
        self._running = False
        self._thread = None
        self._vlc_process = None
        
        # Generate the tone burst
        self._generate_tone_burst()
    
    def _generate_tone_burst(self) -> None:
        """Generate the 440 Hz tone burst audio file."""
        try:
            # Calculate samples for the burst duration
            samples = int(self.config.audio.sample_rate * self.config.audio.burst_duration)
            
            # Generate time array
            t = np.linspace(0, self.config.audio.burst_duration, samples, False)
            
            # Generate 440 Hz sine wave
            frequency = self.config.audio.tone_frequency
            tone = np.sin(2 * np.pi * frequency * t)
            
            # Apply fade in/out to avoid clicks
            fade_samples = int(0.01 * self.config.audio.sample_rate)  # 10ms fade
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                tone[:fade_samples] *= fade_in
                tone[-fade_samples:] *= fade_out
            
            # Normalize to 16-bit range
            tone = (tone * 32767).astype(np.int16)
            
            # Save to file
            output_path = Path(__file__).parent / "tone_burst.wav"
            sf.write(output_path, tone, self.config.audio.sample_rate)
            
            self.logger.info(f"Generated tone burst: {frequency} Hz, {self.config.audio.burst_duration}s")
            
        except Exception as e:
            self.logger.error(f"Failed to generate tone burst: {e}")
            raise
    
    def start(self) -> None:
        """Start the audio generator."""
        if self._running:
            self.logger.warning("Audio generator already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        self.logger.info("Audio generator started")
    
    def stop(self) -> None:
        """Stop the audio generator."""
        self._running = False
        
        if self._vlc_process:
            try:
                self._vlc_process.terminate()
                self._vlc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._vlc_process.kill()
            finally:
                self._vlc_process = None
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self.logger.info("Audio generator stopped")
    
    def _run(self) -> None:
        """Main generation loop."""
        try:
            # Start VLC with loopback
            self._start_vlc()
            
            # Main timing loop
            while self._running:
                # Wait for next burst time
                self._wait_for_next_burst()
                
                if not self._running:
                    break
                
                # Trigger tone burst
                self._trigger_burst()
                
        except Exception as e:
            self.logger.error(f"Error in audio generation loop: {e}")
        finally:
            self._stop_vlc()
    
    def _start_vlc(self) -> None:
        """Start VLC with audio loopback configuration."""
        try:
            # VLC command to play silence with audio loopback
            vlc_cmd = [
                'vlc',
                '--intf', 'dummy',  # No GUI
                '--audio-filter', 'audiobargraph_a',  # Audio bargraph filter
                '--audio-filter-param', f'frequency={self.config.audio.tone_frequency}',
                '--audio-filter-param', f'duration={int(self.config.audio.burst_duration * 1000)}',
                '--audio-filter-param', f'interval={int(self.config.audio.burst_interval * 1000)}',
                '--audio-filter-param', 'silence=1',  # Play silence
                '--audio-filter-param', 'loopback=1',  # Enable loopback
                '--audio-device', self.config.audio.loopback_device,
                '--gain', '0',  # Mute output
                '--repeat',  # Loop indefinitely
                'vlc://quit'  # Dummy input
            ]
            
            self._vlc_process = subprocess.Popen(
                vlc_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.logger.info("VLC started with audio loopback")
            
        except Exception as e:
            self.logger.error(f"Failed to start VLC: {e}")
            raise
    
    def _stop_vlc(self) -> None:
        """Stop VLC process."""
        if self._vlc_process:
            try:
                self._vlc_process.terminate()
                self._vlc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._vlc_process.kill()
            finally:
                self._vlc_process = None
    
    def _wait_for_next_burst(self) -> None:
        """Wait until the next scheduled burst time."""
        current_ptp_time = self.ptp_time.get_ptp_time()
        if current_ptp_time is None:
            time.sleep(0.1)  # Fallback if PTP unavailable
            return
        
        # Calculate time until next burst
        time_since_epoch = current_ptp_time
        next_burst = (time_since_epoch // self.config.audio.burst_interval + 1) * self.config.audio.burst_interval
        wait_time = next_burst - time_since_epoch
        
        if wait_time > 0:
            time.sleep(wait_time)
    
    def _trigger_burst(self) -> None:
        """Trigger a tone burst."""
        try:
            # Get PTP timestamp for this burst
            ptp_time, system_time = self.ptp_time.get_timestamp()
            
            if ptp_time is not None:
                self.logger.debug(f"Tone burst at PTP time: {ptp_time:.6f}")
            else:
                self.logger.debug(f"Tone burst at system time: {system_time:.6f}")
                
        except Exception as e:
            self.logger.error(f"Error triggering burst: {e}")
    
    def get_status(self) -> dict:
        """Get current status of the audio generator."""
        return {
            'running': self._running,
            'ptp_synchronized': self.ptp_time.is_synchronized(),
            'ptp_offset': self.ptp_time.calculate_offset(),
            'vlc_running': self._vlc_process is not None and self._vlc_process.poll() is None
        }
