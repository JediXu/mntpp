#!/usr/bin/env python3
"""
网络监控器
用于收集性能数据和监控网络状态
"""

import subprocess
import time
import json
import logging
from typing import Dict, List, Any
from .ovs_controller import OVSController

logger = logging.getLogger(__name__)

class NetworkMonitor:
    def __init__(self):
        self.ovs_controller = OVSController()
        self.monitoring_data = {}
        self.is_monitoring = False
    
    def start_monitoring(self, switches: List[str], interval: int = 5):
        """开始监控网络状态"""
        self.is_monitoring = True
        self.monitoring_data = {
            'switches': switches,
            'interval': interval,
            'start_time': time.time(),
            'data': []
        }
        
        logger.info(f"Started monitoring {len(switches)} switches with {interval}s interval")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        logger.info("Stopped network monitoring")
    
    def collect_switch_stats(self, switch: str) -> Dict[str, Any]:
        """收集交换机统计信息"""
        try:
            stats = {}
            
            # 获取流表统计
            flows_result = self.ovs_controller.dump_flows(switch)
            if flows_result['success']:
                stats['flows'] = self._parse_flow_stats(flows_result['stdout'])
            
            # 获取端口统计
            ports_result = self.ovs_controller.get_port_stats(switch)
            if ports_result['success']:
                stats['ports'] = self._parse_port_stats(ports_result['stdout'])
            
            # 获取聚合统计
            aggregate_result = self.ovs_controller.get_switch_stats(switch)
            if aggregate_result['success']:
                stats['aggregate'] = self._parse_aggregate_stats(aggregate_result['stdout'])
            
            stats['timestamp'] = time.time()
            stats['switch'] = switch
            
            return stats
            
        except Exception as e:
            logger.error(f"Error collecting stats for switch {switch}: {e}")
            return {}
    
    def collect_all_stats(self) -> Dict[str, Any]:
        """收集所有交换机的统计信息"""
        if not self.monitoring_data.get('switches'):
            return {}
        
        all_stats = {
            'timestamp': time.time(),
            'switches': {}
        }
        
        for switch in self.monitoring_data['switches']:
            stats = self.collect_switch_stats(switch)
            if stats:
                all_stats['switches'][switch] = stats
        
        # 保存到监控数据
        if self.is_monitoring:
            self.monitoring_data['data'].append(all_stats)
        
        return all_stats
    
    def _parse_flow_stats(self, flow_output: str) -> List[Dict[str, Any]]:
        """解析流表统计信息"""
        flows = []
        lines = flow_output.strip().split('\n')
        
        for line in lines[1:]:  # 跳过表头
            if line.strip():
                parts = line.split(',')
                flow = {}
                
                for part in parts:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key in ['n_packets', 'n_bytes', 'priority', 'idle_timeout', 'hard_timeout']:
                            try:
                                value = int(value)
                            except ValueError:
                                pass
                        
                        flow[key] = value
                
                if flow:
                    flows.append(flow)
        
        return flows
    
    def _parse_port_stats(self, port_output: str) -> List[Dict[str, Any]]:
        """解析端口统计信息"""
        ports = []
        lines = port_output.strip().split('\n')
        
        current_port = None
        for line in lines:
            line = line.strip()
            if line.startswith('port') and ':' in line:
                port_info = line.split(':')
                if len(port_info) >= 2:
                    current_port = {
                        'port': port_info[0].split()[1],
                        'name': port_info[1].split()[0] if len(port_info) > 1 else 'unknown'
                    }
            elif current_port and 'rx' in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        current_port[parts[0]] = int(parts[2])
                    except ValueError:
                        current_port[parts[0]] = parts[2]
            elif current_port and 'tx' in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        current_port[parts[0]] = int(parts[2])
                    except ValueError:
                        current_port[parts[0]] = parts[2]
                
                if current_port:
                    ports.append(current_port)
                    current_port = None
        
        return ports
    
    def _parse_aggregate_stats(self, aggregate_output: str) -> Dict[str, Any]:
        """解析聚合统计信息"""
        aggregate = {}
        lines = aggregate_output.strip().split('\n')
        
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                try:
                    value = int(value)
                except ValueError:
                    pass
                
                aggregate[key] = value
        
        return aggregate
    
    def run_iperf_test(self, src_host: str, dst_host: str, duration: int = 10) -> Dict[str, Any]:
        """运行iperf测试"""
        try:
            # 注意：这需要在Mininet环境中运行
            cmd = f"h{src_host} iperf -c h{dst_host} -t {duration} -J"
            
            # 通过tmux发送命令
            # 这里简化处理，实际需要在Mininet CLI中执行
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    iperf_result = json.loads(result.stdout)
                    return {
                        'success': True,
                        'result': iperf_result,
                        'src': src_host,
                        'dst': dst_host,
                        'duration': duration
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Failed to parse iperf output',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'stdout': result.stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        if not self.monitoring_data.get('data'):
            return {}
        
        summary = {
            'total_data_points': len(self.monitoring_data['data']),
            'monitoring_duration': time.time() - self.monitoring_data['start_time'],
            'switches': self.monitoring_data['switches'],
            'latest_data': self.monitoring_data['data'][-1] if self.monitoring_data['data'] else None
        }
        
        return summary
    
    def save_monitoring_data(self, filename: str):
        """保存监控数据到文件"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.monitoring_data, f, indent=2, default=str)
            
            logger.info(f"Monitoring data saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
    
    def load_monitoring_data(self, filename: str) -> bool:
        """从文件加载监控数据"""
        try:
            with open(filename, 'r') as f:
                self.monitoring_data = json.load(f)
            
            logger.info(f"Monitoring data loaded from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading monitoring data: {e}")
            return False