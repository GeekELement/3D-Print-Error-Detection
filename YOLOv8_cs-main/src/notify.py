import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


def send_email_alert(
    to_email: str,
    subject: str = "3D打印异常警报",
    body: str = "",
    attachment_path: str = None,
    smtp_server: str = "smtp.qq.com",
    smtp_port: int = 465,
    from_email: str = None,
    password: str = None
):
    if not from_email or not password:
        print("错误：邮件账号或授权码未配置")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        # 正文
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 附件（如果有）
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(attachment_path)}"'
                )
                msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(from_email, password)
            server.send_message(msg)

        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 邮件已发送 → {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件失败：{e}")
        return False
