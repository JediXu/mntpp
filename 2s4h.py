#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

def createDumbbellTopo():
    """创建2交换机4主机哑铃拓扑"""
    net = Mininet(switch=OVSBridge, controller=None, link=TCLink)
    
    try:
        # 创建主机
        h1 = net.addHost('h1', ip='10.0.1.1/24')
        h2 = net.addHost('h2', ip='10.0.1.2/24')
        h3 = net.addHost('h3', ip='10.0.2.1/24')
        h4 = net.addHost('h4', ip='10.0.2.2/24')
        
        # 创建交换机
        s1 = net.addSwitch('s1')
        s2 = net.addSwitch('s2')
        
        # 添加链路（不指定端口，让Mininet自动分配）
        net.addLink(h1, s1)
        net.addLink(h2, s1)
        net.addLink(s1, s2)
        net.addLink(s2, h3)
        net.addLink(s2, h4)
        
        # 启动网络
        net.start()
        
        # 配置交换机
        for sw in [s1, s2]:
            sw.cmd(f'ovs-vsctl set bridge {sw.name} protocols=OpenFlow10')
            sw.cmd(f'ovs-vsctl set bridge {sw.name} other-config:disable-in-band=true')
            sw.cmd(f'ovs-vsctl set bridge {sw.name} stp-enable=false')
            sw.cmd(f'ovs-ofctl -O OpenFlow10 del-flows {sw.name}')
        
        print("网络启动成功！")
        print("拓扑结构：")
        print("h1 -- s1 -- s2 -- h3")
        print("h2 --/         \\-- h4")
        
        CLI(net)
        
    except Exception as e:
        print(f"网络启动失败: {e}")
    finally:
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    createDumbbellTopo()