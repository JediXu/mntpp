#!/usr/bin/env python3
"""
前端GUI模块
使用Tkinter实现的网络拓扑控制界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import logging
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend_api import BackendAPI
    BACKEND_AVAILABLE = True
    backend_api = BackendAPI()
except ImportError as e:
    print(f"后端模块导入失败: {e}")
    BACKEND_AVAILABLE = False
    backend_api = None

class NetworkTopologyGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mininet Topology & Path Planning")
        self.root.geometry("1200x800")
        
        # 初始化状态变量
        self.experiment_running = False
        self.current_tool = None
        self.selected_path_mode = tk.StringVar(value="manual")
        self.nodes = []  # 存储节点信息 [{id, type, x, y}]
        self.links = []  # 存储链路信息 [{source, target}]
        self.paths = {}  # 存储路径信息
        self.selected_nodes = []  # 用于路径选择的节点序列
        self.drag_data = {"x": 0, "y": 0, "item": None, "node": None}
        self.selected_tool = None
        self.canvas_objects = {}  # 存储画布对象引用
        
        # 路径相关状态变量（必须在创建GUI之前初始化）
        self.is_creating_path = False
        self.is_delete_mode = False
        self.current_path_nodes = []
        self.highlighted_path = None
        self.active_paths = {}  # 存储所有活跃路径 {path_id: {'path': [...], 'color': '...', 'items': [...]}}
        self.path_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan']
        self.next_color_index = 0
        
        # 初始化后端API
        if BACKEND_AVAILABLE and backend_api is not None:
            self.backend_api = backend_api
        else:
            self.backend_api = None
            
        # 创建GUI组件
        self._create_gui()
        
        # 检查后端可用性
        if not BACKEND_AVAILABLE or self.backend_api is None:
            messagebox.showwarning("警告", "后端模块不可用，某些功能可能无法使用")
            
        # 绑定事件
        self._bind_events()
        
        # 启动定时器
        self._update_status()
    
    def _create_gui(self):
        """创建完整的GUI界面 - 三frame布局"""
        # 创建主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建顶部控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        # 第一frame：文件操作和拓扑设计
        frame1 = ttk.LabelFrame(control_frame, text="文件和拓扑", padding=5)
        frame1.pack(side=tk.LEFT, padx=(0, 5))
        
        # 第一行：文件操作
        file_frame = ttk.Frame(frame1)
        file_frame.pack(fill=tk.X)
        ttk.Button(file_frame, text="新建", command=self.new_topology, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="打开", command=self.open_topology, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="保存", command=self.save_topology, width=8).pack(side=tk.LEFT, padx=2)
        
        # 第二行：拓扑设计
        topo_frame = ttk.Frame(frame1)
        topo_frame.pack(fill=tk.X, pady=(5, 0))
        self.tool_buttons = {}
        tools = ["主机", "交换机", "链路", "删除"]
        for tool in tools:
            btn = ttk.Button(topo_frame, text=tool, 
                           command=lambda t=tool: self.select_tool(t), 
                           width=8)
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool] = btn
        
        # 第二frame：实验控制
        frame2 = ttk.LabelFrame(control_frame, text="实验控制", padding=5)
        frame2.pack(side=tk.LEFT, padx=(0, 5))
        
        exp_frame1 = ttk.Frame(frame2)
        exp_frame1.pack(fill=tk.X)
        self.start_btn = ttk.Button(exp_frame1, text="启动实验", 
                                  command=self.start_experiment, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        exp_frame2 = ttk.Frame(frame2)
        exp_frame2.pack(fill=tk.X, pady=(5, 0))
        self.stop_btn = ttk.Button(exp_frame2, text="停止实验", 
                                 command=self.stop_experiment, width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        # 第三frame：路径控制
        frame3 = ttk.LabelFrame(control_frame, text="路径控制", padding=5)
        frame3.pack(side=tk.LEFT)
        
        path_frame1 = ttk.Frame(frame3)
        path_frame1.pack(fill=tk.X)
        ttk.Label(path_frame1, text="算法:").pack(side=tk.LEFT, padx=2)
        algorithms = ["manual", "dijkstra", "bfs", "dfs"]
        self.algo_combo = ttk.Combobox(path_frame1, textvariable=self.selected_path_mode, 
                                     values=algorithms, state="readonly", width=10)
        self.algo_combo.pack(side=tk.LEFT, padx=2)
        
        path_frame2 = ttk.Frame(frame3)
        path_frame2.pack(fill=tk.X, pady=(5, 0))
        self.create_path_btn = ttk.Button(path_frame2, text="创建路径", 
                                        command=self.create_path, width=8)
        self.create_path_btn.pack(side=tk.LEFT, padx=2)
        self.delete_path_btn = ttk.Button(path_frame2, text="删除路径", 
                                        command=self.delete_path, width=8)
        self.delete_path_btn.pack(side=tk.LEFT, padx=2)
        
        # 创建画布区域
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 创建滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        
        # 创建画布
        self.canvas = tk.Canvas(canvas_frame, 
                              bg='white',
                              yscrollcommand=v_scrollbar.set,
                              xscrollcommand=h_scrollbar.set,
                              scrollregion=(0, 0, 2000, 1500))
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建状态栏
        self._create_status_bar()
        
        # 设置初始状态
        self.update_ui_state()
    
    def _create_canvas(self):
        """创建画布"""
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        
        # 创建画布
        self.canvas = tk.Canvas(canvas_frame, 
                              bg='white',
                              yscrollcommand=v_scrollbar.set,
                              xscrollcommand=h_scrollbar.set,
                              scrollregion=(0, 0, 2000, 1500))
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定画布事件
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def _create_status_bar(self):
        """创建信息窗口和状态栏 - 左侧布局，高度对齐"""
        # 创建底部容器
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # 创建信息窗口（左侧）
        info_frame = ttk.Frame(bottom_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 创建信息文本框（2行高）
        self.info_text = tk.Text(info_frame, height=2, width=70, 
                               wrap=tk.WORD, state=tk.DISABLED,
                               font=('TkDefaultFont', 9))
        self.info_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建信息窗口滚动条（与文本框等高）
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        info_scrollbar.config(command=self.info_text.yview)
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        
        # 创建状态容器（右侧）
        status_container = ttk.Frame(bottom_frame)
        status_container.pack(side=tk.LEFT, fill=tk.Y)
        
        # 实验状态标签（上方）
        self.exp_status_label = ttk.Label(status_container, text="实验未启动", 
                                        relief=tk.SUNKEN, width=15,
                                        anchor=tk.CENTER)
        self.exp_status_label.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
        
        # 主状态标签（下方）
        self.status_label = ttk.Label(status_container, text="就绪", 
                                    relief=tk.SUNKEN, width=15,
                                    anchor=tk.CENTER)
        self.status_label.pack(side=tk.TOP, fill=tk.X)
        

    
    def _bind_events(self):
        """绑定事件"""
        self.root.bind("<Escape>", lambda e: self.select_tool(None))
        self.root.bind("<Control-n>", lambda e: self.new_topology())
        self.root.bind("<Control-o>", lambda e: self.open_topology())
        self.root.bind("<Control-s>", lambda e: self.save_topology())
        
        # 画布事件
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        
        # 键盘事件
        # self.root.bind("<Delete>", self.delete_selected)
        
        # 路径选择事件
        self.canvas.bind("<Button-3>", self.on_right_click)  # 右键取消选择
        # self.canvas.bind("<Shift-Button-1>", self.on_shift_click)  # Shift+左键多选
    
    def select_tool(self, tool):
        """选择工具"""
        # 重置所有按钮状态
        for t, btn in self.tool_buttons.items():
            if hasattr(btn, 'state'):
                btn.state(['!pressed'])
        
        # 设置当前工具按钮为按下状态
        if tool in self.tool_buttons:
            if hasattr(self.tool_buttons[tool], 'state'):
                self.tool_buttons[tool].state(['pressed'])
        
        self.current_tool = tool
        
        # 更新鼠标光标
        cursor_map = {
            '主机': 'circle',
            '交换机': 'circle',
            '链路': 'crosshair',
            '删除': 'X_cursor',
            None: 'arrow'
        }
        self.canvas.config(cursor=cursor_map.get(tool, 'arrow'))
        
        if tool:
            self.status_label.config(text=f"选择工具: {tool}")
        else:
            self.status_label.config(text="就绪")
    
    def new_topology(self):
        """新建拓扑"""
        self.canvas.delete("all")
        self.nodes.clear()
        self.links.clear()
        self.paths.clear()
        self.selected_nodes.clear()
        self.active_paths.clear()
        self.next_color_index = 0
        self.highlighted_path = None
        self.status_label.config(text="新建拓扑")
        self.log_message("新建拓扑已创建")
    
    def open_topology(self):
        """打开拓扑"""
        filename = filedialog.askopenfilename(
            title="打开拓扑文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.canvas.delete("all")
                self.nodes = data.get('nodes', [])
                self.links = data.get('links', [])
                
                # 清除现有路径
                self.active_paths.clear()
                self.next_color_index = 0
                self.highlighted_path = None
                
                # 重绘画布
                self.redraw_topology()
                
                self.status_label.config(text=f"拓扑已加载: {filename}")
                self.log_message(f"拓扑文件已加载: {filename}")
                
            except Exception as e:
                messagebox.showerror("错误", f"无法加载拓扑文件: {e}")
    
    def save_topology(self):
        """保存拓扑"""
        filename = filedialog.asksaveasfilename(
            title="保存拓扑文件",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                data = {
                    'nodes': self.nodes,
                    'links': self.links,
                    'paths': self.paths
                }
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.status_label.config(text=f"拓扑已保存: {filename}")
                self.log_message(f"拓扑文件已保存: {filename}")
                
            except Exception as e:
                messagebox.showerror("错误", f"无法保存拓扑文件: {e}")
    
    def start_experiment(self):
        """启动实验 - 基于当前拓扑自动生成Mininet脚本并自动打开CLI"""
        if self.backend_api is None:
            messagebox.showerror("错误", "后端API不可用")
            self.log_message("后端API不可用，无法启动实验")
            return
            
        try:
            # 检查是否有拓扑
            if not self.nodes:
                messagebox.showwarning("提示", "请先创建拓扑（至少添加一个节点）")
                return
                
            # 将当前拓扑数据转换为后端需要的格式
            topology_data = self._get_topology_data_for_backend()
            self.log_message("准备启动实验，拓扑数据已准备")
            
            # 将拓扑数据传递给后端启动实验
            result = self.backend_api.start_experiment(topology_data)
            if result['success']:
                self.experiment_running = True
                self.update_ui_state()
                self.exp_status_label.config(text="实验运行中")
                self.log_message("实验启动成功")
                
                # 实验启动成功，拓扑已在运行中，无需重新显示
                self.log_message("实验已启动，拓扑正在运行")
                
                # CLI窗口已自动打开（由后端API处理）
                self.log_message("Mininet CLI窗口已自动打开")
                    
            else:
                messagebox.showerror("错误", f"启动实验失败: {result.get('error', '未知错误')}")
                self.log_message(f"启动实验失败: {result.get('error', '未知错误')}")
        except Exception as e:
            messagebox.showerror("错误", f"启动实验失败: {e}")
            self.log_message(f"启动实验失败: {e}")
            
    def _get_topology_data_for_backend(self):
        """将当前GUI拓扑数据转换为后端需要的格式"""
        try:
            # 转换为后端需要的拓扑数据格式
            topology_data = {
                "switches": [],
                "hosts": [],
                "links": []
            }
            
            # 添加交换机
            for node in self.nodes:
                if node['type'] == 'switch':
                    switch_name = node.get('id', f's{len(topology_data["switches"])+1}')
                    topology_data["switches"].append({
                        "name": switch_name,
                        "dpid": str(len(topology_data["switches"]) + 1)
                    })
            
            # 添加主机
            for node in self.nodes:
                if node['type'] == 'host':
                    host_name = node.get('id', f'h{len(topology_data["hosts"])+1}')
                    topology_data["hosts"].append({
                        "name": host_name,
                        "ip": f"10.0.0.{len(topology_data['hosts'])+1}/24"
                    })
            
            # 添加链路
            for link in self.links:
                topology_data["links"].append({
                    "src": link['source'],
                    "dst": link['target']
                })
            
            return topology_data
            
        except Exception as e:
            self.log_message(f"获取拓扑数据失败: {e}")
            return None
            
    def stop_experiment(self):
        """停止实验 - 调用后端API"""
        if self.backend_api is None:
            messagebox.showerror("错误", "后端API不可用")
            self.log_message("后端API不可用，无法停止实验")
            return
            
        try:
            result = self.backend_api.stop_experiment()
            if result['success']:
                self.experiment_running = False
                self.update_ui_state()
                self.exp_status_label.config(text="实验未启动")
                self.log_message("实验停止成功 - 拓扑已保留")
                # 停止实验时不清空拓扑，保留设计的拓扑以便重新启动
            else:
                messagebox.showerror("错误", f"停止实验失败: {result.get('error', '未知错误')}")
                self.log_message(f"停止实验失败: {result.get('error', '未知错误')}")
        except Exception as e:
            messagebox.showerror("错误", f"停止实验失败: {e}")
            self.log_message(f"停止实验失败: {e}")
    
    def attach_to_cli(self):
        """附加到CLI - 实际打开终端窗口"""
        if self.backend_api is None:
            messagebox.showerror("错误", "后端API不可用")
            return
            
        try:
            cli_result = self.backend_api.attach_to_cli()
            if cli_result['success']:
                command = cli_result.get('command', 'sudo tmux attach-session -t mininet_session')
                
                # 实际打开终端窗口
                import subprocess
                import platform
                
                if platform.system() == "Linux":
                    # 在Linux上打开新的终端窗口
                    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', command])
                    self.log_message("已打开Mininet CLI终端")
                else:
                    # 显示命令供用户手动执行
                    messagebox.showinfo("CLI命令", f"请在新终端中执行以下命令：\n\n{command}")
                    self.log_message(f"CLI命令已提供: {command}")
            else:
                messagebox.showerror("错误", f"无法获取CLI命令: {cli_result.get('error', '未知错误')}")
                self.log_message(f"获取CLI命令失败: {cli_result.get('error', '未知错误')}")
                
        except Exception as e:
            messagebox.showerror("错误", f"打开CLI窗口失败: {e}")
            self.log_message(f"打开CLI窗口失败: {e}")
    
    def create_path(self):
        """创建路径 - 支持手动和自动路径选择"""
        if self.backend_api is None:
            messagebox.showerror("错误", "后端API不可用")
            self.log_message("后端API不可用，无法创建路径")
            return
            
        if not self.experiment_running:
            messagebox.showwarning("提示", "请先启动实验")
            return
            
        mode = self.selected_path_mode.get()
        
        # 设置路径创建模式
        self.is_creating_path = True
        self.current_path_nodes = []
        self.create_path_btn.config(state=tk.DISABLED)
        
        if mode == "manual":
            self.log_message("手动路径创建模式：请按顺序点击节点（起点→中间点→终点）")
            self.status_label.config(text="手动路径创建模式：按顺序选择节点")
        else:
            self.log_message(f"自动路径创建模式：请选择起点和终点主机")
            self.status_label.config(text=f"自动路径创建模式：选择{mode}算法的起点和终点")

    def delete_path(self):
        """删除路径"""
        if self.backend_api is None:
            messagebox.showerror("错误", "后端API不可用")
            self.log_message("后端API不可用，无法删除路径")
            return
            
        if not self.experiment_running:
            messagebox.showwarning("提示", "请先启动实验")
            return
            
        # 设置删除模式
        self.is_delete_mode = True
        self.delete_path_btn.config(state=tk.DISABLED)
        self.log_message("路径删除模式：请点击要删除的高亮路径")
        self.status_label.config(text="路径删除模式：点击要删除的路径")

    def on_canvas_double_click(self, event):
        """双击画布事件处理"""
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # 找到双击的节点
        clicked_items = self.canvas.find_overlapping(x-10, y-10, x+10, y+10)
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if 'host' in tags or 'switch' in tags:
                # 获取节点信息
                node_id = None
                for node in self.nodes:
                    node_x, node_y = node['x'], node['y']
                    if abs(x - node_x) < 20 and abs(y - node_y) < 20:
                        node_id = node['id']
                        break
                
                if node_id:
                    # 显示节点信息或编辑对话框
                    self.log_message(f"双击节点: {node_id}")
                    break
    
    def cancel_path_creation(self):
        """取消路径创建"""
        if hasattr(self, 'selected_nodes'):
            self.selected_nodes.clear()
        
        # 重置所有按钮状态
        for btn in self.tool_buttons.values():
            btn.state(['!pressed'])
        
        # 清除高亮状态并重绘整个拓扑
        self.clear_path_highlight()
        self.redraw_topology()
        
        # 重置链路状态
        if hasattr(self, 'link_start') and self.link_start:
            self.link_start = None
        
        self.exit_path_mode()
        self.log_message("取消路径操作")
    
    def exit_path_mode(self):
        """退出路径模式，但不清除高亮"""
        # 重置路径创建和删除模式
        if hasattr(self, 'is_creating_path'):
            self.is_creating_path = False
            self.create_path_btn.config(state=tk.NORMAL)
        
        if hasattr(self, 'is_delete_mode'):
            self.is_delete_mode = False
            self.delete_path_btn.config(state=tk.NORMAL)
            
        self.current_tool = None
        self.canvas.config(cursor='arrow')
        
        # 清除绿色临时高亮，但保留红色路径高亮
        self.clear_temporary_highlights()
    
    def clear_temporary_highlights(self):
        """清除临时高亮（绿色），但保留路径高亮（红色）"""
        # 清除绿色节点高亮
        for node in self.nodes:
            items = self.canvas.find_overlapping(
                node['x']-25, node['y']-25, 
                node['x']+25, node['y']+25
            )
            for item in items:
                tags = self.canvas.gettags(item)
                if 'host' in tags or 'switch' in tags:
                    current_outline = self.canvas.itemcget(item, 'outline')
                    if current_outline == 'green':  # 只清除绿色高亮
                        self.canvas.itemconfig(item, outline='black', width=1)
        
        # 清除绿色链路高亮（非path_highlight标记的）
        all_items = self.canvas.find_all()
        for item in all_items:
            tags = self.canvas.gettags(item)
            if 'path_highlight' not in tags:
                item_type = self.canvas.type(item)
                if item_type == 'line':
                    current_fill = self.canvas.itemcget(item, 'fill')
                    if current_fill == 'green':  # 只清除绿色链路
                        self.canvas.delete(item)

    def highlight_path(self, path):
        """高亮显示路径（兼容旧接口）"""
        if not path:
            return
        self.highlight_path_with_color(path, 'red')
    
    def highlight_path_with_color(self, path, color, path_id=None):
        """使用指定颜色高亮显示路径"""
        if not path:
            return
            
        # 获取节点坐标映射
        node_coords = {node['id']: (node['x'], node['y']) for node in self.nodes}
        
        # 存储路径项以便后续删除
        path_items = []
        
        # 高亮路径上的所有节点
        for node_id in path:
            if node_id in node_coords:
                items = self.highlight_node_with_color(node_id, color)
                path_items.extend(items)
        
        # 高亮路径上的所有链路
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            if source in node_coords and target in node_coords:
                line = self.highlight_link_with_color(source, target, color)
                if line:
                    path_items.append(line)
        
        # 如果提供了path_id，更新存储的路径信息
        if path_id and path_id in self.active_paths:
            self.active_paths[path_id]['items'] = path_items
        
        # 更新状态栏
        self.status_label.config(text=f"路径: {' -> '.join(path)} (颜色: {color})")
        self.log_message(f"显示路径: {' -> '.join(path)} (颜色: {color})")
    
    def highlight_node_with_color(self, node_id, color):
        """使用指定颜色高亮单个节点，返回创建的项"""
        items = []
        for node in self.nodes:
            if node['id'] == node_id:
                items_found = self.canvas.find_overlapping(
                    node['x']-25, node['y']-25, 
                    node['x']+25, node['y']+25
                )
                for item in items_found:
                    tags = self.canvas.gettags(item)
                    if 'host' in tags or 'switch' in tags:
                        # 创建高亮圆圈
                        circle = self.canvas.create_oval(
                            node['x']-15, node['y']-15,
                            node['x']+15, node['y']+15,
                            outline=color, width=3, tags=('path_highlight',)
                        )
                        items.append(circle)
                        break
        return items
    
    def highlight_link_with_color(self, node1, node2, color):
        """使用指定颜色高亮两个节点之间的链路"""
        node_coords = {node['id']: (node['x'], node['y']) for node in self.nodes}
        if node1 in node_coords and node2 in node_coords:
            x1, y1 = node_coords[node1]
            x2, y2 = node_coords[node2]
            line = self.canvas.create_line(x1, y1, x2, y2, 
                                         fill=color, width=3, 
                                         tags=('path_highlight',))
            self.canvas.tag_raise(line)
            return line
        return None

    def handle_path_creation_click(self, x, y):
        """处理路径创建时的画布点击"""
        mode = self.selected_path_mode.get()
        
        # 找到点击的节点
        clicked_node = self.get_node_at_position(x, y)
        if not clicked_node:
            return
            
        node_id = clicked_node['id']
        
        if mode == "manual":
            # 手动模式：按顺序添加节点
            if not self.current_path_nodes:
                # 第一个节点必须是主机
                if clicked_node['type'] != 'host':
                    messagebox.showwarning("提示", "路径起点必须是主机")
                    return
                self.current_path_nodes.append(node_id)
                self.highlight_node(node_id, 'green')
                self.log_message(f"选择起点: {node_id}")
                self.status_label.config(text=f"已选择起点: {node_id}，请选择下一个节点")
            else:
                # 检查是否重复
                if node_id in self.current_path_nodes:
                    messagebox.showwarning("提示", "节点已在路径中，不能重复选择")
                    return
                    
                # 检查是否有链路连接
                last_node = self.current_path_nodes[-1]
                if not self.has_link_between(last_node, node_id):
                    messagebox.showwarning("提示", f"节点{last_node}和{node_id}之间没有链路连接")
                    return
                
                # 添加到路径
                self.current_path_nodes.append(node_id)
                self.highlight_node(node_id, 'green')
                self.highlight_link(last_node, node_id, 'green')
                
                # 如果是终点
                if clicked_node['type'] == 'host' and len(self.current_path_nodes) >= 2:
                    # 在手动模式下，直接高亮当前选择的路径
                    self.highlight_path(self.current_path_nodes)
                    self.complete_path_creation()
                else:
                    # 实时高亮当前选择的路径
                    self.highlight_path(self.current_path_nodes)
                    self.log_message(f"已选择: {node_id}")
                    self.status_label.config(text=f"已选择: {node_id}，请选择下一个节点")
                    
        else:  # 自动模式
            # 自动模式：只选择起点和终点
            if len(self.current_path_nodes) == 0:
                # 起点必须是主机
                if clicked_node['type'] != 'host':
                    messagebox.showwarning("提示", "路径起点必须是主机")
                    return
                self.current_path_nodes.append(node_id)
                self.highlight_node(node_id, 'green')
                self.log_message(f"选择起点: {node_id}")
                self.status_label.config(text=f"已选择起点: {node_id}，请选择终点")
            elif len(self.current_path_nodes) == 1:
                # 终点必须是主机，且不能是起点
                if clicked_node['type'] != 'host':
                    messagebox.showwarning("提示", "路径终点必须是主机")
                    return
                if node_id == self.current_path_nodes[0]:
                    messagebox.showwarning("提示", "起点和终点不能相同")
                    return
                    
                self.current_path_nodes.append(node_id)
                self.highlight_node(node_id, 'green')
                self.log_message(f"选择终点: {node_id}")
                
                # 计算路径
                try:
                    result = self.backend_api.calculate_path(
                        self.current_path_nodes[0], 
                        node_id, 
                        mode.lower()
                    )
                    if result['success']:
                        self.current_path_nodes = result['path']
                        self.complete_path_creation()
                    else:
                        messagebox.showerror("错误", f"路径计算失败: {result.get('error', '未知错误')}")
                        self.cancel_path_creation()
                except Exception as e:
                    messagebox.showerror("错误", f"路径计算失败: {e}")
                    self.cancel_path_creation()

    def handle_path_deletion_click(self, x, y):
        """处理路径删除时的画布点击"""
        # 找到点击的路径
        clicked_path_info = self.find_clicked_path_at_position(x, y)
        if clicked_path_info:
            path_id, path_data = clicked_path_info
            path = path_data['path']
            color = path_data['color']
            path_str = ' -> '.join(path)
            
            if messagebox.askyesno("确认删除", f"确定要删除路径 {path_str} 吗？"):
                try:
                    result = self.backend_api.delete_path(path_id)
                    if result['success']:
                        # 清除该路径的高亮显示
                        self.clear_specific_path(path_id)
                        self.log_message(f"删除路径: {path_str}")
                        self.status_label.config(text=f"已删除路径: {path_str}")
                    else:
                        messagebox.showerror("错误", f"删除路径失败: {result.get('error', '未知错误')}")
                except Exception as e:
                    messagebox.showerror("错误", f"删除路径失败: {e}")
            
            # 退出删除模式，但不清除其他路径的高亮
            self.exit_path_mode()

    def get_node_at_position(self, x, y):
        """获取指定位置的节点"""
        clicked_items = self.canvas.find_overlapping(x-15, y-15, x+15, y+15)
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if 'host' in tags or 'switch' in tags:
                coords = self.canvas.coords(item)
                if coords:
                    item_x = (coords[0] + coords[2]) / 2
                    item_y = (coords[1] + coords[3]) / 2
                    for node in self.nodes:
                        if abs(node['x'] - item_x) < 1 and abs(node['y'] - item_y) < 1:
                            return node
        return None

    def has_link_between(self, node1, node2):
        """检查两个节点之间是否有链路"""
        for link in self.links:
            if ((link['source'] == node1 and link['target'] == node2) or
                (link['source'] == node2 and link['target'] == node1)):
                return True
        return False

    def highlight_node(self, node_id, color):
        """高亮单个节点"""
        for node in self.nodes:
            if node['id'] == node_id:
                items = self.canvas.find_overlapping(
                    node['x']-25, node['y']-25, 
                    node['x']+25, node['y']+25
                )
                for item in items:
                    tags = self.canvas.gettags(item)
                    if 'host' in tags or 'switch' in tags:
                        self.canvas.itemconfig(item, outline=color, width=3)
                        break

    def highlight_link(self, node1, node2, color):
        """高亮两个节点之间的链路"""
        node_coords = {node['id']: (node['x'], node['y']) for node in self.nodes}
        if node1 in node_coords and node2 in node_coords:
            x1, y1 = node_coords[node1]
            x2, y2 = node_coords[node2]
            line = self.canvas.create_line(x1, y1, x2, y2, 
                                         fill=color, width=3, 
                                         tags=('path_highlight',))
            self.canvas.tag_raise(line)

    def find_clicked_path_at_position(self, x, y):
        """找到点击位置对应的路径，返回(path_id, path_data)"""
        # 检查所有活跃路径
        for path_id, path_data in self.active_paths.items():
            path = path_data['path']
            node_coords = {node['id']: (node['x'], node['y']) for node in self.nodes}
            
            # 检查是否点击在路径的链路上
            for i in range(len(path) - 1):
                source, target = path[i], path[i+1]
                if source in node_coords and target in node_coords:
                    x1, y1 = node_coords[source]
                    x2, y2 = node_coords[target]
                    
                    # 计算点到线段的距离
                    if self.is_point_on_line(x, y, x1, y1, x2, y2, tolerance=10):
                        return (path_id, path_data)
        
        return None
    
    def is_point_on_line(self, px, py, x1, y1, x2, y2, tolerance=10):
        """检查点是否在指定线段上"""
        # 计算线段长度
        line_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if line_length == 0:
            return False
        
        # 计算点到线段的距离
        u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_length ** 2)
        if u < 0 or u > 1:
            return False
        
        intersection_x = x1 + u * (x2 - x1)
        intersection_y = y1 + u * (y2 - y1)
        distance = ((px - intersection_x) ** 2 + (py - intersection_y) ** 2) ** 0.5
        
        return distance <= tolerance

    def complete_path_creation(self):
        """完成路径创建"""
        if not self.current_path_nodes:
            return
            
        path_str = ' -> '.join(self.current_path_nodes)
        
        if messagebox.askyesno("确认创建", f"是否创建路径 {path_str}？"):
            try:
                mode = self.selected_path_mode.get()
                result = self.backend_api.create_path(self.current_path_nodes, mode)
                
                if result['success']:
                    # 为新路径分配颜色
                    path_id = result.get('path_id', str(len(self.active_paths)))
                    color = self.path_colors[self.next_color_index % len(self.path_colors)]
                    self.next_color_index += 1
                    
                    # 存储路径信息
                    path_data = {
                        'path': self.current_path_nodes,
                        'color': color,
                        'items': []
                    }
                    self.active_paths[path_id] = path_data
                    
                    # 高亮显示新路径
                    self.highlight_path_with_color(self.current_path_nodes, color, path_id)
                    
                    self.log_message(f"创建路径成功: {path_str} (颜色: {color})")
                    self.status_label.config(text=f"已创建路径: {path_str}")
                else:
                    messagebox.showerror("错误", f"创建路径失败: {result.get('error', '未知错误')}")
            except Exception as e:
                messagebox.showerror("错误", f"创建路径失败: {e}")
        else:
            self.log_message("取消路径创建")
        
        # 退出创建模式，但不清除高亮
        self.exit_path_mode()

    def clear_path_highlight(self):
        """清除所有路径高亮"""
        # 清除所有路径高亮项
        self.canvas.delete('path_highlight')
        
        # 重置高亮路径
        self.highlighted_path = None
        self.active_paths.clear()
        self.next_color_index = 0
    
    def clear_specific_path(self, path_id):
        """清除特定路径的高亮显示并恢复原始样式"""
        if path_id in self.active_paths:
            # 删除该路径的所有高亮项
            for item in self.active_paths[path_id]['items']:
                try:
                    self.canvas.delete(item)
                except:
                    pass  # 项可能已不存在
            
            # 从活跃路径中移除
            del self.active_paths[path_id]
            
            # 重新绘制整个拓扑以恢复原始样式
            # 注意：这不会清除其他路径的高亮，因为它们存储在active_paths中
            self.redraw_topology()
            
            # 重新绘制其他活跃路径的高亮
            for active_path_id, path_data in self.active_paths.items():
                if active_path_id != path_id:  # 跳过刚删除的路径
                    self.highlight_path_with_color(
                        path_data['path'], 
                        path_data['color'], 
                        active_path_id
                    )
    
    def on_canvas_click(self, event):
        """画布点击事件 - 支持节点拖拽和链路创建/删除"""
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # 处理路径创建模式
        if self.experiment_running and hasattr(self, 'is_creating_path') and self.is_creating_path:
            self.handle_path_creation_click(x, y)
            return
            
        # 处理路径删除模式
        if self.experiment_running and hasattr(self, 'is_delete_mode') and self.is_delete_mode:
            self.handle_path_deletion_click(x, y)
            return
            
        # 实验运行时禁止拓扑编辑
        if self.experiment_running:
            return
            
        # 原始的画布点击逻辑（拓扑编辑模式）
        
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # 查找点击的节点
        clicked_items = self.canvas.find_overlapping(x-10, y-10, x+10, y+10)
        
        # 检查是否点击在现有节点上（用于拖拽）
        clicked_node = None
        clicked_item = None
        
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if 'host' in tags or 'switch' in tags:
                # 获取节点中心坐标
                coords = self.canvas.coords(item)
                if coords:
                    item_x = (coords[0] + coords[2]) / 2
                    item_y = (coords[1] + coords[3]) / 2
                    
                    # 查找对应的节点数据
                    for node in self.nodes:
                        if abs(node['x'] - item_x) < 1 and abs(node['y'] - item_y) < 1:
                            clicked_node = node
                            clicked_item = item
                            break
                break
        
        # 检查是否点击在链路上
        clicked_link = self.find_closest_link(x, y)
        
        if not self.current_tool:
            # 没有选中工具时，支持节点拖拽
            if clicked_node and clicked_item:
                self.drag_data = {
                    'node': clicked_node,
                    'item': clicked_item,
                    'x': event.x,
                    'y': event.y
                }
            return
        
        if self.current_tool == "主机":
            self.add_host(x, y)
        elif self.current_tool == "交换机":
            self.add_switch(x, y)
        elif self.current_tool == "链路":
            # 创建链路 - 必须点击在节点上
            if clicked_item:
                tags = self.canvas.gettags(clicked_item)
                if 'host' in tags or 'switch' in tags:
                    if hasattr(self, 'link_start') and self.link_start:
                        # 完成链路创建
                        self.create_link_between_items(self.link_start, clicked_item)
                        self.link_start = None
                    else:
                        # 开始创建链路
                        self.link_start = clicked_item
                        self.canvas.itemconfig(clicked_item, outline='red')
        elif self.current_tool == "删除":
            # 删除功能 - 优先删除节点，降低删除连接的灵敏度
            if clicked_node:
                self.delete_node(clicked_node)
            else:
                # 只有在没有点击到节点的情况下才检查链路，且降低灵敏度
                clicked_link = self.find_closest_link(x, y)
                if clicked_link:
                    self.delete_link(clicked_link)
        elif clicked_node and clicked_item:
            # 拖拽模式
            self.drag_data = {
                'node': clicked_node,
                'item': clicked_item,
                'x': event.x,
                'y': event.y
            }
    
    def add_host(self, x, y):
        """添加主机"""
        # 获取已存在的主机编号
        existing_hosts = [n for n in self.nodes if n['type'] == 'host']
        host_numbers = []
        
        for host in existing_hosts:
            try:
                # 提取编号，如h1 -> 1, h12 -> 12
                num = int(host['id'][1:])
                host_numbers.append(num)
            except (ValueError, IndexError):
                continue
        
        # 找到最小的可用编号
        next_num = 1
        while next_num in host_numbers:
            next_num += 1
        
        host_id = f"h{next_num}"
        node = {
            'id': host_id,
            'type': 'host',
            'x': x,
            'y': y
        }
        self.nodes.append(node)
        
        # 绘制主机
        item = self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="lightblue", tags="host")
        text = self.canvas.create_text(x, y, text=host_id, tags="host")
        
        self.log_message(f"添加主机: {host_id}")
    
    def add_switch(self, x, y):
        """添加交换机"""
        # 获取已存在的交换机编号
        existing_switches = [n for n in self.nodes if n['type'] == 'switch']
        switch_numbers = []
        
        for switch in existing_switches:
            try:
                # 提取编号，如s1 -> 1, s12 -> 12
                num = int(switch['id'][1:])
                switch_numbers.append(num)
            except (ValueError, IndexError):
                continue
        
        # 找到最小的可用编号
        next_num = 1
        while next_num in switch_numbers:
            next_num += 1
        
        switch_id = f"s{next_num}"
        node = {
            'id': switch_id,
            'type': 'switch',
            'x': x,
            'y': y
        }
        self.nodes.append(node)
        
        # 绘制交换机
        item = self.canvas.create_rectangle(x-15, y-15, x+15, y+15, fill="lightgreen", tags="switch")
        text = self.canvas.create_text(x, y, text=switch_id, tags="switch")
        
        self.log_message(f"添加交换机: {switch_id}")
    
    def create_link_between_items(self, item1, item2):
        """在画布项之间创建链路"""
        # 获取节点信息
        node1 = None
        node2 = None
        
        # 获取item1的坐标
        coords1 = self.canvas.coords(item1)
        if coords1:
            x1, y1 = (coords1[0] + coords1[2]) / 2, (coords1[1] + coords1[3]) / 2
            for node in self.nodes:
                if abs(node['x'] - x1) < 20 and abs(node['y'] - y1) < 20:
                    node1 = node
                    break
        
        # 获取item2的坐标
        coords2 = self.canvas.coords(item2)
        if coords2:
            x2, y2 = (coords2[0] + coords2[2]) / 2, (coords2[1] + coords2[3]) / 2
            for node in self.nodes:
                if abs(node['x'] - x2) < 20 and abs(node['y'] - y2) < 20:
                    node2 = node
                    break
        
        if node1 and node2 and node1 != node2:
            # 检查是否已存在链路
            for link in self.links:
                if ((link['source'] == node1['id'] and link['target'] == node2['id']) or
                    (link['source'] == node2['id'] and link['target'] == node1['id'])):
                    return  # 链路已存在
            
            # 创建新链路
            link = {
                'source': node1['id'],
                'target': node2['id']
            }
            self.links.append(link)
            self.redraw_topology()
            self.log_message(f"创建链路: {node1['id']} <-> {node2['id']}")
    
    def create_link(self, source_id, target_id):
        """通过节点ID创建链路"""
        if source_id != target_id:
            # 检查是否已存在链路
            for link in self.links:
                if ((link['source'] == source_id and link['target'] == target_id) or
                    (link['source'] == target_id and link['target'] == source_id)):
                    return  # 链路已存在
            
            # 创建新链路
            link = {
                'source': source_id,
                'target': target_id
            }
            self.links.append(link)
            self.redraw_topology()
            self.log_message(f"创建链路: {source_id} <-> {target_id}")
    
    def update_links_for_node(self, node):
        """更新节点的所有连接线"""
        # 重绘画布时会自动更新所有链路
        pass
    
    def handle_delete_click(self, x, y):
        """处理删除点击"""
        # 找到点击的对象并删除
        pass
    
    def delete_node(self, node):
        """删除节点及其相关链路"""
        node_id = node['id']
        
        # 删除与该节点相关的所有链路
        self.links = [link for link in self.links 
                     if link['source'] != node_id and link['target'] != node_id]
        
        # 从节点列表中删除
        self.nodes = [n for n in self.nodes if n['id'] != node_id]
        
        # 重绘画布
        self.redraw_topology()
        self.log_message(f"删除节点: {node_id}")
    
    def delete_link(self, link):
        """删除链路"""
        if link in self.links:
            self.links.remove(link)
            self.redraw_topology()
            self.log_message(f"删除链路: {link['source']} <-> {link['target']}")
    
    def find_closest_link(self, x, y, threshold=25):
        """查找最接近点击位置的链路
        Args:
            x, y: 点击坐标
            threshold: 距离阈值（像素），默认25像素降低灵敏度
        """
        min_dist = float('inf')
        closest_link = None

        # 获取节点坐标映射
        node_coords = {node['id']: (node['x'], node['y']) for node in self.nodes}

        for link in self.links:
            source = link.get('source')
            target = link.get('target')

            if source in node_coords and target in node_coords:
                x1, y1 = node_coords[source]
                x2, y2 = node_coords[target]

                # 计算点到线段的距离
                line_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                if line_length == 0:
                    continue

                # 计算投影点
                t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (line_length ** 2)))
                proj_x = x1 + t * (x2 - x1)
                proj_y = y1 + t * (y2 - y1)

                dist = ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5

                if dist < threshold and dist < min_dist:
                    min_dist = dist
                    closest_link = link

        return closest_link
    
    def find_closest_node(self, x, y):
        """查找最近的节点"""
        min_dist = float('inf')
        closest = None
        
        for node in self.nodes:
            dist = ((node['x'] - x) ** 2 + (node['y'] - y) ** 2) ** 0.5
            if dist < min_dist and dist < 20:
                min_dist = dist
                closest = node
        
        return closest
    
    def on_canvas_drag(self, event):
        """画布拖拽事件 - 支持节点移动"""
        # 实验运行时禁止节点拖动
        if self.experiment_running:
            return
            
        if hasattr(self, 'drag_data') and self.drag_data:
            dx = event.x - self.drag_data['x']
            dy = event.y - self.drag_data['y']
            
            # 移动节点图形
            self.canvas.move(self.drag_data['item'], dx, dy)
            
            # 移动节点文本
            node = self.drag_data['node']
            for text_item in self.canvas.find_withtag('text'):
                coords = self.canvas.coords(text_item)
                if coords:
                    text_x = (coords[0] + coords[2]) / 2 if len(coords) == 4 else coords[0]
                    text_y = (coords[1] + coords[3]) / 2 if len(coords) == 4 else coords[1]
                    if abs(text_x - node['x']) < 1 and abs(text_y - node['y']) < 1:
                        self.canvas.move(text_item, dx, dy)
                        break
            
            # 更新节点数据中的位置
            node['x'] += dx
            node['y'] += dy
            
            # 更新连接线
            self.redraw_topology()
            
            self.drag_data['x'] = event.x
            self.drag_data['y'] = event.y

    def on_canvas_release(self, event):
        """画布释放事件"""
        if hasattr(self, 'drag_data'):
            self.drag_data = None
    
    def on_right_click(self, event):
        """右键点击事件 - 统一取消操作"""
        # 取消路径创建/删除模式
        if self.is_creating_path or self.is_delete_mode:
            self.cancel_path_creation()
            self.log_message("右键取消：已退出路径操作模式")
        
        # 取消节点选择
        if hasattr(self, 'selected_nodes') and self.selected_nodes:
            self.selected_nodes.clear()
            self.redraw_topology()
            self.log_message("右键取消：已清除节点选择")
        
        # 取消工具选择
        if self.current_tool:
            self.select_tool(None)
            self.log_message("右键取消：已退出工具选择模式")
    
    def redraw_topology(self):
        """重绘画布 - 确保正确的层级关系：链路(底层) -> 节点形状(中层) -> 编号(顶层)"""
        self.canvas.delete("all")
        
        # 创建节点ID到坐标的映射
        node_coords = {}
        
        # 第1步：绘制链路（最底层）
        for link in self.links:
            source = link.get('source')
            target = link.get('target')
            
            if source in [n['id'] for n in self.nodes] and target in [n['id'] for n in self.nodes]:
                source_node = next(n for n in self.nodes if n['id'] == source)
                target_node = next(n for n in self.nodes if n['id'] == target)
                x1, y1 = source_node['x'], source_node['y']
                x2, y2 = target_node['x'], target_node['y']
                
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2, tags=('link',))
        
        # 第2步：绘制节点形状（中层）
        for node in self.nodes:
            x, y = node['x'], node['y']
            node_id = node['id']
            
            if node['type'] == 'host':
                self.canvas.create_oval(x-15, y-15, x+15, y+15, 
                                      fill="lightblue", outline="black", width=1, 
                                      tags=('host', node_id))
            elif node['type'] == 'switch':
                self.canvas.create_rectangle(x-15, y-15, x+15, y+15, 
                                           fill="lightgreen", outline="black", width=1, 
                                           tags=('switch', node_id))
        
        # 第3步：绘制节点编号（顶层）
        for node in self.nodes:
            x, y = node['x'], node['y']
            node_id = node['id']
            
            # 使用白色背景使文字更清晰
            self.canvas.create_text(x, y, text=node_id, 
                                  font=('Arial', 10, 'bold'),
                                  fill="black",
                                  tags=('text', node_id))
    
    def update_ui_state(self):
        """更新UI状态 - 根据实验状态控制按钮可用性"""
        running = self.experiment_running
        
        if running:
            self.exp_status_label.config(text="实验运行中")
            # 实验运行时禁用某些按钮
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.create_path_btn.config(state='normal')
            self.delete_path_btn.config(state='normal')
            self.algo_combo.config(state='readonly')
            
            # 禁用拓扑设计按钮
            for btn in self.tool_buttons.values():
                btn.config(state='disabled')
        else:
            self.exp_status_label.config(text="实验未启动")
            # 实验未启动时启用所有按钮
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.create_path_btn.config(state='disabled')
            self.delete_path_btn.config(state='disabled')
            self.algo_combo.config(state='disabled')
            
            # 启用拓扑设计按钮
            for btn in self.tool_buttons.values():
                btn.config(state='normal')
            
            # 实验停止时重置路径模式
            self.cancel_path_creation()
    
    def simulate_topology_data(self):
        """模拟拓扑数据"""
        # 模拟从后端获取的拓扑数据
        topology_data = {
            'nodes': [
                {'id': 's1', 'type': 'switch', 'x': 200, 'y': 200},
                {'id': 's2', 'type': 'switch', 'x': 400, 'y': 200},
                {'id': 'h1', 'type': 'host', 'x': 100, 'y': 200},
                {'id': 'h2', 'type': 'host', 'x': 500, 'y': 200}
            ],
            'links': [
                {'source': 'h1', 'target': 's1'},
                {'source': 's1', 'target': 's2'},
                {'source': 's2', 'target': 'h2'}
            ]
        }
        
        self.nodes = topology_data['nodes']
        self.links = topology_data['links']
        self.redraw_topology()
    
    def start_monitoring(self):
        """开始监控"""
        self.log_message("开始网络监控...")
    
    def stop_monitoring(self):
        """停止监控"""
        self.log_message("停止网络监控")
    
    def show_statistics(self):
        """显示统计信息"""
        messagebox.showinfo("统计信息", "网络监控统计信息将在这里显示")
    
    def log_message(self, message):
        """记录日志消息到信息窗口"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)
    
    def _update_status(self):
        """定期更新状态"""
        if self.experiment_running:
            # 这里可以定期从后端获取状态
            pass
        
        self.root.after(1000, self._update_status)
    
    def display_topology(self, topology_data):
        """显示后端返回的拓扑 - 实验启动后仅更新状态，不重新绘制"""
        if not topology_data:
            return
        
        # 实验启动后，我们保留用户设计的拓扑布局
        # 只更新节点和链路的运行状态，不重新绘制
        nodes = topology_data.get('nodes', [])
        links = topology_data.get('edges', topology_data.get('links', []))
        
        # 更新节点状态显示（可选：添加运行状态标记）
        for node in nodes:
            node_id = node.get('id')
            # 可以在这里添加节点运行状态的视觉标记
            
        self.log_message(f"拓扑已激活: {len(nodes)}个节点, {len(links)}条链路")
        
        # 实验运行时不重新绘制拓扑，保持用户原有布局
    
    def clear_topology(self):
        """清除拓扑显示"""
        self.canvas.delete("all")
        self.nodes.clear()
        self.links.clear()
        if hasattr(self, 'selected_nodes'):
            self.selected_nodes.clear()
        if hasattr(self, 'highlighted_path'):
            self.clear_path_highlight()

    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """GUI程序入口"""
    try:
        gui = NetworkTopologyGUI()
        gui.run()
    except Exception as e:
        print(f"启动GUI失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
