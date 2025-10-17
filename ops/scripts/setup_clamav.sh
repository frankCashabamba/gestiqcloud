#!/bin/bash
# Setup script for ClamAV antivirus engine
# Run on production servers for malware scanning

set -e

echo "=== ClamAV Installation & Setup ==="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Install ClamAV
case $OS in
    ubuntu|debian)
        echo "Installing ClamAV on Debian/Ubuntu..."
        sudo apt-get update
        sudo apt-get install -y clamav clamav-daemon clamav-freshclam
        ;;
    centos|rhel|fedora)
        echo "Installing ClamAV on RHEL/CentOS/Fedora..."
        sudo yum install -y epel-release
        sudo yum install -y clamav clamav-update clamd
        ;;
    alpine)
        echo "Installing ClamAV on Alpine..."
        sudo apk add --no-cache clamav clamav-daemon freshclam
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

echo ""
echo "ClamAV installed successfully"
echo ""

# Stop services for configuration
echo "Stopping ClamAV services..."
sudo systemctl stop clamav-daemon || true
sudo systemctl stop clamav-freshclam || true

# Update virus definitions
echo ""
echo "Updating virus definitions (this may take a while)..."
sudo freshclam || {
    echo "Warning: freshclam failed, trying alternative..."
    sudo freshclam --daemon-notify=/var/run/clamav/clamd.ctl || true
}

# Configure ClamAV daemon
echo ""
echo "Configuring ClamAV daemon..."

CLAMD_CONF="/etc/clamav/clamd.conf"
if [ ! -f "$CLAMD_CONF" ]; then
    CLAMD_CONF="/etc/clamd.d/scan.conf"
fi

if [ -f "$CLAMD_CONF" ]; then
    # Ensure socket is enabled
    sudo sed -i 's/^#LocalSocket /LocalSocket /' "$CLAMD_CONF" || true
    
    # Increase max file size for imports (default 25MB, set to 32MB)
    if grep -q "^MaxFileSize" "$CLAMD_CONF"; then
        sudo sed -i 's/^MaxFileSize.*/MaxFileSize 32M/' "$CLAMD_CONF"
    else
        echo "MaxFileSize 32M" | sudo tee -a "$CLAMD_CONF"
    fi
    
    # Increase max scan size
    if grep -q "^MaxScanSize" "$CLAMD_CONF"; then
        sudo sed -i 's/^MaxScanSize.*/MaxScanSize 128M/' "$CLAMD_CONF"
    else
        echo "MaxScanSize 128M" | sudo tee -a "$CLAMD_CONF"
    fi
    
    echo "ClamAV daemon configured"
else
    echo "Warning: Could not find clamd.conf"
fi

# Configure freshclam for auto-updates
echo ""
echo "Configuring automatic virus definition updates..."

FRESHCLAM_CONF="/etc/clamav/freshclam.conf"
if [ -f "$FRESHCLAM_CONF" ]; then
    # Enable daemon mode
    if ! grep -q "^Daemon" "$FRESHCLAM_CONF"; then
        echo "Daemon yes" | sudo tee -a "$FRESHCLAM_CONF"
    fi
    
    # Set update frequency (24 checks per day = every hour)
    if grep -q "^Checks" "$FRESHCLAM_CONF"; then
        sudo sed -i 's/^Checks.*/Checks 24/' "$FRESHCLAM_CONF"
    else
        echo "Checks 24" | sudo tee -a "$FRESHCLAM_CONF"
    fi
fi

# Start services
echo ""
echo "Starting ClamAV services..."
sudo systemctl enable clamav-daemon
sudo systemctl enable clamav-freshclam
sudo systemctl start clamav-freshclam
sudo systemctl start clamav-daemon

# Wait for daemon to be ready
echo ""
echo "Waiting for ClamAV daemon to be ready..."
sleep 5

# Test connection
echo ""
echo "Testing ClamAV daemon..."
if command -v clamdscan &> /dev/null; then
    echo "TESTING" | clamdscan - && echo "✓ ClamAV daemon is working" || echo "✗ ClamAV test failed"
else
    echo "clamdscan not found, using clamdtop to check status..."
    sudo systemctl status clamav-daemon --no-pager
fi

# Setup daily update cron (backup to systemd timer)
echo ""
echo "Setting up cron job for virus definition updates..."
CRON_JOB="0 3 * * * /usr/bin/freshclam --quiet"
(crontab -l 2>/dev/null | grep -v freshclam; echo "$CRON_JOB") | crontab -

echo ""
echo "=== ClamAV Setup Complete ==="
echo ""
echo "Configuration:"
echo "  - Daemon socket: /var/run/clamav/clamd.ctl"
echo "  - Max file size: 32MB"
echo "  - Max scan size: 128MB"
echo "  - Updates: Every hour + daily cron at 3 AM"
echo ""
echo "Check status:"
echo "  sudo systemctl status clamav-daemon"
echo "  sudo systemctl status clamav-freshclam"
echo ""
echo "View logs:"
echo "  sudo journalctl -u clamav-daemon -f"
echo ""
