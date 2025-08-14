# Mininet PoP (Path of Ping) - PyQt Edition

一个基于PyQt6的Mininet网络拓扑可视化与路径规划工具。本项目是对原版基于Tkinter的GUI工具的重大重构和功能增强。

## 🎯 功能特性

- **现代化的UI**: 使用PyQt6构建，界面更美观，交互更流畅。
- **可视化拓扑设计**:
  - 通过拖拽方式移动节点，实时更新拓扑布局。
  - 双击节点或链路，在设计时编辑其属性。
- **属性编辑**:
  - **主机**: 可自定义IP和MAC地址。
  - **链路**: 可配置带宽、时延、丢包率 (利用TC)。
- **CLI集成**: 实验运行时，可获取`tmux`命令一键附加到Mininet CLI。
- **路径规划**: 支持手动和经典算法(Dijkstra/BFS/DFS)的路径计算。
- **流表下发**: 根据规划的路径，自动生成并下发OpenFlow流表规则。
- **实时监控**:
  - 实验运行时，双击主机可查看实时的接口流量统计（收/发包数和字节数）。

## 🏗️ 架构设计

### 前端 (GUI)
- **技术栈**: PyQt6
- **功能**: 拓扑设计、属性编辑、路径选择、状态监控。
- **特点**:
  - 采用`QGraphicsView`框架实现高性能的拓扑渲染。
  - 通过自定义`QGraphicsItem`实现节点拖拽和交互。

### 后端模块
- **mininet_manager.py**: 通过生成拓扑脚本并在`tmux`会话中运行来管理Mininet生命周期，保留了对Mininet CLI的直接访问能力。
- **backend_api.py**: 为前端提供统一、清晰的API接口，并增加了通过`tmux`与Mininet交互获取实时数据的功能。
- **topology_graph.py**: 拓扑图构建与端口映射。
- **path_to_flow.py**: 路径到流表转换。
- **ovs_controller.py**: OpenFlow控制器接口。
- **monitor.py**: 负责解析从Mininet获取的统计数据。

## 🚀 快速开始

### 环境要求
- Ubuntu 22.04+ 或兼容的Linux发行版
- Python 3.8+
- Mininet 2.3.0+
- Open vSwitch
- tmux

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/JediXu/mntpp.git
cd mntpp
```

2. **一键安装依赖**
```bash
# 脚本将安装 python3-pyqt6, mininet, openvswitch-switch, tmux 等
bash scripts/install_ubuntu2204.sh
```

3. **安装Python包**
```bash
pip3 install -r requirements.txt
```

4. **启动应用**
```bash
python3 mntpp.py
# 或
python3 pyqt_app.py
```

## 📋 使用指南

### 拓扑与实验
1. 启动应用 (`python3 mntpp.py`)。
2. 点击 "Start Experiment" 按钮，将自动加载`2s4h.json`拓扑并启动Mininet。
3. 拓扑显示在画布上，可以拖动节点调整布局。
4. 双击主机或交换机可编辑其属性（仅在实验开始前）。
5. 实验运行期间，双击主机可查看实时流量统计。
6. 点击 "Attach to CLI" 按钮，会提示在新终端中需要执行的命令，以进入Mininet CLI。
7. 点击 "Stop Experiment" 停止Mininet仿真。

### 路径规划
1. 实验启动后，（未来版本将支持）选择起点和终点主机。
2. 选择路径算法。
3. 点击"创建路径"下发流表。

## 🔧 开发调试

### 日志查看
- 应用的操作日志会实时打印在启动终端。
- `mininet_controller.log` 文件记录了更详细的后端日志。

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

MIT License
