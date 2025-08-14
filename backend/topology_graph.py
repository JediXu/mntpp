#!/usr/bin/env python3
"""
拓扑图管理器
从Mininet CLI提取网络拓扑信息并构建图结构
"""

import networkx as nx
import logging
import re
import time
from typing import Dict, List, Tuple, Any
from backend.tmux_manager import TmuxManager

logger = logging.getLogger(__name__)

class TopologyGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.port_mapping = {}  # 存储端口映射信息
        self.node_info = {}     # 存储节点信息
        self.net_output = ""    # 存储原始net命令输出
        self.raw_links = []     # 存储解析后的链路信息
        self.tmux_manager = TmuxManager(session_name="mininet_session", use_sudo=True)
    
    def extract_topology_from_mininet(self, session_name: str = "mininet_session") -> bool:
        """从Mininet CLI提取完整拓扑信息，使用net命令获取更完整的邻接表"""
        try:
            # 等待网络完全启动
            max_wait = 30
            waited = 0
            
            while waited < max_wait:
                # 检查会话是否存在
                if not self._check_session_exists(session_name):
                    logger.warning("Mininet会话不存在，等待启动...")
                    time.sleep(1)
                    waited += 1
                    continue
                
                # 使用net命令获取拓扑信息
                net_output = self._get_net_from_mininet(session_name)
                if net_output:
                    # 保存原始net输出
                    self.net_output = net_output
                    
                    topology_info = self._parse_net_output(net_output)
                    if topology_info['switches']:
                        logger.info(f"检测到完整拓扑: {len(topology_info['switches'])} 交换机, "
                                   f"{len(topology_info['hosts'])} 主机, {len(topology_info['links'])} 链路")
                        
                        # 保存解析后的链路信息
                        self.raw_links = topology_info['links']
                        
                        self._build_complete_graph(
                            topology_info['switches'], 
                            topology_info['hosts'], 
                            topology_info['links']
                        )
                        return True
                
                time.sleep(1)
                waited += 1
                if waited % 3 == 0:
                    logger.info(f"等待网络启动... ({waited}s)")
            
            logger.error("无法从Mininet CLI获取拓扑信息")
            return False
            
        except Exception as e:
            logger.error(f"提取拓扑时出错: {e}")
            return False
    
    def _check_session_exists(self, session_name: str) -> bool:
        """检查tmux会话是否存在"""
        try:
            result = self.tmux_manager.send_command("dump", wait=1)
            return result is not None and len(result.strip()) > 0
        except:
            return False
    
    def _get_net_from_mininet(self, session_name: str) -> str:
        """从Mininet CLI获取net命令输出"""
        try:
            max_retries = 3
            for attempt in range(max_retries):
                # 发送空命令检查提示符
                check_output = self.tmux_manager.send_command("", wait=0.5)
                if check_output and "mininet>" in check_output:
                    # CLI已准备好，发送net命令
                    output = self.tmux_manager.send_command("net", wait=2)
                    if output and any(x in output for x in ['eth', 'lo:']):
                        logger.debug(f"成功获取net输出: {len(output)}字符")
                        return output
                    else:
                        logger.debug(f"第{attempt+1}次尝试获取net输出失败")
                else:
                    logger.debug(f"第{attempt+1}次尝试等待CLI提示符")
                    time.sleep(1)
            
            return ""
            
        except Exception as e:
            logger.error(f"获取net输出失败: {e}")
            return ""
    
    def _parse_net_output(self, net_output: str) -> Dict[str, List[Dict[str, Any]]]:
        """解析Mininet CLI的net输出"""
        topology_info = {
            'switches': [],
            'hosts': [],
            'links': []
        }
        
        try:
            lines = net_output.strip().split('\n')
            
            switches = set()
            hosts = set()
            links = []
            
            for line in lines:
                line = line.strip()
                if not line or line == 'mininet>':
                    continue
                
                # 解析格式: 节点名 端口信息
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                node_name = parts[0]
                
                # 跳过mininet提示符
                if node_name == 'mininet>':
                    continue
                
                # 收集节点信息
                if node_name.startswith('s'):
                    switches.add(node_name)
                elif node_name.startswith('h'):
                    hosts.add(node_name)
                
                # 解析端口连接
                for part in parts[1:]:
                    if ':' in part and 'eth' in part:
                        # 格式: s1-eth4:h1-eth0
                        local_port, remote_info = part.split(':', 1)
                        
                        # 解析本地端口
                        local_match = re.match(r'^(\w+)-eth(\d+)$', local_port)
                        if not local_match:
                            continue
                        
                        local_node = local_match.group(1)
                        local_port_num = int(local_match.group(2))
                        
                        # 解析远端信息
                        remote_match = re.match(r'^(\w+)-eth(\d+)$', remote_info)
                        if not remote_match:
                            continue
                        
                        remote_node = remote_match.group(1)
                        remote_port_num = int(remote_match.group(2))
                        
                        # 避免重复添加链路（双向的）
                        link_key = tuple(sorted([local_node, remote_node]))
                        
                        # 创建链路，确保端口对应关系正确
                        if local_node < remote_node:
                            links.append({
                                'source': local_node,
                                'target': remote_node,
                                'source_port': local_port_num,
                                'target_port': remote_port_num
                            })
                        else:
                            links.append({
                                'source': remote_node,
                                'target': local_node,
                                'source_port': remote_port_num,
                                'target_port': local_port_num
                            })
            
            # 构建节点列表
            for switch in sorted(switches):
                topology_info['switches'].append({
                    'name': switch,
                    'dpid': switch.replace('s', '')
                })
            
            for host in sorted(hosts):
                topology_info['hosts'].append({
                    'name': host,
                    'ip': f'10.0.0.{host[1:]}/24'
                })
            
            # 去重链路
            seen_links = set()
            unique_links = []
            for link in links:
                link_key = (link['source'], link['target'])
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    unique_links.append(link)
            
            topology_info['links'] = unique_links
            
            return topology_info
            
        except Exception as e:
            logger.error(f"解析net输出失败: {e}")
            return topology_info
    
    def _build_complete_graph(self, switches: List[Dict], hosts: List[Dict], links: List[Dict[str, Any]]):
        """构建包含交换机和主机的完整图"""
        try:
            self.graph.clear()
            
            # 添加交换机节点
            for switch in switches:
                self.graph.add_node(switch['name'], 
                                  type='switch',
                                  dpid=switch['dpid'])
            
            # 添加主机节点
            for host in hosts:
                self.graph.add_node(host['name'],
                                  type='host',
                                  ip=host['ip'])
            
            # 添加链路
            for link in links:
                self.graph.add_edge(link['source'], link['target'],
                                  source_port=link['source_port'],
                                  target_port=link['target_port'])
            
            # 构建端口映射
            self._build_port_mapping()
            
            logger.info(f"构建完整图成功: {len(self.graph.nodes)} 节点, {len(self.graph.edges)} 边")
            
        except Exception as e:
            logger.error(f"构建图失败: {e}")
    
    def _build_port_mapping(self):
        """构建端口映射"""
        try:
            self.port_mapping = {}
            
            for node in self.graph.nodes:
                self.port_mapping[node] = {}
                
                # 获取节点的所有连接
                for neighbor in self.graph.neighbors(node):
                    edge_data = self.graph[node][neighbor]
                    
                    # 确定端口映射
                    if node == edge_data.get('source'):
                        port = edge_data.get('source_port', 1)
                    else:
                        port = edge_data.get('target_port', 1)
                    
                    self.port_mapping[node][neighbor] = port
            
        except Exception as e:
            logger.error(f"构建端口映射失败: {e}")
    
    def get_topology_data(self) -> Dict[str, Any]:
        """获取拓扑数据用于GUI显示"""
        try:
            nodes = []
            edges = []
            
            for node in self.graph.nodes:
                node_data = self.graph.nodes[node]
                nodes.append({
                    'id': node,
                    'type': node_data.get('type', 'unknown'),
                    'ip': node_data.get('ip', '')
                })
            
            for edge in self.graph.edges:
                edge_data = self.graph[edge[0]][edge[1]]
                edges.append({
                    'source': edge[0],
                    'target': edge[1],
                    'source_port': edge_data.get('source_port', 1),
                    'target_port': edge_data.get('target_port', 1)
                })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'port_mapping': self.port_mapping
            }
            
        except Exception as e:
            logger.error(f"获取拓扑数据失败: {e}")
            return {'nodes': [], 'edges': [], 'port_mapping': {}}
    
    def find_path(self, src: str, dst: str, algorithm: str = 'dijkstra') -> List[str]:
        """计算从源到目的的路径"""
        try:
            if src not in self.graph or dst not in self.graph:
                logger.error(f"节点不存在: {src} 或 {dst}")
                return []
            
            if algorithm == 'dijkstra':
                try:
                    path = nx.shortest_path(self.graph, src, dst)
                    return path
                except nx.NetworkXNoPath:
                    logger.error(f"从 {src} 到 {dst} 无可用路径")
                    return []
            
            return []
            
        except Exception as e:
            logger.error(f"计算路径失败: {e}")
            return []
    
    def get_port_pair_from_raw_links(self, node1: str, node2: str) -> tuple:
        """从原始链路信息中获取两个节点间的端口对
        
        返回 (node1的端口, node2的端口)
        直接从net_output中查找匹配的链路
        """
        try:
            if not self.raw_links:
                logger.warning("没有可用的原始链路信息")
                return None, None
            
            # 在原始链路中查找匹配的边
            for link in self.raw_links:
                source = link['source']
                target = link['target']
                
                # 检查正向边
                if source == node1 and target == node2:
                    return (link['source_port'], link['target_port'])
                
                # 检查反向边
                elif source == node2 and target == node1:
                    return (link['target_port'], link['source_port'])
            
            logger.warning(f"在原始链路中未找到 {node1} 和 {node2} 之间的连接")
            return None, None
            
        except Exception as e:
            logger.error(f"从原始链路获取端口对失败: {e}")
            return None, None
    
    # def get_raw_topology_info(self) -> Dict[str, Any]:
    #     """获取原始拓扑信息，包括net输出和链路信息"""
    #     return {
    #         'net_output': self.net_output,
    #         'raw_links': self.raw_links,
    #         'port_mapping': self.port_mapping
    #     }