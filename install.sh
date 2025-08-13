#!/bin/bash
# PTPPing Installation Script
# This script installs PTPPing and its dependencies on Ubuntu/Debian systems

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_error "Cannot detect OS version"
    exit 1
fi

print_status "Detected OS: $OS $VER"

# Update package list
print_status "Updating package list..."
apt update

# Install system dependencies
print_status "Installing system dependencies..."

# Core dependencies
apt install -y python3 python3-pip python3-venv

# Audio dependencies
apt install -y vlc alsa-utils pulseaudio

# PTP dependencies
apt install -y linuxptp ptp4l phc2sys

# InfluxDB client
apt install -y influxdb-client

# Grafana (optional, can be installed separately)
if command -v grafana-server &> /dev/null; then
    print_status "Grafana is already installed"
else
    print_warning "Grafana not found. You may want to install it separately for dashboard visualization."
fi

# Create PTPPing user and group
print_status "Creating PTPPing user and group..."
if ! getent group ptpping > /dev/null 2>&1; then
    groupadd ptpping
fi

if ! getent passwd ptpping > /dev/null 2>&1; then
    useradd -r -g ptpping -s /bin/false ptpping
fi

# Add user to required groups
usermod -a -G audio ptpping
usermod -a -G ptp ptpping

# Create directories
print_status "Creating directories..."
mkdir -p /opt/ptpping
mkdir -p /etc/ptpping
mkdir -p /var/log/ptpping
mkdir -p /var/lib/ptpping

# Copy files
print_status "Copying PTPPing files..."
cp -r . /opt/ptpping/
chown -R ptpping:ptpping /opt/ptpping
chmod +x /opt/ptpping/ptpping.py

# Copy configuration
if [[ ! -f /etc/ptpping/config.toml ]]; then
    cp config.toml.example /etc/ptpping/config.toml
    chown ptpping:ptpping /etc/ptpping/config.toml
    print_warning "Please edit /etc/ptpping/config.toml with your configuration"
else
    print_status "Configuration file already exists"
fi

# Copy systemd services
print_status "Installing systemd services..."
cp systemd/*.service /etc/systemd/system/
systemctl daemon-reload

# Install Python dependencies
print_status "Installing Python dependencies..."
cd /opt/ptpping
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Create virtual environment (optional but recommended)
print_status "Creating Python virtual environment..."
python3 -m venv /opt/ptpping/venv
source /opt/ptpping/venv/bin/activate
pip install -r requirements.txt

# Update service files to use virtual environment
sed -i 's|/usr/bin/python3|/opt/ptpping/venv/bin/python|g' /etc/systemd/system/ptpping-*.service

# Set permissions
print_status "Setting permissions..."
chown -R ptpping:ptpping /var/log/ptpping
chown -R ptpping:ptpping /var/lib/ptpping

# Enable services (but don't start them yet)
print_status "Enabling systemd services..."
systemctl enable ptpping-generator.service
systemctl enable ptpping-capture.service
systemctl enable ptpping-dashboard.service

# Create ALSA loopback device
print_status "Setting up ALSA loopback device..."
if ! modprobe snd-aloop; then
    print_warning "Failed to load ALSA loopback module. Audio loopback may not work."
fi

# Add ALSA loopback to modules list
if ! grep -q "snd-aloop" /etc/modules; then
    echo "snd-aloop" >> /etc/modules
fi

# Create udev rules for audio devices
print_status "Creating udev rules..."
cat > /etc/udev/rules.d/99-ptpping-audio.rules << EOF
# PTPPing audio device rules
KERNEL=="snd_aloop", GROUP="audio", MODE="0660"
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

print_status "Installation completed successfully!"

echo
print_status "Next steps:"
echo "1. Edit /etc/ptpping/config.toml with your configuration"
echo "2. Ensure PTP is synchronized: systemctl status ptp4l"
echo "3. Start services:"
echo "   - systemctl start ptpping-generator.service"
echo "   - systemctl start ptpping-capture.service"
echo "   - systemctl start ptpping-dashboard.service"
echo
echo "4. Check service status: systemctl status ptpping-*"
echo "5. View logs: journalctl -u ptpping-* -f"
echo
print_warning "Remember to configure your network switches and ensure PTP synchronization is working properly."
