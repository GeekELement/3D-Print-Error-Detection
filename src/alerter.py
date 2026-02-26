"""
报警模块

功能：邮件告警、邮件回复处理、Klipper打印机控制

包含：
- send_email: 发送告警邮件（支持附件）
- EmailReplyHandler: 监听邮件回复，实现远程控制
- KlipperClient: 通过Moonraker API控制Klipper打印机
"""

import smtplib
import os
import imaplib
import email
import time
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from config import config


def send_email(to_email: str = "", subject: str = "3D打印异常警报", body: str = "",
               attachment_path: str = "", smtp_server: str = "", smtp_port: int = 465,
               from_email: str = "", password: str = ""):
    """
    发送告警邮件
    
    Args:
        to_email: 接收邮箱地址
        subject: 邮件主题
        body: 邮件正文
        attachment_path: 附件文件路径（可选）
        smtp_server: SMTP服务器地址
        smtp_port: SMTP端口
        from_email: 发送邮箱地址
        password: 发送邮箱授权码
        
    Returns:
        bool: 发送成功返回True，失败返回False
    """
    # 参数为空时从配置读取默认值
    if not to_email:
        to_email = config.get_str('email.to', '')
    if not smtp_server:
        smtp_server = config.get_str('email.smtp.server', 'smtp.qq.com')
    if not smtp_port:
        smtp_port = config.get_int('email.smtp.port', 465)
    if not from_email:
        from_email = config.get_str('email.from', '')
    if not password:
        password = config.get_str('email.password', '')

    # 检查必要配置
    if config.get_bool('email.enabled') and (not from_email or not password):
        print("错误：邮件账号或授权码未配置")
        return False

    try:
        # 构造邮件
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 添加附件（如果有）
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment_path)}"')
                msg.attach(part)

        # 发送邮件（SMTP_SSL用于SSL连接）
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(from_email, password)
            server.send_message(msg)

        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 邮件已发送 → {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件失败：{e}")
        return False


class KlipperClient:
    """
    Klipper Moonraker API 客户端
    
    通过HTTP请求控制Klipper打印机
    
    使用示例：
        client = KlipperClient()
        client.stop_print()  # 停止打印
        client.pause_print()  # 暂停打印
    """
    
    def __init__(self, klipper_url: str = "", api_key: str = ""):
        """
        初始化Klipper客户端
        
        Args:
            klipper_url: Moonraker服务器地址，如 http://192.168.1.100:7125
            api_key: API密钥（可选）
            
        Raises:
            ValueError: 未配置klipper_url时抛出
        """
        self.klipper_url = klipper_url if klipper_url else config.get_str('klipper.url', '')
        self.api_key = api_key if api_key else config.get_str('klipper.api_key', '')
        
        if not self.klipper_url:
            raise ValueError("Klipper URL 必须配置")
        
        # HTTP请求头
        self.headers = {'Content-Type': 'application/json'}
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key

    def _request(self, method: str, endpoint: str, data: dict = None):
        """
        发送HTTP请求到Moonraker API
        
        Args:
            method: HTTP方法，GET或POST
            endpoint: API端点路径
            data: 请求数据（POST时使用）
            
        Returns:
            dict: 响应JSON，失败返回None
        """
        url = f"{self.klipper_url}{endpoint}"
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Klipper API 请求失败：{e}")
            return None

    def stop_print(self):
        """
        停止当前打印任务
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/api/job/cancel")

    def pause_print(self):
        """
        暂停打印
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/api/job/pause")

    def resume_print(self):
        """
        恢复打印
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/api/job/resume")

    def get_job_status(self):
        """
        获取打印任务状态
        
        Returns:
            dict: 任务状态信息，失败返回None
        """
        return self._request("GET", "/api/job")


class EmailReplyHandler:
    """
    邮件回复处理器
    
    功能：监听IMAP邮箱，识别告警邮件的回复，根据指令控制打印机
    
    支持的指令：
    - 回复 "0": 立即停止打印
    - 回复 "1": 继续打印，指定时间内跳过检测
    
    使用示例：
        handler = EmailReplyHandler()
        handler.check_replies()  # 定期调用检查新邮件
        skip_time = handler.get_skip_remaining_time()  # 获取剩余跳过时间
    """
    
    def __init__(self):
        """
        初始化邮件回复处理器
        
        配置项：
        - email_reply.enabled: 是否启用
        - email.from: 邮箱账号
        - email.password: 邮箱授权码
        - email.imap.server: IMAP服务器
        - email.imap.check_interval: 检查间隔
        - email_reply.skip_duration_min: 跳过检测时长（分钟）
        """
        self.enabled = config.get_bool('email_reply.enabled', False)
        self.email_account = config.get_str('email.from', '')
        self.password = config.get_str('email.password', '')
        self.imap_server = config.get_str('email.imap.server', 'imap.qq.com')
        self.check_interval = config.get_int('email.imap.check_interval', 10)
        self.skip_duration_min = config.get_int('email_reply.skip_duration_min', 10)

        # 状态变量
        self.last_check_time = datetime.now()  # 上次检查时间
        self.skip_detection_until = None       # 跳过检测的截止时间

    def _parse_reply_content(self, body):
        """
        解析邮件内容，提取控制指令
        
        Args:
            body: 邮件正文
            
        Returns:
            str: 指令 '0' 或 '1'，未识别返回None
        """
        if not body:
            return None
        body = body.strip().lower()
        # 查找是否包含指令字符
        for cmd in ['0', '1']:
            if cmd in body:
                return cmd
        return None

    def _handle_stop(self):
        """
        处理停止打印指令
        
        当收到指令 "0" 时，调用Klipper API停止打印
        """
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到停止打印指令 (0)")
        try:
            if config.get_bool('klipper.enabled'):
                client = KlipperClient()
                result = client.stop_print()
                if result is not None:
                    print("已向Klipper发送停止打印指令")
                else:
                    print("Klipper停止打印指令发送失败")
            else:
                print("Klipper未启用")
        except Exception as e:
            print(f"停止打印失败：{e}")

    def _handle_continue(self):
        """
        处理继续打印指令
        
        当收到指令 "1" 时，设置跳过检测的截止时间
        """
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到继续打印指令 (1)，{self.skip_duration_min}分钟内不检测")
        # 设置跳过检测的截止时间（当前时间 + 跳过时长）
        self.skip_detection_until = time.time() + self.skip_duration_min * 60

    def _connect(self):
        """
        连接到IMAP服务器
        
        Returns:
            IMAP4对象，连接失败返回None
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_account, self.password)
            return mail
        except Exception as e:
            print(f"连接邮件服务器失败：{e}")
            return None

    def check_replies(self):
        """
        检查邮箱收件箱，处理告警邮件的回复
        
        工作流程：
        1. 连接到IMAP服务器
        2. 搜索上次检查后的未读邮件
        3. 识别回复邮件（主题含"Re:"或"回复"）
        4. 解析邮件内容，提取指令
        5. 执行相应操作
        6. 标记邮件为已读
        """
        if not self.enabled:
            return
        
        current_time = datetime.now()
        mail = self._connect()
        if not mail:
            return
        
        try:
            # 选择收件箱
            mail.select("inbox")
            # 搜索上次检查后的未读邮件
            search_since = self.last_check_time.strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'SINCE {search_since} UNSEEN')
            
            if status != "OK" or not messages[0]:
                self.last_check_time = current_time
                mail.close()
                return
            
            # 逐封处理邮件
            for msg_id in messages[0].split():
                res, msg = mail.fetch(msg_id, "(RFC822)")
                if res != "OK":
                    continue
                
                for response in msg:
                    if isinstance(response, tuple):
                        msg_content = response[1]
                        msg = email.message_from_bytes(msg_content)
                        
                        # 解析邮件主题
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # 判断是否为回复邮件（主题以Re:开头或包含"回复"）
                        is_reply = subject.lower().startswith('re:') or '回复' in subject
                        if is_reply:
                            # 解析邮件正文
                            body = ""
                            if msg.is_multipart():
                                # 多部分邮件，查找text/plain部分
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if isinstance(payload, bytes):
                                            body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                                        else:
                                            body = payload
                                        break
                            else:
                                payload = msg.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                                else:
                                    body = payload
                            
                            # 提取指令并执行
                            command = self._parse_reply_content(body)
                            if command == '0':
                                self._handle_stop()
                            elif command == '1':
                                self._handle_continue()
                
                # 标记邮件为已读
                mail.store(msg_id, '+FLAGS', '\\Seen')
            
            self.last_check_time = current_time
        
        except Exception as e:
            print(f"检查邮件失败：{e}")
        finally:
            mail.logout()

    def get_skip_remaining_time(self):
        """
        获取剩余跳过检测时间
        
        Returns:
            int: 剩余秒数，0表示不在跳过状态
        """
        if self.skip_detection_until:
            remaining = self.skip_detection_until - time.time()
            if remaining > 0:
                return int(remaining)
        return 0