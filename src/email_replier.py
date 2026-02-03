"""
邮件回复监听模块
功能：监听用户对告警邮件的回复，根据回复内容控制打印流程
回复 '0' = 停止打印
回复 '1' = 继续打印且指定时间内不检测
"""
import imaplib
import email
import time
import re
from datetime import datetime
from email.header import decode_header
from config_loader import config


class EmailReplyHandler:
    """邮件回复处理器"""

    def __init__(self):
        self.enabled = config.get_bool('email_reply.enabled', False)
        self.email_account = config.get_str('email.from', '')
        self.password = config.get_str('email.password', '')
        self.imap_server = config.get_str('email.imap.server', 'imap.qq.com')
        self.check_interval = config.get_int('email.imap.check_interval', 10)
        self.subject_prefix = config.get_str('email_reply.subject_prefix', '【3D打印异常警报】')
        self.skip_duration_min = config.get_int('email_reply.skip_duration_min', 10)

        self.last_check_time = datetime.now()
        self.skip_detection_until = None
        self.pending_commands = {}

    def _parse_reply_content(self, body):
        """解析回复内容，提取命令"""
        if not body:
            return None
        
        body = body.strip().lower()
        
        for cmd in ['0', '1']:
            if cmd in body:
                return cmd
        
        return None

    def _handle_stop(self, msg_id):
        """处理停止打印命令"""
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到停止打印指令 (0)，正在停止打印...")
        
        try:
            from klipper_client import KlipperClient
            if config.get_bool('klipper.enabled'):
                client = KlipperClient()
                result = client.stop_print()
                if result is not None:
                    print("已向Klipper发送停止打印指令")
                else:
                    print("Klipper停止打印指令发送失败")
            else:
                print("Klipper未启用，跳过停止打印指令")
        except Exception as e:
            print(f"停止打印失败：{e}")

    def _handle_continue(self, msg_id):
        """处理继续打印命令"""
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到继续打印指令 (1)，{self.skip_duration_min}分钟内不检测")
        
        self.skip_detection_until = time.time() + self.skip_duration_min * 60

    def _connect(self):
        """连接到IMAP服务器"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_account, self.password)
            return mail
        except Exception as e:
            print(f"连接邮件服务器失败：{e}")
            return None

    def check_replies(self):
        """检查邮件回复"""
        if not self.enabled:
            print("[调试] 邮件回复处理未启用")
            return
        
        print(f"[调试] 开始检查邮件，间隔 {self.check_interval} 秒")
        
        current_time = datetime.now()
        
        mail = self._connect()
        if not mail:
            print("[调试] 连接邮件服务器失败")
            return
        
        try:
            print("[调试] 已连接邮箱，开始搜索邮件...")
            mail.select("inbox")
            
            search_since = self.last_check_time.strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'SINCE {search_since} UNSEEN')
            
            if status != "OK":
                print(f"[调试] 搜索邮件失败，状态：{status}")
                self.last_check_time = current_time
                mail.close()
                return
            
            if not messages[0]:
                print("[调试] 未找到未读邮件")
                self.last_check_time = current_time
                mail.close()
                return
            
            print(f"[调试] 找到 {len(messages[0].split())} 封未读邮件")
            
            for msg_id in messages[0].split():
                print(f"[调试] 处理邮件 ID：{msg_id}")
                res, msg = mail.fetch(msg_id, "(RFC822)")
                
                if res != "OK":
                    print(f"[调试] 获取邮件失败，状态：{res}")
                    continue
                
                for response in msg:
                    if isinstance(response, tuple):
                        msg_content = response[1]
                        msg = email.message_from_bytes(msg_content)
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        print(f"[调试] 邮件主题：{subject}")

                        is_reply = subject.lower().startswith('re:') or '回复' in subject
                        print(f"[调试] 是否为回复邮件：{is_reply}")

                        if is_reply:
                            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 收到告警邮件回复：{subject}")
                            
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if isinstance(payload, bytes):
                                            body = payload.decode(
                                                part.get_content_charset() or "utf-8", errors="replace"
                                            )
                                        else:
                                            body = payload
                                        break
                            else:
                                payload = msg.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body = payload.decode(
                                        msg.get_content_charset() or "utf-8", errors="replace"
                                    )
                                else:
                                    body = payload
                            
                            print(f"[调试] 邮件内容：{body}")
                            
                            command = self._parse_reply_content(body)
                            print(f"[调试] 识别的指令：{command}")
                            
                            if command:
                                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 识别到指令：{command}")
                                if command == '0':
                                    self._handle_stop(msg_id)
                                elif command == '1':
                                    self._handle_continue(msg_id)
                            else:
                                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 未识别到有效指令（回复0停止，回复1继续）")
                        else:
                            print(f"[调试] 邮件回复不匹配，跳过")
                
                mail.store(msg_id, '+FLAGS', '\\Seen')
            
            self.last_check_time = current_time
            print("[调试] 本次邮件检查完成")
        
        except Exception as e:
            print(f"[调试] 检查邮件失败：{e}")
        finally:
            mail.logout()

    def is_skipping_detection(self):
        """检查是否跳过检测"""
        if self.skip_detection_until and time.time() < self.skip_detection_until:
            return True
        return False

    def get_skip_remaining_time(self):
        """获取剩余跳过时间（秒）"""
        if self.skip_detection_until:
            remaining = self.skip_detection_until - time.time()
            if remaining > 0:
                return int(remaining)
        return 0


if __name__ == "__main__":
    handler = EmailReplyHandler()
    print("邮件回复监听模块测试")
    print("等待回复中...")
    
    while True:
        handler.check_replies()
        time.sleep(handler.check_interval)
