#!/usr/bin/env python3
"""
Tmux会话管理器
用于启动和管理Mininet的tmux会话
"""

import subprocess
import os
import time
import logging

logger = logging.getLogger(__name__)

class TmuxManager:
    def __init__(self, session_name="mininet_session", use_sudo=False):
        self.session_name = session_name
        self.session_created = False
        self.use_sudo = use_sudo
    
    def start_session(self, command=None):
        """启动一个新的tmux会话"""
        try:
            # 首先确保tmux服务器正在运行
            self._ensure_tmux_server()
            
            # 检查会话是否已存在
            check_cmd = f"tmux has-session -t {self.session_name} 2>/dev/null"
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"Tmux session {self.session_name} already exists")
                return True
            
            # 创建新会话，使用绝对路径和完整环境
            if command:
                # 确保使用bash shell
                full_command = f"bash -c 'cd /tmp && {command}'"
                cmd = f"tmux new-session -d -s {self.session_name} {full_command}"
            else:
                cmd = f"tmux new-session -d -s {self.session_name}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.session_created = True
                logger.info(f"Tmux session {self.session_name} started successfully")
                
                # 验证会话确实已创建
                if not self.is_session_active():
                    logger.error("Session creation reported success but session not found")
                    return False
                    
                return True
            else:
                logger.error(f"Failed to start tmux session: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting tmux session: {e}")
            return False
            
    def _ensure_tmux_server(self):
        """确保tmux服务器正在运行"""
        try:
            # 启动一个dummy会话来确保tmux服务器运行
            dummy_cmd = "tmux start-server"
            subprocess.run(dummy_cmd, shell=True, capture_output=True)
            
            # 给服务器一点时间启动
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error ensuring tmux server: {e}")
    
    def attach_session(self):
        """附加到tmux会话（供用户手动操作）"""
        try:
            # 首先检查会话是否存在
            if not self.is_session_active():
                logger.error(f"Tmux session {self.session_name} does not exist")
                return False
                
            cmd = f"tmux attach-session -t {self.session_name}"
            # 在独立终端中运行
            subprocess.Popen(cmd, shell=True)
            logger.info(f"Attaching to tmux session {self.session_name}")
            return True
        except Exception as e:
            logger.error(f"Error attaching to tmux session: {e}")
            return False
    
    def get_session_output(self):
        """获取会话的完整输出"""
        try:
            cmd_prefix = ['sudo'] if self.use_sudo else []
            result = subprocess.run(cmd_prefix + ['tmux', 'capture-pane', '-p', '-t', self.session_name], 
                                  capture_output=True, text=True)
            return result.stdout
        except:
            return ""
    
    def send_command(self, command, wait=1):
        """发送命令到会话并等待响应"""
        try:
            cmd_prefix = ['sudo'] if self.use_sudo else []
            
            # 清空当前输出
            # self.clear_pane()
            
            # 发送命令
            subprocess.run(cmd_prefix + ['tmux', 'send-keys', '-t', self.session_name, command, 'Enter'])
            
            # 等待命令执行
            if wait > 0:
                time.sleep(wait)
            
            # 获取输出
            output = self.get_session_output()
            return output
        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return ""
    
    # def clear_pane(self):
    #     """清空会话面板"""
    #     try:
    #         cmd_prefix = ['sudo'] if self.use_sudo else []
    #         subprocess.run(cmd_prefix + ['tmux', 'send-keys', '-t', self.session_name, 'clear', 'Enter'])
    #         return True
    #     except:
    #         return False
    
    def get_prompt_status(self):
        """检查当前是否显示提示符"""
        try:
            output = self.get_session_output()
            lines = output.split('\n')
            for line in reversed(lines):
                if 'mininet>' in line:
                    return True
            return False
        except:
            return False
    
    def kill_session(self):
        """关闭tmux会话"""
        try:
            cmd = f"tmux kill-session -t {self.session_name} 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                self.session_created = False
                logger.info(f"Tmux session {self.session_name} killed")
                return True
            else:
                logger.warning(f"Failed to kill tmux session or session didn't exist")
                return False
                
        except Exception as e:
            logger.error(f"Error killing tmux session: {e}")
            return False
    
    def is_session_active(self):
        """检查会话是否活跃"""
        try:
            cmd = f"tmux has-session -t {self.session_name} 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False