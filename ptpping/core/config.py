"""
Configuration management for PTPPing.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import toml


@dataclass
class PTPConfig:
    """PTP configuration settings."""
    interface: str
    domain: int
    priority: int


@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int
    tone_frequency: int
    burst_duration: float
    burst_interval: float
    device: str
    loopback_device: str


@dataclass
class NetworkConfig:
    """Network configuration settings."""
    switch_name: str
    host_name: str
    vlan_id: int


@dataclass
class InfluxDBConfig:
    """InfluxDB configuration settings."""
    url: str
    database: str
    organization: str
    token: str
    retention_days: int


@dataclass
class GrafanaConfig:
    """Grafana configuration settings."""
    url: str
    api_key: str


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str
    file: str
    max_size: int
    backup_count: int


@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    system_metrics: bool
    metrics_interval: int
    webhook_enabled: bool
    webhook_url: str


@dataclass
class Config:
    """Main configuration class."""
    ptp: PTPConfig
    audio: AudioConfig
    network: NetworkConfig
    influxdb: InfluxDBConfig
    grafana: GrafanaConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'Config':
        """Load configuration from TOML file."""
        try:
            config_data = toml.load(config_path)
            
            # Validate and create configuration objects
            ptp = PTPConfig(
                interface=config_data['ptp']['interface'],
                domain=config_data['ptp']['domain'],
                priority=config_data['ptp']['priority']
            )
            
            audio = AudioConfig(
                sample_rate=config_data['audio']['sample_rate'],
                tone_frequency=config_data['audio']['tone_frequency'],
                burst_duration=config_data['audio']['burst_duration'],
                burst_interval=config_data['audio']['burst_interval'],
                device=config_data['audio']['device'],
                loopback_device=config_data['audio']['loopback_device']
            )
            
            network = NetworkConfig(
                switch_name=config_data['network']['switch_name'],
                host_name=config_data['network']['host_name'],
                vlan_id=config_data['network']['vlan_id']
            )
            
            influxdb = InfluxDBConfig(
                url=config_data['influxdb']['url'],
                database=config_data['influxdb']['database'],
                organization=config_data['influxdb']['organization'],
                token=config_data['influxdb']['token'],
                retention_days=config_data['influxdb']['retention_days']
            )
            
            grafana = GrafanaConfig(
                url=config_data['grafana']['url'],
                api_key=config_data['grafana']['api_key']
            )
            
            logging_config = LoggingConfig(
                level=config_data['logging']['level'],
                file=config_data['logging']['file'],
                max_size=config_data['logging']['max_size'],
                backup_count=config_data['logging']['backup_count']
            )
            
            monitoring = MonitoringConfig(
                system_metrics=config_data['monitoring']['system_metrics'],
                metrics_interval=config_data['monitoring']['metrics_interval'],
                webhook_enabled=config_data['monitoring']['webhook_enabled'],
                webhook_url=config_data['monitoring']['webhook_url']
            )
            
            return cls(
                ptp=ptp,
                audio=audio,
                network=network,
                influxdb=influxdb,
                grafana=grafana,
                logging=logging_config,
                monitoring=monitoring
            )
            
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    def validate(self) -> bool:
        """Validate configuration values."""
        # Validate audio settings
        if self.audio.sample_rate % self.audio.tone_frequency != 0:
            raise ValueError(
                f"Tone frequency {self.audio.tone_frequency} must be an integer "
                f"divisor of sample rate {self.audio.sample_rate}"
            )
        
        if self.audio.burst_duration <= 0 or self.audio.burst_interval <= 0:
            raise ValueError("Burst duration and interval must be positive")
        
        if self.audio.burst_duration >= self.audio.burst_interval:
            raise ValueError("Burst duration must be less than burst interval")
        
        # Validate PTP settings
        if self.ptp.domain < 0 or self.ptp.domain > 255:
            raise ValueError("PTP domain must be between 0 and 255")
        
        if self.ptp.priority < 0 or self.ptp.priority > 255:
            raise ValueError("PTP priority must be between 0 and 255")
        
        return True
