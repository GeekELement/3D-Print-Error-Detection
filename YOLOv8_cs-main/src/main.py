import time
import os
import cv2
from datetime import datetime
from ultralytics import YOLO
from camera_capture import SimpleCamera
from notify import send_email_alert   # 只使用这一套邮件接口


# ───────────── 配置区 ─────────────
MODEL_PATH = r"C:\Files\3D_Print_Error_Detection\YOLOv8_cs-main\yolov8n.pt"
CAMERA_INDEX = 0

INTERVAL_MIN = 0.1                   # 检测间隔（分钟）
CONF_THRESHOLD = 0.25                # YOLO 检测阈值
ALERT_CONF_THRESHOLD = 0.70          # 报警阈值

PREDICTED_IMAGE_DIR = r"C:\Files\3D_Print_Error_Detection\YOLOv8_cs-main\images\predicted_pictures"

EMAIL_ALERT_ENABLED = True
EMAIL_TO = "geekelement@outlook.com"
EMAIL_FROM = "geekelement@foxmail.com"
EMAIL_PASSWORD = "uxdrpmvghbffdbbj"  # 授权码（不是QQ密码）


# ───────────── 主程序 ─────────────
def main():
    os.makedirs(PREDICTED_IMAGE_DIR, exist_ok=True)

    print("初始化摄像头...")
    camera = SimpleCamera(camera_index=CAMERA_INDEX)

    print("加载 YOLOv8 模型...")
    try:
        model = YOLO(MODEL_PATH)
        print("模型加载完成")
    except Exception as e:
        print(f"模型加载失败：{e}")
        return

    print(f"开始监控，每 {INTERVAL_MIN} 分钟检测一次（Ctrl+C 退出）")
    last_time = time.time()

    try:
        while True:
            now = time.time()
            if now - last_time >= INTERVAL_MIN * 60:
                ts_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{ts_human}] 开始新一轮检测...")

                # 1️⃣ 拍照
                image_path = camera.capture_and_save(prefix="print")

                # 2️⃣ YOLO 推理
                results = model(image_path, conf=CONF_THRESHOLD, verbose=False)[0]

                detected_info = []
                should_alert = False
                alert_details = []

                for box in results.boxes:
                    cls_name = results.names[int(box.cls)]
                    conf = float(box.conf)

                    detected_info.append(f"{cls_name} ({conf:.2f})")

                    if conf >= ALERT_CONF_THRESHOLD:
                        should_alert = True
                        alert_details.append(f"{cls_name} ({conf:.2f})")

                if detected_info:
                    print("检测到：", ", ".join(detected_info))
                else:
                    print("本次未检测到任何目标")

                # 3️⃣ 保存预测图
                ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
                predicted_path = os.path.join(
                    PREDICTED_IMAGE_DIR, f"pred_{ts_file}.jpg"
                )

                annotated = results.plot()
                if cv2.imwrite(predicted_path, annotated):
                    print(f"预测图已保存：{predicted_path}")
                else:
                    print("预测图保存失败，跳过本轮")
                    last_time = now
                    continue

                # 4️⃣ 发送报警邮件
                if should_alert and EMAIL_ALERT_ENABLED:
                    body = (
                        "【3D打印异常警报】\n\n"
                        f"检测时间：{ts_human}\n"
                        f"异常目标：{', '.join(alert_details)}\n\n"
                        "请尽快检查打印机状态。\n"
                        "预测图片已作为附件发送。"
                    )

                    send_email_alert(
                        to_email=EMAIL_TO,
                        subject="【紧急】3D打印检测到异常",
                        body=body,
                        attachment_path=predicted_path,
                        from_email=EMAIL_FROM,
                        password=EMAIL_PASSWORD
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
