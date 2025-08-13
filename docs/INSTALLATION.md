# PTPPing Installation Guide

This guide covers the complete installation and setup of PTPPing on Ubuntu/Debian systems.

## Prerequisites

### System Requirements
- Ubuntu 20.04 LTS or later / Debian 11 or later
- Python 3.8 or later
- Root access (for installation and PTP configuration)
- Network interface with PTP support
- Audio hardware with loopback capability

### Hardware Requirements
- **PTP Grandmaster**: Hardware timestamping support (optional, can use software PTP)
- **End Stations**: Any network interface (software PTP is sufficient)
- **Audio**: ALSA-compatible sound card with loopback support

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/makalin/ptpping.git
   cd ptpping
   ```

2. **Run the installation script:**
   ```bash
   sudo chmod +x install.sh
   sudo ./install.sh
   ```

3. **Configure PTPPing:**
   ```bash
   sudo nano /etc/ptpping/config.toml
   ```

### Method 2: Manual Installation

1. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv vlc alsa-utils \
                      linuxptp ptp4l phc2sys influxdb-client
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Set up ALSA loopback:**
   ```bash
   sudo modprobe snd-aloop
   echo "snd-aloop" | sudo tee -a /etc/modules
   ```

## Configuration

### 1. PTP Configuration

Ensure PTP is properly configured and synchronized:

```bash
# Check PTP status
sudo systemctl status ptp4l

# View PTP interface
sudo ip link show

# Check PTP synchronization
sudo pmc -d eth0 get CLOCK_CLASS
```

### 2. Audio Configuration

Verify audio loopback is working:

```bash
# List audio devices
aplay -l
arecord -l

# Test loopback
speaker-test -t sine -f 440 -c 1 -D hw:Loopback,0,0
```

### 3. PTPPing Configuration

Edit `/etc/ptpping/config.toml`:

```toml
[ptp]
interface = "eth0"  # Your PTP interface
domain = 0
priority = 128

[audio]
sample_rate = 48000
tone_frequency = 440
burst_duration = 0.1
burst_interval = 1.0
loopback_device = "hw:Loopback,0,0"

[network]
switch_name = "sw01"  # Your switch identifier
host_name = "ws01"    # Your host identifier
vlan_id = 0

[influxdb]
url = "http://localhost:8086"
database = "ptpping"
organization = "myorg"
token = "your-influxdb-token"

[grafana]
url = "http://localhost:3000"
api_key = "your-grafana-api-key"
```

## Service Management

### Start Services

```bash
# Start audio generator (on workstations)
sudo systemctl start ptpping-generator.service

# Start audio capture (on workstations)
sudo systemctl start ptpping-capture.service

# Start dashboard manager (once in NOC)
sudo systemctl start ptpping-dashboard.service
```

### Enable Services (Auto-start)

```bash
sudo systemctl enable ptpping-generator.service
sudo systemctl enable ptpping-capture.service
sudo systemctl enable ptpping-dashboard.service
```

### Check Service Status

```bash
sudo systemctl status ptpping-*
sudo journalctl -u ptpping-* -f
```

## Testing

### Run Test Script

```bash
python3 test_ptpping.py
```

### Manual Testing

1. **Test PTP synchronization:**
   ```bash
   sudo phc_ctl -d eth0 get
   ```

2. **Test audio generation:**
   ```bash
   sudo python3 ptpping.py --role generator --config config.toml
   ```

3. **Test audio capture:**
   ```bash
   sudo python3 ptpping.py --role capture --config config.toml
   ```

## Troubleshooting

### Common Issues

#### PTP Not Synchronized
```bash
# Check PTP daemon status
sudo systemctl status ptp4l

# Check interface configuration
sudo ip link show eth0

# Verify PTP messages
sudo tcpdump -i eth0 -s0 -w ptp.pcap port 319 or port 320
```

#### Audio Loopback Issues
```bash
# Check ALSA modules
lsmod | grep snd

# Test loopback device
speaker-test -t sine -f 440 -c 1 -D hw:Loopback,0,0

# Check audio permissions
sudo usermod -a -G audio ptpping
```

#### InfluxDB Connection Issues
```bash
# Test InfluxDB connection
influx ping

# Check authentication
influx auth list

# Verify bucket exists
influx bucket list
```

### Log Analysis

```bash
# View all PTPPing logs
sudo journalctl -u ptpping-* --since "1 hour ago"

# View specific service logs
sudo journalctl -u ptpping-generator.service -f

# Check system logs for audio/PTP issues
sudo dmesg | grep -i audio
sudo dmesg | grep -i ptp
```

## Performance Tuning

### Audio Processing
- Adjust `chunk_size` in `AudioCapture` for lower latency
- Modify `detection_threshold` for better sensitivity
- Tune `min_burst_gap` to avoid false detections

### PTP Synchronization
- Use hardware timestamping when available
- Configure appropriate PTP domain and priority
- Monitor PTP offset and jitter

### Network Configuration
- Ensure QoS settings for PTP traffic
- Configure switch ports for low latency
- Monitor network jitter and packet loss

## Security Considerations

### User Permissions
- Run services as dedicated `ptpping` user
- Limit access to audio and PTP devices
- Use appropriate file permissions

### Network Security
- Restrict InfluxDB and Grafana access
- Use API tokens instead of passwords
- Configure firewall rules appropriately

### System Security
- Keep system packages updated
- Monitor service logs for anomalies
- Use secure configuration files

## Monitoring and Maintenance

### Health Checks
```bash
# Check service health
sudo systemctl is-active ptpping-*

# Monitor resource usage
sudo systemctl status ptpping-* --no-pager -l

# Check log rotation
sudo logrotate -d /etc/logrotate.d/ptpping
```

### Data Retention
- Configure InfluxDB retention policies
- Monitor disk usage for time-series data
- Archive old data as needed

### Updates
- Test updates in staging environment
- Backup configuration and data before updates
- Follow semantic versioning for releases

## Support

For issues and questions:
- Check the troubleshooting section above
- Review system logs and PTPPing logs
- Open an issue on GitHub
- Check the FAQ in the main README

## Next Steps

After successful installation:
1. Configure your network switches for PTP
2. Set up InfluxDB and Grafana
3. Deploy PTPPing to all workstations
4. Monitor and tune performance
5. Set up alerting for latency issues
