#!/bin/bash
# Ubuntu 22.04 一键安装脚本

echo "=== Mininet GUI项目 Ubuntu 22.04 安装脚本 ==="
echo "此脚本适用于纯净的Ubuntu 22.04系统"
echo ""

# 检查是否为Ubuntu 22.04
if ! grep -q "Ubuntu 22.04" /etc/os-release; then
    echo "⚠️  警告：此脚本专为Ubuntu 22.04设计，当前系统可能不适用"
    read -p "是否继续？(y/N): " -n 1 -r
echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 更新系统
echo "📦 更新系统..."
sudo apt update

# 安装系统依赖
echo "🔧 安装系统依赖..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-tk \
    python3-dbus \
    dbus-x11 \
    mininet \
    openvswitch-switch \
    tmux \
    xterm \
    gnome-terminal \
    net-tools \
    iproute2 \
    git

# 可选：安装其他终端（增强兼容性）
echo "🖥️  安装额外终端（可选）..."
sudo apt install -y konsole xfce4-terminal terminator

# 安装Python依赖
echo "🐍 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    sudo pip3 install -r requirements.txt
else
    sudo pip3 install networkx matplotlib dbus-python
fi

# 拉取mntpp
cd ~
git clone https://github.com/JediXu/mntpp/mntpp.git
cd mntpp

# 配置权限
echo "🔑 配置权限..."
sudo usermod -aG sudo $USER
sudo systemctl enable openvswitch-switch
sudo systemctl start openvswitch-switch

# 验证安装
echo "✅ 验证安装..."
python3 -c "import tkinter; print('Tkinter: OK')" 2>/dev/null || echo "❌ Tkinter: 失败"
python3 -c "import networkx; print('NetworkX: OK')" 2>/dev/null || echo "❌ NetworkX: 失败"
python3 -c "import matplotlib; print('Matplotlib: OK')" 2>/dev/null || echo "❌ Matplotlib: 失败"

# 运行权限检查脚本
if [ -f "scripts/check_install.py" ]; then
    echo ""
    echo "=== 运行环境检查 ==="
    python3 scripts/check_install.py
fi

echo ""
echo "=== 安装完成 ==="
echo "✅ 所有依赖已成功安装"
echo ""
echo "使用方法:"
echo "  1. 重新登录或重启系统使权限生效"
echo "  2. 运行: ./run_mntpp.sh"
echo "  3. 或运行: sudo python3 mntpp.py"
echo ""
echo "验证安装:"
echo "  python3 scripts/quick_verify.py    # 快速验证"
echo "  python3 scripts/verify_environment.py  # 详细验证"
echo ""
echo "运行快速验证..."
sleep 2
python3 scripts/quick_verify.py
