#!/bin/bash
# Ubuntu 22.04 一键安装脚本 for Mininet PoP (PyQt Edition)

echo "=== Mininet PoP (PyQt Edition) Ubuntu 22.04 Installation Script ==="
echo "This script is for a clean Ubuntu 22.04 system."
echo ""

# Check for Ubuntu 22.04
if ! grep -q "Ubuntu 22.04" /etc/os-release; then
    echo "⚠️  Warning: This script is designed for Ubuntu 22.04. Your system may not be compatible."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system..."
sudo apt-get update

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-pyqt6 \
    mininet \
    openvswitch-switch \
    tmux \
    net-tools \
    iproute2

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
else
    echo "requirements.txt not found. Installing core dependencies..."
    pip3 install networkx PyQt6
fi

# Configure permissions
echo "🔑 Configuring permissions..."
sudo usermod -aG sudo $USER
sudo systemctl enable openvswitch-switch
sudo systemctl start openvswitch-switch

# Verify installation
echo "✅ Verifying installation..."
python3 -c "import PyQt6; print('PyQt6: OK')" 2>/dev/null || echo "❌ PyQt6: Failed"
python3 -c "import networkx; print('NetworkX: OK')" 2>/dev/null || echo "❌ NetworkX: Failed"
mn --version > /dev/null 2>&1 && echo "Mininet: OK" || echo "Mininet: Failed"
ovs-vsctl --version > /dev/null 2>&1 && echo "Open vSwitch: OK" || echo "Open vSwitch: Failed"


echo ""
echo "=== Installation Complete ==="
echo "✅ All dependencies should be installed."
echo ""
echo "Usage:"
echo "  1. Log out and log back in, or reboot for group permissions to take effect."
echo "  2. Run: python3 mntpp.py"
echo ""
echo "NOTE: This application requires a graphical desktop environment to run."
echo ""