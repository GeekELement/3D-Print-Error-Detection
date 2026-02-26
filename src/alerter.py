"""
报警模块

功能：邮件告警、邮件回复处理、多种固件打印机控制

包含：
- send_email: 发送告警邮件（支持附件）
- EmailReplyHandler: 监听邮件回复，实现远程控制
- KlipperClient: 通过Moonraker API控制Klipper打印机
- OctoPrintClient: 通过API控制OctoPrint打印机
- BambuClient: 通过MQTT控制Bambu Lab打印机
"""

import smtplib
import os
import imaplib
import email
import time
import json
import requests
import paho.mqtt.client as mqtt
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


class OctoPrintClient:
    """
    OctoPrint API 客户端
    
    通过HTTP请求控制OctoPrint打印机
    
    使用示例：
        client = OctoPrintClient()
        client.stop_print()  # 停止打印
        client.pause_print()  # 暂停打印
    """
    
    def __init__(self, octoprint_url: str = "", api_key: str = ""):
        """
        初始化OctoPrint客户端
        
        Args:
            octoprint_url: OctoPrint服务器地址，如 http://192.168.1.100:5000
            api_key: API密钥
            
        Raises:
            ValueError: 未配置octoprint_url时抛出
        """
        self.octoprint_url = octoprint_url if octoprint_url else config.get_str('octoprint.url', '')
        self.api_key = api_key if api_key else config.get_str('octoprint.api_key', '')
        
        if not self.octoprint_url:
            raise ValueError("OctoPrint URL 必须配置")
        
        # 移除末尾斜杠
        self.octoprint_url = self.octoprint_url.rstrip('/')
        
        # HTTP请求头
        self.headers = {'Content-Type': 'application/json'}
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key

    def _request(self, method: str, endpoint: str, data: dict = None):
        """
        发送HTTP请求到OctoPrint API
        
        Args:
            method: HTTP方法，GET或POST
            endpoint: API端点路径
            data: 请求数据（POST时使用）
            
        Returns:
            dict: 响应JSON，失败返回None
        """
        url = f"{self.octoprint_url}/api{endpoint}"
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"OctoPrint API 请求失败：{e}")
            return None

    def stop_print(self):
        """
        停止当前打印任务
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/job", {"command": "cancel"})

    def pause_print(self):
        """
        暂停打印
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/job", {"command": "pause"})

    def resume_print(self):
        """
        恢复打印
        
        Returns:
            dict: API响应，失败返回None
        """
        return self._request("POST", "/job", {"command": "resume"})

    def get_job_status(self):
        """
        获取打印任务状态
        
        Returns:
            dict: 任务状态信息，失败返回None
        """
        return self._request("GET", "/job")


class BambuClient:
    """
    Bambu Lab MQTT 客户端
    
    通过MQTT协议控制Bambu Lab打印机
    
    使用示例：
        client = BambuClient()
        client.stop_print()  # 停止打印
        client.pause_print()  # 暂停打印
    """
    
    def __init__(self, bambu_host: str = "", access_code: str = "", serial_number: str = ""):
        """
        初始化Bambu MQTT客户端
        
        Args:
            bambu_host: Bambu打印机IP地址，如 192.168.1.100
            access_code: 访问代码（打印机设置中的access code）
            serial_number: 打印机序列号
            
        Raises:
            ValueError: 未配置bambu_host时抛出
        """
        self.bambu_host = bambu_host if bambu_host else config.get_str('bambu.host', '')
        self.access_code = access_code if access_code else config.get_str('bambu.access_code', '')
        self.serial_number = serial_number if serial_number else config.get_str('bambu.serial_number', '')
        
        if not self.bambu_host:
            raise ValueError("Bambu 主机地址必须配置")
        
        # MQTT配置
        self.mqtt_port = config.get_int('bambu.mqtt_port', 8883)
        self.request_topic = f"device/{self.serial_number}/request"
        
        self._client = None
        self._connected = False

    def _connect(self):
        """建立MQTT连接"""
        if self._connected and self._client:
            return True
        
        try:
            self._client = mqtt.Client()
            self._client.username_pw_set(self.serial_number, self.access_code)
            self._client.tls_set()
            self._client.connect(self.bambu_host, self.mqtt_port, 60)
            self._client.loop_start()
            self._connected = True
            return True
        except Exception as e:
            print(f"Bambu MQTT 连接失败：{e}")
            return False

    def _publish(self, command: str, params: dict = None):
        """
        发布MQTT命令
        
        Args:
            command: 命令类型 (stop/pause/resume)
            params: 命令参数
            
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        if not self._connect():
            return False
        
        try:
            payload = {
                "command": command,
                "sequence_id": "0"
            }
            if params:
                payload.update(params)
            
            result = self._client.publish(self.request_topic, json.dumps(payload))
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Bambu MQTT 发送失败：{e}")
            return False

    def stop_print(self):
        """
        停止当前打印任务
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        return self._publish("stop_print")

    def pause_print(self):
        """
        暂停打印
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        return self._publish("pause")

    def resume_print(self):
        """
        恢复打印
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        return self._publish("resume")

    def get_job_status(self):
        """
        获取打印任务状态
        
        注意：Bambu通过MQTT主动推送状态，需要订阅report主题才能获取
        这里返回None（需要实现订阅逻辑）
        
        Returns:
            None: 暂不支持直接获取状态
        """
        return None


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

    def _handle_stop(self):
        """
        处理停止打印指令
        
        当收到指令 "0" 时，根据配置调用对应固件的API停止打印
        支持：Klipper、OctoPrint、Bambu Lab
        """
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到停止打印指令 (0)")
        
        printer_type = config.get_str('printer.type', 'none')
        
        # Klipper
        if printer_type == 'klipper':
            try:
                client = KlipperClient()
                result = client.stop_print()
                if result is not None:
                    print("已向Klipper发送停止打印指令")
                else:
                    print("Klipper停止打印指令发送失败")
            except Exception as e:
                print(f"Klipper停止打印失败：{e}")
        
        # OctoPrint
        elif printer_type == 'octoprint':
            try:
                client = OctoPrintClient()
                result = client.stop_print()
                if result is not None:
                    print("已向OctoPrint发送停止打印指令")
                else:
                    print("OctoPrint停止打印指令发送失败")
            except Exception as e:
                print(f"OctoPrint停止打印失败：{e}")
        
        # Bambu Lab
        elif printer_type == 'bambu':
            try:
                client = BambuClient()
                result = client.stop_print()
                if result:
                    print("已向Bambu Lab发送停止打印指令")
                else:
                    print("Bambu Lab停止打印指令发送失败")
            except Exception as e:
                print(f"Bambu Lab停止打印失败：{e}")
        
        elif printer_type == 'none':
            print("未配置打印机控制")

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