import json
import time
import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from camera import Camera
from detector import DefectDetector
from notify import MailClient
from octoprint_client import OctoPrintClient

class Config:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def get(self, key, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

def main():
    # 加载配置
    config = Config()
    
    # 初始化各个模块
    camera = Camera(config.get('camera_index', 0))
    detector = DefectDetector(config.get('model_path'))
    
    # 初始化邮件客户端
    mail_client = MailClient(
        smtp_server=config.get('smtp_server'),
        smtp_port=config.get('smtp_port'),
        email_address=config.get('email_address'),
        email_password=config.get('email_password'),
        imap_server=config.get('imap_server'),
        imap_port=config.get('imap_port')
    )
    
    # 初始化OctoPrint客户端
    octoprint_client = OctoPrintClient(
        octoprint_url=config.get('octoprint_url'),
        api_key=config.get('octoprint_api_key')
    )
    
    # 初始化静默模式
    silent_mode = False
    silent_until = 0
    
    print("3D打印缺陷智能检测与交互式处理系统启动...")
    
    while True:
        try:
            # 检查是否处于静默模式
            current_time = time.time()
            if silent_mode and current_time < silent_until:
                print(f"系统处于静默模式，剩余时间: {int(silent_until - current_time)}秒")
                time.sleep(60)  # 等待1分钟
                continue
            elif silent_mode and current_time >= silent_until:
                print("静默模式结束")
                silent_mode = False
            
            # USB摄像头抓图
            print("正在捕获图像...")
            frame = camera.capture_frame()
            
            # YOLOv8模型推理
            print("正在进行缺陷检测...")
            results = detector.detect_defects(frame)
            defects = detector.get_defect_info(results)
            
            # 检查是否发现缺陷
            if defects:
                print(f"发现{len(defects)}个缺陷:")
                for defect in defects:
                    print(f"- {defect['class_name']} (置信度: {defect['confidence']:.2f})")
                
                # 发送告警邮件
                print("正在发送告警邮件...")
                recipient_email = config.get('recipient_email', config.get('email_address'))
                subject = "【3D打印告警】检测到打印缺陷！"
                
                # 构建邮件内容
                defect_types = set([d['class_name'] for d in defects])
                defect_list = ', '.join(defect_types)
                
                message = f"在您的打印任务中检测到疑似 [{defect_list}] 缺陷。\n"
                message += "请回复本邮件，输入以下数字进行操作：\n"
                message += "1 - 立即停止打印\n"
                message += "2 - 忽略此次告警，1小时内不再提醒\n"
                message += "\n【系统提示】如果您在10分钟内未回复，打印将自动停止。"
                
                # 发送邮件
                mail_client.send_alert_email(recipient_email, subject, message, frame)
                
                # 等待用户回复（10分钟超时）
                print("等待用户回复...")
                alert_time = current_time
                user_response = mail_client.check_email_replies(alert_time, timeout=600)  # 10分钟超时
                
                if user_response == '1':
                    print("收到用户指令：停止打印")
                    octoprint_client.stop_print()
                elif user_response == '2':
                    print("收到用户指令：进入静默模式")
                    silent_mode = True
                    silent_until = current_time + 3600  # 1小时静默模式
                else:
                    print("用户超时未回复，自动停止打印")
                    octoprint_client.stop_print()
            else:
                print("未发现缺陷")
            
            # 等待1分钟
            print("等待1分钟...")
            time.sleep(60)
            
        except Exception as e:
            print(f"发生错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
