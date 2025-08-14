#!/usr/bin/env python3
"""
Mininet GUI项目 - 环境完整性验证脚本
全面检查系统依赖、Python包、网络配置和项目完整性
"""

import sys
import os
import subprocess
import platform
import importlib
import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentVerifier:
    def __init__(self):
        self.results = {
            'system': {},
            'python': {},
            'network': {},
            'project': {},
            'permissions': {}
        }
    
    def check_system_commands(self):
        """检查系统命令可用性"""
        logger.info("检查系统命令...")
        
        commands = {
            'python3': ['python3', '--version'],
            'ovs-vsctl': ['ovs-vsctl', '--version'],
            'ovs-ofctl': ['ovs-ofctl', '--version'],
            'tmux': ['tmux', '-V'],
            'xterm': ['which', 'xterm'],
            'gnome-terminal': ['which', 'gnome-terminal'],
            'netstat': ['which', 'netstat'],
            'ip': ['which', 'ip'],
            'sudo': ['which', 'sudo']
        }
        
        for cmd, test_cmd in commands.items():
            try:
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    if 'which' in test_cmd[0]:
                        # 使用which命令检查存在性
                        self.results['system'][cmd] = {'status': 'ok', 'version': '已安装'}
                        logger.info(f"✅ {cmd}: 已安装")
                    else:
                        # 获取版本信息
                        version = result.stdout.strip().split('\n')[0]
                        self.results['system'][cmd] = {'status': 'ok', 'version': version}
                        logger.info(f"✅ {cmd}: {version}")
                else:
                    self.results['system'][cmd] = {'status': 'missing', 'message': '命令未找到'}
                    logger.error(f"❌ {cmd}: 命令未找到")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.results['system'][cmd] = {'status': 'missing', 'message': '命令未找到'}
                logger.error(f"❌ {cmd}: 命令未找到")
        
        # 单独检查Mininet
        try:
            result = subprocess.run(['mn', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.results['system']['mininet'] = {'status': 'ok', 'version': version}
                logger.info(f"✅ mininet: {version}")
            else:
                self.results['system']['mininet'] = {'status': 'missing', 'message': 'Mininet不可用'}
                logger.error(f"❌ mininet: Mininet不可用")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.results['system']['mininet'] = {'status': 'missing', 'message': 'Mininet未安装'}
            logger.error(f"❌ mininet: Mininet未安装")
    
    def check_python_packages(self):
        """检查Python包"""
        logger.info("检查Python包...")
        
        packages = {
            'tkinter': None,
            'networkx': 'networkx',
            'matplotlib': 'matplotlib',
            'matplotlib.pyplot': 'matplotlib.pyplot',
            'dbus': 'dbus',
            'json': 'json',
            'logging': 'logging',
            'subprocess': 'subprocess',
            'os': 'os',
            'sys': 'sys',
            'platform': 'platform',
            'pathlib': 'pathlib'
        }
        
        for package_name, import_name in packages.items():
            try:
                if package_name == 'tkinter':
                    # 特殊处理tkinter
                    import tkinter
                    import tkinter.messagebox
                    import tkinter.filedialog
                    self.results['python'][package_name] = {
                        'status': 'ok',
                        'version': f"Python {sys.version}"
                    }
                    logger.info(f"✅ tkinter: GUI支持正常")
                else:
                    module = importlib.import_module(package_name)
                    if hasattr(module, '__version__'):
                        version = module.__version__
                    else:
                        version = "内置模块"
                    self.results['python'][package_name] = {'status': 'ok', 'version': version}
                    logger.info(f"✅ {package_name}: {version}")
            except ImportError as e:
                self.results['python'][package_name] = {'status': 'missing', 'message': str(e)}
                logger.error(f"❌ {package_name}: {e}")
    
    def check_network_services(self):
        """检查网络服务状态"""
        logger.info("检查网络服务...")
        
        # 检查OpenVSwitch
        try:
            result = subprocess.run(['systemctl', 'is-active', 'openvswitch-switch'], 
                                  capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                self.results['network']['openvswitch'] = {'status': 'ok', 'message': '运行中'}
                logger.info("✅ OpenVSwitch: 运行中")
            else:
                self.results['network']['openvswitch'] = {'status': 'stopped', 'message': '未运行'}
                logger.warning("⚠️  OpenVSwitch: 未运行")
        except Exception as e:
            self.results['network']['openvswitch'] = {'status': 'error', 'message': str(e)}
            logger.error(f"❌ OpenVSwitch检查失败: {e}")
        
        # 检查网络接口
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = [line for line in result.stdout.split('\n') if 'ovs' in line.lower() or 'eth' in line.lower()]
            self.results['network']['interfaces'] = {'status': 'ok', 'count': len(interfaces)}
            logger.info(f"✅ 网络接口: 发现{len(interfaces)}个接口")
        except Exception as e:
            self.results['network']['interfaces'] = {'status': 'error', 'message': str(e)}
            logger.error(f"❌ 网络接口检查失败: {e}")
    
    def check_project_structure(self):
        """检查项目结构完整性"""
        logger.info("检查项目结构...")
        
        project_root = Path(__file__).parent.parent
        required_files = [
            'mntpp.py',
            'backend_api.py',
            'gui.py',
            'requirements.txt',
            'backend/__init__.py',
            'backend/mininet_manager.py',
            'backend/tmux_manager.py',
            'backend/topology_graph.py',
            'backend/path_to_flow.py',
            'backend/ovs_controller.py',
            'backend/monitor.py'
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                self.results['project'][file_path] = {'status': 'ok', 'size': full_path.stat().st_size}
                logger.info(f"✅ {file_path}: {full_path.stat().st_size}字节")
            else:
                self.results['project'][file_path] = {'status': 'missing', 'message': '文件不存在'}
                logger.error(f"❌ {file_path}: 文件不存在")
    
    def check_permissions(self):
        """检查权限配置"""
        logger.info("检查权限配置...")
        
        # 检查sudo权限
        try:
            result = subprocess.run(['sudo', '-n', 'true'], capture_output=True)
            if result.returncode == 0:
                self.results['permissions']['sudo'] = {'status': 'ok', 'message': '无需密码'}
                logger.info("✅ sudo: 无需密码验证")
            else:
                self.results['permissions']['sudo'] = {'status': 'password', 'message': '需要密码'}
                logger.warning("⚠️  sudo: 需要密码验证")
        except Exception as e:
            self.results['permissions']['sudo'] = {'status': 'error', 'message': str(e)}
            logger.error(f"❌ sudo权限检查失败: {e}")
        
        # 检查当前用户组
        try:
            groups = subprocess.run(['groups'], capture_output=True, text=True).stdout.strip()
            if 'sudo' in groups:
                self.results['permissions']['groups'] = {'status': 'ok', 'message': '在sudo组'}
                logger.info("✅ 用户组: 在sudo组")
            else:
                self.results['permissions']['groups'] = {'status': 'warning', 'message': '不在sudo组'}
                logger.warning("⚠️  用户组: 不在sudo组")
        except Exception as e:
            self.results['permissions']['groups'] = {'status': 'error', 'message': str(e)}
            logger.error(f"❌ 用户组检查失败: {e}")
    
    def check_mininet_functionality(self):
        """检查Mininet功能"""
        logger.info("检查Mininet功能...")
        
        # 检查Mininet是否可用
        try:
            result = subprocess.run(['mn', '--help'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'Usage:' in result.stdout:
                self.results['network']['mininet_available'] = {'status': 'ok', 'message': 'Mininet可用'}
                logger.info("✅ Mininet: 可用")
            else:
                self.results['network']['mininet_available'] = {'status': 'error', 'message': 'Mininet不可用'}
                logger.error("❌ Mininet: 不可用")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.results['network']['mininet_available'] = {'status': 'missing', 'message': 'Mininet未安装'}
            logger.error("❌ Mininet: 未安装")
        except Exception as e:
            self.results['network']['mininet_available'] = {'status': 'error', 'message': str(e)}
            logger.error(f"❌ Mininet: 检查异常: {e}")
        
        # 如需测试，请手动运行：sudo mn --test pingall
    
    def generate_report(self):
        """生成验证报告"""
        print("\n" + "="*60)
        print("环境完整性验证报告")
        print("="*60)
        
        total_checks = 0
        passed_checks = 0
        
        for category, checks in self.results.items():
            print(f"\n{category.upper()}:")
            for item, result in checks.items():
                total_checks += 1
                if result['status'] == 'ok':
                    passed_checks += 1
                    print(f"  ✅ {item}: {result.get('version', '正常')}")
                elif result['status'] == 'warning':
                    print(f"  ⚠️  {item}: {result.get('message', '警告')}")
                else:
                    print(f"  ❌ {item}: {result.get('message', '失败')}")
        
        print(f"\n{'='*60}")
        print(f"总结: {passed_checks}/{total_checks} 项检查通过")
        
        if passed_checks == total_checks:
            print("🎉 环境完整，可以正常运行项目")
            return True
        else:
            print("⚠️  环境不完整，请修复上述问题")
            return False
    
    def save_report(self):
        """保存详细报告到文件"""
        report_file = Path(__file__).parent.parent / 'environment_report.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"详细报告已保存到: {report_file}")

def main():
    """主函数"""
    print("Mininet GUI项目 - 环境完整性验证")
    print("="*50)
    
    verifier = EnvironmentVerifier()
    
    # 执行各项检查
    verifier.check_system_commands()
    verifier.check_python_packages()
    verifier.check_network_services()
    verifier.check_project_structure()
    verifier.check_permissions()
    verifier.check_mininet_functionality()
    
    # 生成报告
    success = verifier.generate_report()
    verifier.save_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())