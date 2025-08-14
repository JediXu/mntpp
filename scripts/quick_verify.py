#!/usr/bin/env python3
"""
Mininet GUI项目 - 快速环境验证
"""

import sys
import os
import subprocess
import importlib

def check_command(cmd):
    """检查命令是否存在"""
    try:
        # 使用which命令检查，避免xterm等命令挂起
        result = subprocess.run(['which', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def check_mininet():
    """专门检查Mininet"""
    try:
        # 直接运行mn --version来验证
        result = subprocess.run(['mn', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def check_package(pkg):
    """检查Python包是否存在"""
    try:
        importlib.import_module(pkg)
        return True
    except ImportError:
        return False

def main():
    print("🔍 Mininet Topo & Path项目 - 快速环境验证")
    print("="*40)
    
    # 系统命令检查
    system_commands = {
        'python3': 'python3 --version',
        'ovs-vsctl': 'ovs-vsctl --version',
        'tmux': 'tmux -V',
        'xterm': 'xterm -version'
    }
    
    print("\n📦 系统命令:")
    
    # 单独检查Mininet
    if check_mininet():
        print("  ✅ mininet")
    else:
        print("  ❌ mininet")
    
    # 检查其他命令
    for cmd, test in system_commands.items():
        if check_command(cmd):
            print(f"  ✅ {cmd}")
        else:
            print(f"  ❌ {cmd}")
    
    # Python包检查
    python_packages = [
        'tkinter',
        'networkx',
        'matplotlib',
        'dbus'
    ]
    
    print("\n🐍 Python包:")
    for pkg in python_packages:
        if check_package(pkg):
            print(f"  ✅ {pkg}")
        else:
            print(f"  ❌ {pkg}")
    
    # 服务状态
    print("\n🔄 服务状态:")
    try:
        result = subprocess.run(['systemctl', 'is-active', 'openvswitch-switch'], 
                              capture_output=True, text=True)
        if result.stdout.strip() == 'active':
            print("  ✅ OpenVSwitch")
        else:
            print("  ❌ OpenVSwitch")
    except:
        print("  ❌ OpenVSwitch检查失败")
    
    # 项目文件
    print("\n📁 项目文件:")
    required_files = [
        'mntpp.py',
        'backend_api.py',
        'gui.py',
        'requirements.txt',
        'backend/mininet_manager.py',
        'backend/tmux_manager.py'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
    
    print("\n" + "="*40)
    print("如需详细验证，运行: python3 scripts/verify_environment.py")

if __name__ == "__main__":
    main()