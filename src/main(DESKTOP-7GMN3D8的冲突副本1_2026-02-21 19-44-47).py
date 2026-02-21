import time
import os
import cv2
from datetime import datetime
from ultralytics import YOLO
from camera_capture import SimpleCamera
from notify import send_email_alert   # 只使用这一套邮件接口
from email_replier import EmailReplyHandler
from config_loader import config      # 导入 YAML 配置


# ───────────── 主程序 ─────────────
def main():
    # 验证配置
    errors = config.validate()
    if errors:
        print("配置验证失败：")
        for error in errors:
            print(f"  - {error}")
        return

    print("初始化摄像头...")
    camera = SimpleCamera(camera_index=config.get_int('camera.index', 0))

    print("加载 YOLOv8 模型...")
    try:
        model = YOLO(config.get_str('model_path_abs', ''))
        print("模型加载完成")
    except Exception as e:
        print(f"模型加载失败：{e}")
        return

    email_reply_handler = EmailReplyHandler()
    print("邮件回复监听已启动")

    interval_sec = config.get_float('monitoring.interval_sec', 1)
    print(f"开始监控，每 {interval_sec} 秒检测一次（Ctrl+C 退出）")
    last_time = time.time()
    last_email_check = time.time()

    try:
        while True:
            now = time.time()
            
            email_check_interval = config.get_int('email.imap.check_interval', 10)
            if now - last_email_check >= email_check_interval:
                email_reply_handler.check_replies()
                last_email_check = now
            
            skip_remaining = email_reply_handler.get_skip_remaining_time()
            if skip_remaining > 0:
                print(f"跳过检测，剩余 {skip_remaining} 秒")
                time.sleep(5)
                continue
            
            if now - last_time >= interval_sec:
                ts_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{ts_human}] 开始新一轮检测...")

                # 1️⃣ 拍照
                image_path = camera.capture_and_save(prefix="print")

                # 2️⃣ YOLO 推理
                conf_threshold = config.get_float('model.conf_threshold', 0.25)
                results = model(image_path, conf=conf_threshold, verbose=False)[0]

                detected_info = []
                should_alert = False
                alert_details = []

                alert_conf_threshold = config.get_float('model.alert_conf_threshold', 0.70)

                for box in results.boxes:
                    cls_name = results.names[int(box.cls)]
                    conf = float(box.conf)

                    detected_info.append(f"{cls_name} ({conf:.2f})")

                    if conf >= alert_conf_threshold:
                        should_alert = True
                        alert_details.append(f"{cls_name} ({conf:.2f})")

                if detected_info:
                    print("检测到：", ", ".join(detected_info))
                else:
                    print("本次未检测到任何目标")

                # 3️⃣ 保存预测图
                ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
                predicted_dir = config.get_str('predicted_dir_abs', '')
                predicted_path = os.path.join(predicted_dir, f"pred_{ts_file}.jpg")

                annotated = results.plot()
                if cv2.imwrite(predicted_path, annotated):
                    print(f"预测图已保存：{predicted_path}")
                else:
                    print("预测图保存失败，跳过本轮")
                    last_time = now
                    continue

                # 4️⃣ 发送报警邮件
                if should_alert and config.get_bool('email.enabled'):
                    body = (
                        "【3D打印异常警报】\n\n"
                        f"检测时间：{ts_human}\n"
                        f"异常目标：{', '.join(alert_details)}\n\n"
                        "请尽快检查打印机状态。\n"
                        "预测图片已作为附件发送。"
                    )

                    send_email_alert(
                        to_email=config.get_str('email.to', ''),
                        subject="【紧急】3D打印检测到异常",
                        body=body,
                        attachment_path=predicted_path,
                        smtp_server=config.get_str('email.smtp.server', 'smtp.qq.com'),
                        smtp_port=config.get_int('email.smtp.port', 465),
                        from_email=config.get_str('email.from', ''),
                        password=config.get_str('email.password', '')
                    )

                last_time = now

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    except Exception as e:
        print(f"运行时错误：{e}")
    finally:
        camera.release()
        print("摄像头已释放，程序结束")


# ───────────── 入口 ─────────────
if __name__ == "__main__":
    main()
