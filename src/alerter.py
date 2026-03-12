"""
报警模块

功能：邮件告警、多种固件打印机控制

包含：
- send_email: 发送告警邮件（支持附件）
- KlipperClient: 通过Moonraker API控制Klipper打印机
- OctoPrintClient: 通过API控制OctoPrint打印机
- BambuClient: 通过MQTT控制Bambu Lab打印机
"""

import smtplib
import os
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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
    if smtp_port is None:
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


