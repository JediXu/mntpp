#!/usr/bin/env python3
"""
后端主模块
整合所有后端功能，为前端提供统一的接口
"""

import logging
import json
import os
import subprocess
import tempfile
import time
from typing import Dict, List, Any, Optional

# 导入所有后端模块
from backend.mininet_manager import MininetManager
from backend.topology_graph import TopologyGraph
from backend.path_to_flow import PathToFlow
from backend.ovs_controller import OVSController
from backend.monitor import NetworkMonitor
from backend.tmux_manager import TmuxManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BackendAPI:
    """后端API主类，为前端提供统一的接口"""
    
    def __init__(self):
        self.mininet_manager = MininetManager()
        self.topology_graph = TopologyGraph()
        self.path_to_flow = PathToFlow(self.topology_graph)
        self.ovs_controller = OVSController()
        self.monitor = NetworkMonitor()
        
        self.is_experiment_running = False
        self.current_topology = None
        self.active_paths = {}

    def _create_default_simple_py(self):
        """创建默认的simple.py拓扑文件"""
        default_content = '''#!/usr/bin/env python3
"""
默认的简单拓扑示例
包含一个交换机和两个主机
"""

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel

class SimpleTopo(Topo):
    def build(self):
        # 添加交换机
        s1 = self.addSwitch('s1')
        
        # 添加两个主机
        h1 = self.addHost('h1', ip='10.0.0.1')
        h2 = self.addHost('h2', ip='10.0.0.2')
        
        # 添加链路
        self.addLink(h1, s1)
        self.addLink(h2, s1)

def run():
    topo = SimpleTopo()
    net = Mininet(topo=topo)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
'''
        with open('simple.py', 'w') as f:
            f.write(default_content)
    
    # Mininet管理接口
    def start_experiment(self, topology_data: dict = None) -> Dict[str, Any]:
        """启动实验 - 基于拓扑数据结构（统一接口）"""
        try:
            if self.is_experiment_running:
                return {'success': False, 'error': 'Experiment already running'}
            
            if not topology_data:
                return {'success': False, 'error': 'No topology data provided'}
            
            logger.info("Using provided topology data")
            
            # 启动Mininet，使用拓扑数据
            success = self.mininet_manager.start_mininet(topology_data=topology_data)
            
            if success:
                self.is_experiment_running = True
                
                # 立即提取拓扑信息
                if self.topology_graph.extract_topology_from_mininet():
                    self.current_topology = self.topology_graph.get_topology_data()
                
                logger.info("Experiment started successfully with topology data")
                
                # 自动打开CLI窗口
                try:
                    import subprocess
                    import platform
                    import shutil
                    
                    cmd = "sudo tmux attach-session -t mininet_session"
                    
                    def open_terminal_linux():
                        """Linux系统终端打开"""
                        terminals = [
                            ['gnome-terminal', '--', 'bash', '-c', cmd],
                            ['konsole', '-e', 'bash', '-c', cmd],
                            ['xfce4-terminal', '-e', 'bash', '-c', cmd],
                            ['xterm', '-e', cmd],
                            ['terminator', '-e', 'bash', '-c', cmd]
                        ]
                        
                        for terminal_cmd in terminals:
                            try:
                                if shutil.which(terminal_cmd[0]):
                                    subprocess.Popen(terminal_cmd)
                                    logger.info(f"已自动打开Mininet CLI终端({terminal_cmd[0]})")
                                    return True
                            except Exception as e:
                                logger.debug(f"尝试{terminal_cmd[0]}失败: {e}")
                                continue
                        return False
                    
                    def open_terminal_mac():
                        """macOS系统终端打开"""
                        try:
                            apple_script = f'''
                            tell application "Terminal"
                                do script "{cmd}"
                                activate
                            end tell
                            '''
                            subprocess.Popen(['osascript', '-e', apple_script])
                            logger.info("已自动打开Mininet CLI终端(Terminal.app)")
                            return True
                        except Exception as e:
                            logger.debug(f"macOS终端打开失败: {e}")
                            return False
                    
                    if platform.system() == "Linux":
                        if not open_terminal_linux():
                            logger.warning("所有Linux终端尝试失败，请手动执行命令")
                    elif platform.system() == "Darwin":
                        if not open_terminal_mac():
                            logger.warning("macOS终端打开失败，请手动执行命令")
                    else:
                        # Windows或其他系统
                        logger.info("CLI终端自动打开功能在此系统上不可用，请手动执行命令")
                            
                except Exception as cli_e:
                    logger.warning(f"自动打开CLI窗口失败: {cli_e}")
                
                return {
                    'success': True,
                    'message': 'Experiment started with topology data',
                    'topology': self.current_topology,
                    'cli_auto_opened': True
                }
            else:
                return {'success': False, 'error': 'Failed to start Mininet with topology data'}
                
        except Exception as e:
            logger.error(f"Error starting experiment: {e}")
            return {'success': False, 'error': str(e)}

    def stop_experiment(self) -> Dict[str, Any]:
        """停止实验"""
        try:
            if not self.is_experiment_running:
                return {'success': False, 'error': 'No experiment running'}
            
            # 清除所有交换机的流表（只清理交换机，不包括主机）
            switches = [node for node in self.topology_graph.graph.nodes() 
                       if node.startswith('s')]
            if switches:
                self.ovs_controller.clear_all_flows(switches)
            
            # 停止Mininet
            success = self.mininet_manager.stop_mininet()
            
            if success:
                self.is_experiment_running = False
                self.current_topology = None
                self.active_paths.clear()
                
                logger.info("Experiment stopped successfully")
                return {'success': True, 'message': 'Experiment stopped'}
            else:
                return {'success': False, 'error': 'Failed to stop Mininet'}
                
        except Exception as e:
            logger.error(f"Error stopping experiment: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_experiment_status(self) -> Dict[str, Any]:
        """获取实验状态"""
        return {
            'is_running': self.is_experiment_running,
            'topology': self.current_topology,
            'active_paths': list(self.active_paths.keys()),
            'mininet_status': self.mininet_manager.get_status()
        }
    
    # 拓扑管理接口
    def get_topology(self) -> Dict[str, Any]:
        """获取当前拓扑"""
        if not self.is_experiment_running:
            return {'success': False, 'error': 'No experiment running'}
        
        try:
            if self.topology_graph.extract_topology_from_mininet():
                self.current_topology = self.topology_graph.get_topology_data()
                return {
                    'success': True,
                    'topology': self.current_topology
                }
            else:
                return {'success': False, 'error': 'Failed to extract topology'}
                
        except Exception as e:
            logger.error(f"Error getting topology: {e}")
            return {'success': False, 'error': str(e)}
    
    def save_topology(self, filename: str) -> Dict[str, Any]:
        """保存拓扑到文件"""
        try:
            self.topology_graph.save_topology(filename)
            return {'success': True, 'message': f'Topology saved to {filename}'}
        except Exception as e:
            logger.error(f"Error saving topology: {e}")
            return {'success': False, 'error': str(e)}
    
    def load_topology(self, filename: str) -> Dict[str, Any]:
        """从文件加载拓扑"""
        try:
            success = self.topology_graph.load_topology(filename)
            if success:
                self.current_topology = self.topology_graph.get_topology_data()
                return {
                    'success': True,
                    'topology': self.current_topology
                }
            else:
                return {'success': False, 'error': 'Failed to load topology'}
                
        except Exception as e:
            logger.error(f"Error loading topology: {e}")
            return {'success': False, 'error': str(e)}
    
    # 路径管理接口
    def create_path(self, path: List[str], algorithm: str = 'manual') -> Dict[str, Any]:
        """创建路径"""
        try:
            if not self.is_experiment_running:
                return {'success': False, 'error': 'No experiment running'}
            
            # 验证路径
            is_valid, message = self.path_to_flow.validate_path(path)
            if not is_valid:
                return {'success': False, 'error': message}
            
            # 生成路径ID
            path_id = f"path_{path[0]}_{path[-1]}_{len(self.active_paths)}"
            
            # 创建流表规则
            flow_rules = self.path_to_flow.create_flow_rules(path, path_id)
            if not flow_rules:
                return {'success': False, 'error': 'Failed to create flow rules'}
            
            # 生成OVS命令
            commands = self.path_to_flow.generate_ovs_commands(flow_rules)
            if not commands:
                return {'success': False, 'error': 'Failed to generate commands'}
            
            # 执行命令
            results = self.ovs_controller.execute_commands(commands)
            
            # 检查执行结果
            failed_commands = [r for r in results if not r['success']]
            if failed_commands:
                return {
                    'success': False,
                    'error': f'Failed to install {len(failed_commands)} flow rules',
                    'failed_commands': failed_commands
                }
            
            # 存储路径信息
            self.active_paths[path_id] = {
                'path': path,
                'flow_rules': flow_rules,
                'algorithm': algorithm
            }
            
            logger.info(f"Path created: {path} (ID: {path_id})")
            return {
                'success': True,
                'path_id': path_id,
                'path': path,
                'flow_rules': len(flow_rules)
            }
            
        except Exception as e:
            logger.error(f"Error creating path: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_path(self, path_id: str) -> Dict[str, Any]:
        """删除路径"""
        try:
            if path_id not in self.active_paths:
                return {'success': False, 'error': 'Path not found'}
            
            # 生成删除命令
            commands = self.path_to_flow.delete_flow_rules(path_id)
            
            # 执行命令
            results = self.ovs_controller.execute_commands(commands)
            
            # 检查执行结果
            failed_commands = [r for r in results if not r['success']]
            if failed_commands:
                return {
                    'success': False,
                    'error': f'Failed to delete {len(failed_commands)} flow rules',
                    'failed_commands': failed_commands
                }
            
            # 移除路径信息
            path_info = self.active_paths.pop(path_id)
            
            logger.info(f"Path deleted: {path_id}")
            return {
                'success': True,
                'path_id': path_id,
                'path': path_info['path']
            }
            
        except Exception as e:
            logger.error(f"Error deleting path: {e}")
            return {'success': False, 'error': str(e)}
    
    def calculate_path(self, src: str, dst: str, algorithm: str = 'dijkstra') -> Dict[str, Any]:
        """计算路径"""
        try:
            if not self.is_experiment_running:
                return {'success': False, 'error': 'No experiment running'}
            
            path = self.path_to_flow.calculate_path(src, dst, algorithm)
            if path:
                return {
                    'success': True,
                    'path': path,
                    'algorithm': algorithm
                }
            else:
                return {'success': False, 'error': 'Failed to calculate path'}
                
        except Exception as e:
            logger.error(f"Error calculating path: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_paths(self) -> Dict[str, Any]:
        """获取所有活跃路径"""
        return {
            'success': True,
            'paths': self.active_paths
        }
    
    # 监控接口
    def start_monitoring(self, switches: List[str] = None, interval: int = 5) -> Dict[str, Any]:
        """开始监控"""
        try:
            if not switches:
                switches = list(self.topology_graph.graph.nodes())
            
            self.monitor.start_monitoring(switches, interval)
            return {'success': True, 'message': f'Started monitoring {len(switches)} switches'}
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控"""
        try:
            self.monitor.stop_monitoring()
            return {'success': True, 'message': 'Stopped monitoring'}
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_monitoring_data(self) -> Dict[str, Any]:
        """获取监控数据"""
        try:
            data = self.monitor.collect_all_stats()
            summary = self.monitor.get_monitoring_summary()
            
            return {
                'success': True,
                'data': data,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring data: {e}")
            return {'success': False, 'error': str(e)}
    
    def save_monitoring_data(self, filename: str) -> Dict[str, Any]:
        """保存监控数据"""
        try:
            self.monitor.save_monitoring_data(filename)
            return {'success': True, 'message': f'Monitoring data saved to {filename}'}
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
            return {'success': False, 'error': str(e)}
    
    # 系统管理接口
    def attach_to_cli(self) -> Dict[str, Any]:
        """附加到Mininet CLI"""
        try:
            if not self.is_experiment_running:
                return {'success': False, 'error': 'No experiment running'}
            
            # 使用MininetManager的attach_to_cli方法
            success, cmd_or_error = self.mininet_manager.attach_to_cli()
            
            if success:
                return {
                    'success': True,
                    'message': 'Use the following command to attach to CLI',
                    'command': cmd_or_error
                }
            else:
                return {'success': False, 'error': cmd_or_error}
                
        except Exception as e:
            logger.error(f"Error attaching to CLI: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            # 获取交换机列表
            switches_result = self.ovs_controller.list_switches()
            switches = []
            if switches_result['success']:
                switches = [s.strip() for s in switches_result['stdout'].split('\n') if s.strip()]
            
            return {
                'success': True,
                'switches': switches,
                'experiment_running': self.is_experiment_running,
                'active_paths': len(self.active_paths)
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {'success': False, 'error': str(e)}

    def get_host_stats(self, host_name: str) -> Dict[str, Any]:
        """获取单个主机的接口统计信息 (TMUX-Compatible)"""
        if not self.is_experiment_running:
            return {'success': False, 'error': 'Experiment not running'}

        tmp_file = None
        try:
            # Create a temporary file to store the output
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                tmp_file = f.name

            # Command to be executed in the tmux session
            interface = f"{host_name}-eth0"
            command_to_run = f"{host_name} ip -s link show {interface} > {tmp_file}"

            # Send the command to the tmux session
            tmux_cmd = f"sudo tmux send-keys -t mininet_session '{command_to_run}' Enter"
            subprocess.run(tmux_cmd, shell=True, check=True)

            # Wait for the command to execute and write to the file
            time.sleep(1.5) # This is a fragile but necessary evil with this architecture

            # Read the output from the temporary file
            with open(tmp_file, 'r') as f:
                output = f.read()

            if not output:
                return {'success': False, 'error': f'Could not get stats for {host_name}. Is the host name correct?'}

            # We can reuse the parser logic from monitor.py here
            stats = self.monitor._parse_ip_stats(output) # Assuming monitor has the parser
            return {'success': True, 'stats': stats}

        except Exception as e:
            logger.error(f"Error getting stats for host {host_name}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            # Clean up the temporary file
            if tmp_file and os.path.exists(tmp_file):
                os.remove(tmp_file)

# 创建全局后端实例
backend = BackendAPI()

# 导出给前端使用的接口
def start_experiment(topology_data=None):
    """启动实验 - 基于拓扑数据（统一接口）"""
    return backend.start_experiment(topology_data)

def stop_experiment():
    """停止实验（兼容接口）"""
    return backend.stop_experiment()

def get_experiment_status():
    """获取实验状态（兼容接口）"""
    return backend.get_experiment_status()

def get_topology():
    """获取拓扑（兼容接口）"""
    return backend.get_topology()

def create_path(path, algorithm='manual'):
    """创建路径（兼容接口）"""
    return backend.create_path(path, algorithm)

def delete_path(path_id):
    """删除路径（兼容接口）"""
    return backend.delete_path(path_id)

def calculate_path(src, dst, algorithm='dijkstra'):
    """计算路径（兼容接口）"""
    return backend.calculate_path(src, dst, algorithm)

def get_system_info():
    """获取系统信息（兼容接口）"""
    return backend.get_system_info()

def get_host_stats(host_name):
    """获取主机统计信息（兼容接口）"""
    return backend.get_host_stats(host_name)

def attach_to_cli():
    """附加到CLI（兼容接口）"""
    return backend.attach_to_cli()

def start_monitoring(switches=None, interval=5):
    return backend.start_monitoring(switches, interval)

def stop_monitoring():
    return backend.stop_monitoring()

def get_monitoring_data():
    return backend.get_monitoring_data()

def save_topology(filename):
    return backend.save_topology(filename)

def load_topology(filename):
    return backend.load_topology(filename)

def save_monitoring_data(filename):
    return backend.save_monitoring_data(filename)

if __name__ == "__main__":
    # 测试后端功能
    print("Backend API loaded successfully")
    print("Available functions:")
    print("- start_experiment()")
    print("- stop_experiment()")
    print("- get_topology()")
    print("- create_path()")
    print("- delete_path()")
    print("- get_monitoring_data()")
    print("- attach_to_cli()")
    print("- get_system_info()")
    print("- save_topology()")
    print("- load_topology()")
    print("- save_monitoring_data()")
    