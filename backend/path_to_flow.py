#!/usr/bin/env python3
"""
路径到流表转换器
将路径转换为OpenFlow流表规则
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class PathToFlow:
    def __init__(self, topology_graph):
        self.topology_graph = topology_graph
        self.active_flows = {}  # 存储活跃的流表规则
    
    def create_flow_rules(self, path: List[str], flow_id: str = None, priority: int = 1000) -> List[Dict[str, Any]]:
        """创建流表规则
        
        修复版实现思路：
        1. 直接使用原始路径，无需扩展
        2. 为路径中的每对相邻节点查询端口映射
        3. 提取交换机的输入输出端口对
        4. 为每个交换机生成双向流表规则
        """
        try:
            if not path or len(path) < 2:
                logger.warning("Invalid path: must have at least 2 nodes")
                return []
            
            # 生成唯一的flow_id
            if flow_id is None:
                flow_id = f"flow_{path[0]}_{path[-1]}"
            
            # 直接使用原始路径，无需扩展
            logger.info(f"Path: {path}")
            
            # 提取交换机的输入输出端口对
            switch_port_map = {}  # {switch: {'in_port': port, 'out_port': port}}
            
            # 遍历路径中的每个交换机
            for i in range(1, len(path) - 1):  # 跳过源和目的主机
                switch = path[i]
                if not str(switch).startswith('s'):
                    continue
                
                # 找到前一个和后一个节点
                prev_node = path[i-1]
                next_node = path[i+1]
                
                # 获取端口对
                h1_to_s1 = self._get_port_pair(prev_node, switch)
                s1_to_h2 = self._get_port_pair(switch, next_node)
                
                if h1_to_s1 is None or s1_to_h2 is None:
                    logger.error(f"Cannot find ports for {prev_node}-{switch} or {switch}-{next_node}")
                    continue
                
                # 修正端口获取逻辑：
                # h1_to_s1: (h1的端口, s1的端口) -> 我们需要的是s1接收h1的端口
                # s1_to_h2: (s1的端口, h2的端口) -> 我们需要的是s1发送到h2的端口
                
                # 获取交换机的端口值
                switch_in_port = h1_to_s1[1]  # s1接收来自h1的端口
                switch_out_port = s1_to_h2[0]  # s1发送到h2的端口
                
                # 验证端口值是否有效
                if switch_in_port == 0 or switch_out_port == 0:
                    logger.warning(f"Invalid port values: in_port={switch_in_port}, out_port={switch_out_port}")
                    
                logger.debug(f"Switch {switch}: in_port={switch_in_port} (from {prev_node}), out_port={switch_out_port} (to {next_node})")
                
                switch_port_map[switch] = {
                    'in_port': switch_in_port,   # s1接收来自h1的端口
                    'out_port': switch_out_port  # s1发送到h2的端口
                }
            
            logger.info(f"Switch port map: {switch_port_map}")
            
            # 为每个交换机生成双向流表规则
            flow_rules = []
            
            for switch, ports in switch_port_map.items():
                in_port = ports['in_port']
                out_port = ports['out_port']
                
                # 正向流表规则（从源到目的）
                rule1 = {
                    'switch': switch,
                    'flow_id': f"{flow_id}_forward",
                    'in_port': in_port,
                    'out_port': out_port,
                    'priority': priority,
                    'path': path,
                    'direction': 'forward'
                }
                
                # 反向流表规则（从目的到源）
                rule2 = {
                    'switch': switch,
                    'flow_id': f"{flow_id}_reverse",
                    'in_port': out_port,
                    'out_port': in_port,
                    'priority': priority,
                    'path': list(reversed(path)),
                    'direction': 'reverse'
                }
                
                flow_rules.extend([rule1, rule2])
            
            # 存储流表规则
            self.active_flows[flow_id] = flow_rules
            
            logger.info(f"Created {len(flow_rules)} flow rules for path: {path}")
            return flow_rules
            
        except Exception as e:
            logger.error(f"Error creating flow rules: {e}")
            return []
    
    def generate_ovs_commands(self, flow_rules: List[Dict[str, Any]]) -> List[str]:
        """生成ovs-ofctl命令"""
        try:
            commands = []
            
            for rule in flow_rules:
                switch = rule['switch']
                
                # 只处理交换机，跳过主机
                if not str(switch).startswith('s'):
                    logger.warning(f"Skipping non-switch device: {switch}")
                    continue
                    
                in_port = rule['in_port']
                out_port = rule['out_port']
                priority = rule['priority']
                
                # 构建OpenFlow规则
                match = f"in_port={in_port}"
                actions = f"actions=output:{out_port}"
                
                cmd = f"sudo ovs-ofctl add-flow {switch} '{match},priority={priority},{actions}'"
                commands.append(cmd)
            
            logger.info(f"Generated {len(commands)} ovs-ofctl commands")
            return commands
            
        except Exception as e:
            logger.error(f"Error generating ovs commands: {e}")
            return []
    
    def delete_flow_rules(self, flow_id: str) -> List[str]:
        """删除指定路径的流表规则"""
        try:
            if flow_id not in self.active_flows:
                logger.warning(f"Flow ID {flow_id} not found")
                return []
            
            flow_rules = self.active_flows[flow_id]
            commands = []
            
            for rule in flow_rules:
                switch = rule['switch']
                in_port = rule['in_port']
                
                # 删除对应的流表规则
                # 这里使用简单的匹配条件删除
                cmd = f"sudo ovs-ofctl del-flows {switch} in_port={in_port}"
                commands.append(cmd)
            
            # 从活跃流表中移除
            del self.active_flows[flow_id]
            
            logger.info(f"Deleted flow rules for flow ID: {flow_id}")
            return commands
            
        except Exception as e:
            logger.error(f"Error deleting flow rules: {e}")
            return []
    
    def _get_port_pair(self, node1: str, node2: str) -> tuple:
        """获取两个节点间的端口对（优先使用原始链路信息）
        
        返回 (node1的端口, node2的端口)
        优先从原始链路信息中获取，如果不可用则回退到NetworkX图
        """
        try:
            # 首先尝试从原始链路信息获取
            raw_ports = self.topology_graph.get_port_pair_from_raw_links(node1, node2)
            if raw_ports and raw_ports[0] is not None and raw_ports[1] is not None:
                logger.debug(f"使用原始链路信息: {node1}:{raw_ports[0]} -> {node2}:{raw_ports[1]}")
                return raw_ports
            
            # 如果原始链路信息不可用，回退到NetworkX图
            logger.debug("原始链路信息不可用，回退到NetworkX图")
            
            # 检查两个方向的边
            edge_data = None
            port1, port2 = None, None
            
            if self.topology_graph.graph.has_edge(node1, node2):
                edge_data = self.topology_graph.graph[node1][node2]
                port1 = edge_data.get('source_port', 1)  # node1的端口
                port2 = edge_data.get('target_port', 1)  # node2的端口
            elif self.topology_graph.graph.has_edge(node2, node1):
                edge_data = self.topology_graph.graph[node2][node1]
                port1 = edge_data.get('target_port', 1)  # node1的端口
                port2 = edge_data.get('source_port', 1)  # node2的端口
            else:
                logger.warning(f"No edge found between {node1} and {node2}")
                return None, None
            
            logger.debug(f"使用NetworkX图: {node1}:{port1} -> {node2}:{port2}")
            return (port1, port2)
            
        except Exception as e:
            logger.error(f"Error getting port pair for {node1}-{node2}: {e}")
            return None, None
    
    def calculate_path(self, src: str, dst: str, algorithm: str = 'dijkstra') -> List[str]:
        """计算从源到目的的路径"""
        try:
            return self.topology_graph.find_path(src, dst, algorithm)
            
        except Exception as e:
            logger.error(f"Error calculating path: {e}")
            return []
    
    def validate_path(self, path: List[str]) -> Tuple[bool, str]:
        """验证路径的有效性"""
        try:
            if len(path) < 2:
                return False, "Path must have at least 2 nodes"
            
            # 检查路径中的节点是否都存在
            for node in path:
                if node not in self.topology_graph.graph.nodes:
                    return False, f"Node {node} not found in topology"
            
            # 检查路径中的链路是否都存在
            for i in range(len(path) - 1):
                src, dst = path[i], path[i + 1]
                if not self.topology_graph.graph.has_edge(src, dst):
                    return False, f"No link between {src} and {dst}"
            
            # 检查是否有环路
            if len(set(path)) != len(path):
                return False, "Path contains loops"
            
            return True, "Valid path"
            
        except Exception as e:
            logger.error(f"Error validating path: {e}")
            return False, str(e)
    