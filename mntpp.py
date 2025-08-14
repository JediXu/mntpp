#!/usr/bin/env python3
"""
Mininet网络拓扑控制器 - 主程序入口
"""

import sys
import os
import logging
import argparse

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend_api import BackendAPI
    BACKEND_AVAILABLE = True
    logging.info("Backend modules loaded successfully")
except ImportError as e:
    BACKEND_AVAILABLE = False
    logging.warning(f"Backend modules not available: {e}")

try:
    import gui
    GUI_AVAILABLE = True
    logging.info("GUI modules loaded successfully")
except ImportError as e:
    GUI_AVAILABLE = False
    logging.warning(f"GUI modules not available: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mininet_controller.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """检查系统依赖"""
    logger.info("检查系统依赖...")
    
    dependencies = {
        'mininet': 'which mn',
        'ovs-vsctl': 'which ovs-vsctl',
        'ovs-ofctl': 'which ovs-ofctl',
        'tmux': 'which tmux',
        'python3-tk': 'python3 -c "import tkinter"'
    }
    
    missing = []
    for name, cmd in dependencies.items():
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode != 0:
            missing.append(name)
            logger.warning(f"缺少依赖: {name}")
        else:
            logger.info(f"✓ {name} 已安装")
    
    if missing:
        logger.error(f"缺少依赖项: {', '.join(missing)}")
        return False
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Mininet网络拓扑控制器')
    parser.add_argument('--check', action='store_true', help='检查依赖')
    parser.add_argument('--cli', action='store_true', help='命令行模式')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.check:
        if check_dependencies():
            print("所有依赖项已安装，可以正常运行程序")
        else:
            print("请安装缺失的依赖项")
            sys.exit(1)
        return
    
    if args.cli:
        if not BACKEND_AVAILABLE:
            print("后端模块不可用，无法启动CLI模式")
            sys.exit(1)
        
        print("启动CLI模式...")
        try:
            from backend_api import BackendAPI
            backend_api = BackendAPI()
            result = backend_api.start_experiment()
            if result['success']:
                print("实验启动成功")
                input("按Enter键停止实验...")
                backend_api.stop_experiment()
            else:
                print(f"实验启动失败: {result.get('error', '未知错误')}")
        except Exception as e:
            print(f"启动CLI失败: {e}")
            sys.exit(1)
    else:
        if not GUI_AVAILABLE:
            print("GUI模块不可用")
            sys.exit(1)
        
        print("启动GUI模式...")
        try:
            import gui
            gui.main()
        except Exception as e:
            print(f"启动GUI失败: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()