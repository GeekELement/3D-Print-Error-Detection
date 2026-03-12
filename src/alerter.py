"""
报警模块

功能：邮件告警、Bambu Lab打印机控制

包含：
- send_email: 发送告警邮件（支持附件）
- BambuClient: 通过MQTT控制Bambu Lab打印机
"""

import smtplib
import os
import json
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

    if config.get_bool('email.enabled') and (not from_email or not password):
        print("错误：邮件账号或授权码未配置")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment_path)}"')
                msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(from_email, password)
            server.send_message(msg)

        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 邮件已发送 → {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件失败：{e}")
        return False


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
