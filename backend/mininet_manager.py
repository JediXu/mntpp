#!/usr/bin/env python3
"""
Mininet Manager - 管理Mininet网络的启动和停止
"""

import os
import json
import subprocess
import time
import tempfile
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)
from pathlib import Path

class MininetManager:
    def __init__(self):
        self.session_name = "mininet_session"
        self.topology_script_path = None
        self.process = None
        
    def start_mininet(self, topology_file=None, topology_data=None):
        """启动Mininet网络 - 支持直接从拓扑数据启动"""
        try:
            # 清理之前的会话
            self.stop_mininet()
            
            # 清理标志文件
            for f in ['/tmp/mininet_ready', '/tmp/mininet_error']:
                if os.path.exists(f):
                    os.remove(f)
            
            # 生成拓扑脚本
            script_path = self._generate_mininet_script(topology_data, topology_file)
            if not script_path:
                logger.error("无法生成拓扑脚本")
                return False
            
            # 创建tmux会话并启动Mininet
            logger.info("启动Mininet网络...")
            
            # 确保tmux会话被正确创建
            subprocess.run(f"sudo -E tmux new-session -d -s {self.session_name}", 
                         shell=True, check=True)
            
            # 等待会话创建
            time.sleep(2)
            
            # 在会话中运行Mininet CLI - 使用生成的拓扑脚本
            if topology_data or topology_file:
                # 使用自定义拓扑脚本
                cmd = f"sudo -E tmux send-keys -t {self.session_name} " \
                      f"'python3 {script_path}' Enter"
            else:
                # 使用默认线性拓扑
                cmd = f"sudo -E tmux send-keys -t {self.session_name} " \
                      f"'mn --topo=linear,2' Enter"
            subprocess.run(cmd, shell=True, check=True)
            
            # 等待网络启动
            logger.info("等待网络启动...")
            if self._wait_for_mininet_ready(timeout=20):
                logger.info("Mininet网络启动成功")
                return True
            else:
                # 检查错误
                if os.path.exists('/tmp/mininet_error'):
                    with open('/tmp/mininet_error', 'r') as f:
                        error = f.read()
                    logger.error(f"Mininet启动失败: {error}")
                else:
                    logger.error("Mininet启动超时")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"启动命令失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启动Mininet时出错: {e}")
            return False
            
    def stop_mininet(self):
        """停止Mininet网络 - 使用系统级清理"""
        try:
            # 1. 停止tmux会话
            subprocess.run(f"sudo tmux kill-session -t {self.session_name}", 
                         shell=True, capture_output=True)
            
            # 2. 使用mn -c进行完整清理
            subprocess.run("sudo mn -c", shell=True, capture_output=True)
            
            # 3. 清理残留的veth接口
            cleanup_cmd = """
            sudo ip link show | grep -o 's[0-9]\+-eth[0-9]\+' | sort -u | xargs -I {} sudo ip link delete {}
            """
            subprocess.run(cleanup_cmd, shell=True, capture_output=True)
            
            # 4. 清理标志文件
            for flag_path in ['/tmp/mininet_ready', '/tmp/mininet_error']:
                if os.path.exists(flag_path):
                    try:
                        os.remove(flag_path)
                    except:
                        pass
            
            # 5. 清理OVS残留配置
            subprocess.run("sudo ovs-vsctl --if-exists del-br s1", shell=True, capture_output=True)
            subprocess.run("sudo ovs-vsctl --if-exists del-br s2", shell=True, capture_output=True)
            subprocess.run("sudo ovs-vsctl --if-exists del-br s3", shell=True, capture_output=True)
            
            logger.info("Mininet网络已完全停止并清理")
            return True, "Mininet网络已完全停止并清理"
            
        except Exception as e:
            logger.error(f"停止Mininet时出错: {e}")
            return False, f"停止错误: {str(e)}"
    
    def attach_to_cli(self):
        """附加到Mininet CLI会话"""
        try:
            # 检查会话是否存在
            result = subprocess.run(f"sudo tmux list-sessions | grep {self.session_name}", 
                                  shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, "Mininet会话不存在"
            
            # 提供附加命令
            cmd = f"sudo tmux attach-session -t {self.session_name}"
            return True, cmd
            
        except Exception as e:
            return False, f"附加会话错误: {str(e)}"

    def _generate_mininet_script(self, topology_data=None, topology_file=None):
        """生成Mininet拓扑脚本"""
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
            script_path = temp_file.name
            
            # 基础导入
            script = '''#!/usr/bin/env python3
"""
Mininet拓扑脚本 - 自动生成
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo
import subprocess
import time
import os
import sys

'''
            
            # 添加拓扑类
            script += '''
class MyTopo(Topo):
    def build(self):
        """构建拓扑"""
        # 添加交换机
'''
            
            # 根据拓扑数据生成节点
            if topology_file and os.path.exists(topology_file):
                # 从文件读取拓扑
                with open(topology_file, 'r') as f:
                    topology = json.load(f)
            elif topology_data:
                # 使用提供的拓扑数据
                topology = topology_data
            else:
                # 默认简单拓扑
                topology = {
                    "switches": [{"name": "s1", "dpid": "1"}],
                    "hosts": [
                        {"name": "h1", "ip": "10.0.0.1/24"},
                        {"name": "h2", "ip": "10.0.0.2/24"}
                    ],
                    "links": [
                        {"src": "h1", "dst": "s1"},
                        {"src": "h2", "dst": "s1"}
                    ]
                }
            
            # 添加交换机
            for switch in topology.get('switches', []):
                name = switch['name']
                dpid = switch.get('dpid', '1')
                script += f'        self.addSwitch("{name}", dpid="{dpid}")\n'
            
            # 添加主机
            script += '\n        # 添加主机\n'
            for host in topology.get('hosts', []):
                name = host['name']
                # 支持从host数据中直接获取ip和mac
                ip = host.get('ip', f'10.0.0.{len(topology.get("hosts", [])) + 1}/24')
                mac = host.get('mac')

                mac_param = f', mac="{mac}"' if mac else ''
                script += f'        self.addHost("{name}", ip="{ip}"{mac_param})\n'

            # 添加链路
            script += '\n        # 添加链路\n'
            use_tc_link = any(link.get('bw') is not None or link.get('delay') or link.get('loss') is not None for link in topology.get('links', []))

            for link in topology.get('links', []):
                src = link['src']
                dst = link['dst']

                params = {}
                if link.get('bw') is not None:
                    params['bw'] = link['bw']
                if link.get('delay'):
                    params['delay'] = f"'{link['delay']}'" # Delay is a string
                if link.get('loss') is not None:
                    params['loss'] = link['loss']

                if params:
                    param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                    script += f'        self.addLink("{src}", "{dst}", {param_str})\n'
                else:
                    script += f'        self.addLink("{src}", "{dst}")\n'
            
            # 添加主函数
            script += '''

def run():
    """创建网络并保持运行状态"""
    try:
        setLogLevel('info')
        info('*** Starting Mininet topology...\\n')
        
        # 创建拓扑
        topo = MyTopo()
'''
            if use_tc_link:
                script += "        net = Mininet(topo=topo, controller=None, switch=OVSSwitch, link=TCLink)\n"
            else:
                script += "        net = Mininet(topo=topo, controller=None, switch=OVSSwitch)\n"

            script += '''
        info('*** Starting network\\n')
        net.start()
        
        # 验证交换机创建
        info('*** Verifying switches...\\n')
        if not net.switches:
            raise Exception("No switches created in network")
        
        info('Found {} switches\\n'.format(len(net.switches)))
        
        # 等待OVS交换机就绪
        info('*** Waiting for OVS switches...\\n')
        max_wait = 15
        for switch in net.switches:
            waited = 0
            while waited < max_wait:
                try:
                    result = subprocess.run(['ovs-vsctl', 'list-br'], 
                                        capture_output=True, text=True, timeout=5)
                    if switch.name in result.stdout:
                        info('  ✓ {} is ready\\n'.format(switch.name))
                        break
                except Exception as e:
                    info('  Error checking {}: {}\\n'.format(switch.name, e))
                time.sleep(1)
                waited += 1
            
            if waited >= max_wait:
                info('  ⚠ {} not ready after {}s\\n'.format(switch.name, max_wait))
        
        info('*** Network is ready\\n')
        info('*** Starting CLI...\\n')
        CLI(net)
        
    except Exception as e:
        info('Error: {}\\n'.format(e))
    finally:
        try:
            if 'net' in locals():
                net.stop()
        except:
            pass

if __name__ == '__main__':
    run()
'''
            
            temp_file.write(script)
            temp_file.close()
            
            # 设置可执行权限
            os.chmod(script_path, 0o755)
            
            return script_path
            
        except Exception as e:
            return None
    
    def _wait_for_mininet_ready(self, timeout=20):
        """等待Mininet CLI启动完成 - 基于诊断结果改进"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查tmux会话是否存在
                result = subprocess.run(['sudo', 'tmux', 'list-sessions'], 
                                      capture_output=True, text=True, timeout=3)
                if self.session_name not in result.stdout:
                    logger.warning("tmux会话不存在")
                    return False
                
                # 直接检查CLI提示符
                result = subprocess.run(['sudo', 'tmux', 'capture-pane', 
                                       '-t', self.session_name, '-p'], 
                                      capture_output=True, text=True, timeout=3)
                
                output = result.stdout
                if "mininet>" in output:
                    logger.info("✅ Mininet CLI已启动")
                    
                    # 验证CLI功能
                    subprocess.run(['sudo', 'tmux', 'send-keys', 
                                  '-t', self.session_name, 'nodes', 'Enter'], 
                                  capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['sudo', 'tmux', 'capture-pane', 
                                           '-t', self.session_name, '-p'], 
                                          capture_output=True, text=True, timeout=3)
                    
                    if "available nodes are" in result.stdout:
                        logger.info("✅ Mininet CLI功能正常")
                        return True
                
                # 检查是否有错误信息
                if "Error" in output or "error" in output.lower():
                    logger.error(f"启动错误: {output}")
                    return False
                
            except subprocess.TimeoutExpired:
                logger.warning("命令超时")
            except Exception as e:
                logger.debug(f"等待时出错: {e}")
            
            time.sleep(2)  # 给更多启动时间
        
        logger.error("等待Mininet就绪超时")
        return False
    
    def get_status(self):
        """获取Mininet网络状态"""
        try:
            # 检查tmux会话
            result = subprocess.run(f"sudo tmux list-sessions | grep {self.session_name}", 
                                  shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"running": False, "message": "Mininet未运行"}
            
            # 检查CLI是否就绪
            result = subprocess.run(['sudo', 'tmux', 'capture-pane', 
                                   '-t', self.session_name, '-p'], 
                                  capture_output=True, text=True, timeout=3)
            
            if "mininet>" in result.stdout:
                return {"running": True, "message": "Mininet网络运行正常"}
            else:
                return {"running": True, "message": "Mininet正在启动中"}
            
        except Exception as e:
            return {"running": False, "message": f"状态检查错误: {str(e)}"}
