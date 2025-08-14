#!/usr/bin/env python3
"""
OVS控制器
执行流表下发和清除操作
"""

import subprocess
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class OVSController:
    def __init__(self):
        self.executed_commands = []
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """执行单个OVS命令"""
        try:
            logger.info(f"Executing: {command}")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            execution_result = {
                'command': command,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
            
            if result.returncode == 0:
                logger.debug(f"Command executed successfully: {command}")
            else:
                logger.error(f"Command failed: {command}, Error: {result.stderr}")
            
            self.executed_commands.append(execution_result)
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            error_result = {
                'command': command,
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }
            self.executed_commands.append(error_result)
            return error_result
    
    def execute_commands(self, commands: List[str]) -> List[Dict[str, Any]]:
        """执行多个OVS命令"""
        results = []
        
        for command in commands:
            result = self.execute_command(command)
            results.append(result)
            
            # 如果某个命令失败，可以选择停止或继续
            if not result['success']:
                logger.warning(f"Command failed, continuing with next commands...")
        
        return results
    
    def add_flow(self, switch: str, match: str, actions: str, priority: int = 1000) -> Dict[str, Any]:
        """添加流表规则"""
        command = f"sudo ovs-ofctl add-flow {switch} '{match},priority={priority},{actions}'"
        return self.execute_command(command)
    
    def delete_flows(self, switch: str, match: str = None) -> Dict[str, Any]:
        """删除流表规则"""
        if match:
            command = f"sudo ovs-ofctl del-flows {switch} '{match}'"
        else:
            command = f"sudo ovs-ofctl del-flows {switch}"
        return self.execute_command(command)
    
    def dump_flows(self, switch: str) -> Dict[str, Any]:
        """转储交换机的流表"""
        command = f"sudo ovs-ofctl dump-flows {switch}"
        return self.execute_command(command)
    
    def dump_ports(self, switch: str) -> Dict[str, Any]:
        """转储交换机的端口信息"""
        command = f"sudo ovs-ofctl show {switch}"
        return self.execute_command(command)
    
    def get_switch_stats(self, switch: str) -> Dict[str, Any]:
        """获取交换机的统计信息"""
        command = f"sudo ovs-ofctl dump-aggregate {switch}"
        return self.execute_command(command)
    
    def list_switches(self) -> Dict[str, Any]:
        """列出所有OVS交换机"""
        command = "sudo ovs-vsctl list-br"
        return self.execute_command(command)
    
    def get_port_stats(self, switch: str) -> Dict[str, Any]:
        """获取端口统计信息"""
        command = f"sudo ovs-ofctl dump-ports {switch}"
        return self.execute_command(command)
    
    def install_flow_rules(self, flow_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """安装流表规则列表"""
        commands = []
        
        for rule in flow_rules:
            switch = rule['switch']
            in_port = rule.get('in_port', 1)
            out_port = rule.get('out_port', 2)
            priority = rule.get('priority', 1000)
            
            # 构建匹配规则
            match = f"in_port={in_port}"
            if 'eth_src' in rule:
                match += f",dl_src={rule['eth_src']}"
            if 'eth_dst' in rule:
                match += f",dl_dst={rule['eth_dst']}"
            if 'ip_src' in rule:
                match += f",nw_src={rule['ip_src']}"
            if 'ip_dst' in rule:
                match += f",nw_dst={rule['ip_dst']}"
            
            actions = f"output:{out_port}"
            
            command = f"sudo ovs-ofctl add-flow {switch} '{match},priority={priority},{actions}'"
            commands.append(command)
        
        return self.execute_commands(commands)
    
    def clear_all_flows(self, switches: List[str]) -> List[Dict[str, Any]]:
        """清除所有交换机的流表"""
        commands = [f"sudo ovs-ofctl del-flows {switch}" for switch in switches]
        return self.execute_commands(commands)
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.executed_commands
    
    def clear_execution_history(self):
        """清除执行历史"""
        self.executed_commands.clear()
