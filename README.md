# Mininet Topology & Path Planning GUI

一个基于Tkinter的Mininet网络拓扑可视化与路径规划工具。

## 🎯 功能特性

- **可视化拓扑设计**: 通过拖拽方式创建网络拓扑
- **路径规划**: 支持手动和算法(Dijkstra/BFS/DFS)路径计算
- **流表下发**: 自动生成并下发OpenFlow流表规则
- **实时监控**: 监控网络状态和性能指标
- **CLI集成**: 一键进入Mininet命令行界面

## 🏗️ 架构设计

### 前端 (GUI)
- **技术栈**: 纯Tkinter实现
- **功能**: 拓扑设计、路径选择、状态监控
- **特点**: 非阻塞主线程，独立终端执行CLI

### 后端模块
- **tmux_manager.py**: tmux会话管理
- **mininet_manager.py**: Mininet网络生命周期管理
- **topology_graph.py**: 拓扑图构建与端口映射
- **path_to_flow.py**: 路径到流表转换
- **ovs_controller.py**: OpenFlow控制器接口
- **monitor.py**: 网络监控与性能收集

## 🚀 快速开始

### 环境要求
- Ubuntu 22.04+ 或兼容Linux发行版
- Python 3.8+
- Mininet 2.3.0+
- Open vSwitch

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/JediXu/mntpp.git
cd mininet-gui
```

2. **安装依赖**
```bash
sudo apt update
sudo apt install mininet openvswitch-switch tmux xterm python3-tk
pip3 install -r requirements.txt
```

3. **验证环境**
```bash
python3 scripts/quick_verify.py
```

4. **启动应用**
```bash
python3 gui.py
# 或
python3 mntpp.py
```

## 📋 使用指南

### 创建拓扑
1. 启动GUI界面
2. 选择工具栏中的"主机"或"交换机"工具
3. 在画布上点击放置节点
4. 选择"链路"工具连接节点

### 路径规划
1. 点击"启动实验"运行拓扑
2. 选择起点和终点主机
3. 选择路径算法（手动/Dijkstra/BFS/DFS）
4. 点击"创建路径"下发流表

### CLI操作
- 点击"附加到CLI"按钮
- 或在新终端执行：`sudo tmux attach-session -t mininet_session`

## 🔧 开发调试

### 调试脚本
项目提供多个调试脚本：
- `scripts/quick_verify.py`: 快速环境检查
- `scripts/verify_environment.py`: 完整环境验证
- `scripts/count_loc.py`: 代码行数统计

### 日志查看
- GUI界面实时显示操作日志
- 查看 `mininet_controller.log` 获取详细日志

## 📊 项目统计

- **总代码行数**: 2,772 LOC
- **Python文件**: 13个
- **测试脚本**: 4个
- **文档**: 完整README和FIXES.md

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🐛 问题反馈

如有问题，请在GitHub Issues中提交，包含：
- 操作系统版本
- Python版本
- 错误描述和重现步骤
- 相关日志输出
