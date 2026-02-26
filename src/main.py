"""
3D打印异常检测系统 - 主程序

功能：定时捕获摄像头画面，使用YOLOv8模型检测打印缺陷，
      发现异常时发送邮件告警，并支持邮件回复远程控制打印机。
"""

import time
import os
import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from camera import Camera, cleanup_old_images
from alerter import send_email, EmailReplyHandler
from config import config
from device import CudaUtils


def main():
    """
    主函数：初始化各模块并进入监控循环
    
    流程：
    1. 验证配置并创建必要目录
    2. 初始化CUDA设备、摄像头、YOLO模型、邮件回复处理器
    3. 进入循环：拍照 -> 检测 -> 保存 -> 告警
    """
    
    # ───────────── 初始化阶段 ─────────────
    
    # 1. 验证配置合法性
    errors = config.validate()
    if errors:
        print("配置验证失败：")
        for error in errors:
            print(f"  - {error}")
        return

    # 2. 确保图片保存目录存在
    config.ensure_directories()
    
    # 3. 初始化CUDA设备
    cuda_utils = CudaUtils(config)
    cuda_utils.print_info()

    # 4. 初始化摄像头
    print("初始化摄像头...")
    camera = Camera(camera_index=config.get_int('camera.index', 0))

    # 5. 加载YOLOv8模型
    print("加载 YOLOv8 模型...")
    try:
        model = YOLO(config.get_str('model_path_abs', ''))
        # 根据CUDA可用性决定使用GPU还是CPU
        if cuda_utils.should_use_cuda:
            model.to('cuda')
        print("模型加载完成")
    except Exception as e:
        print(f"模型加载失败：{e}")
        return

    # 6. 初始化邮件回复处理器（用于远程控制）
    email_reply_handler = EmailReplyHandler()
    print("邮件回复监听已启动")

    # ───────────── 监控循环阶段 ─────────────
    
# 读取配置参数
    interval_sec = config.get_float('monitoring.interval_sec', 1)  # 检测间隔
    max_captured = config.get_int('camera.max_captured', 3)
    max_predicted = config.get_int('camera.max_predicted', 3)
    
    print(f"开始监控，每 {interval_sec} 秒检测一次（Ctrl+C 退出）")
    
    # 状态变量
    last_time = time.time()           # 上次检测时间
    last_email_check = time.time()    # 上次检查邮件时间

    try:
        while True:
            now = time.time()
            
            # 1. 定期检查邮件回复（用户可能通过邮件控制打印机）
            email_check_interval = config.get_int('email.imap.check_interval', 10)
            if now - last_email_check >= email_check_interval:
                email_reply_handler.check_replies()
                last_email_check = now
            
            # 2. 如果用户回复"继续打印"，跳过本次检测
            skip_remaining = email_reply_handler.get_skip_remaining_time()
            if skip_remaining > 0:
                print(f"跳过检测，剩余 {skip_remaining} 秒")
                time.sleep(min(5, skip_remaining))
                continue
            
            # 3. 达到检测间隔，开始新一轮检测
            if now - last_time >= interval_sec:
                ts_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{ts_human}] 开始新一轮检测...")

                # ───────────── 检测步骤 1: 拍照 ─────────────
                image_path = camera.capture_and_save(prefix="print", cleanup=True)
                
                # 跳过未保存的图片（视频模式帧间隔控制）
                if image_path is None:
                    last_time = now
                    continue

                # ───────────── 检测步骤 2: YOLO 推理 ─────────────
                # 获取检测阈值
                conf_threshold = config.get_float('model.conf_threshold', 0.25)
                # 执行推理，返回结果列表，取第一个结果
                results = model(image_path, conf=conf_threshold, verbose=False)[0]

                # 解析检测结果
                detected_info = []       # 记录本次检测到的目标信息
                should_alert = False     # 是否需要发送告警
                alert_details = []       # 告警详情

                # 读取告警阈值配置
                alert_conf_threshold = config.get_float('model.alert_conf_threshold', 0.70)
                spaghetti_area_threshold = config.get_float('model.spaghetti_area_threshold', 5000)

                # 分类处理检测到的目标
                other_faults = []        # 非spaghetti的其他故障
                spaghetti_boxes = []     # 所有spaghetti检测框

                # 遍历所有检测框
                for box in results.boxes:
                    cls_name = results.names[int(box.cls)]  # 类别名称
                    conf = float(box.conf)                  # 置信度
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)  # 边界框坐标

                    # 区分spaghetti和其他故障类型
                    if cls_name == "spaghetti":
                        spaghetti_boxes.append((conf, xyxy))
                    else:
                        other_faults.append(f"{cls_name}: {conf:.2f}")

                # ───────────── 处理 spaghetti 检测结果 ─────────────
                if spaghetti_boxes:
                    img_height, img_width = results.orig_img.shape[:2]
                    
                    # 计算spaghetti区域并集面积
                    # 优化：单框时直接计算，多框时使用mask计算并集
                    if len(spaghetti_boxes) == 1:
                        # 单个检测框，直接计算面积
                        x1, y1, x2, y2 = spaghetti_boxes[0][1]
                        spaghetti_total_area = max(0, min(x2, img_width) - max(0, x1)) * \
                                               max(0, min(y2, img_height) - max(0, y1))
                    else:
                        # 多个检测框，使用mask计算并集（处理重叠情况）
                        mask = np.zeros((img_height, img_width), dtype=np.uint8)
                        for conf, xyxy in spaghetti_boxes:
                            x1, y1, x2, y2 = xyxy
                            # 边界检查，防止框超出图片范围
                            x1, x2 = max(0, min(x1, img_width)), max(0, min(x2, img_width))
                            y1, y2 = max(0, min(y1, img_height)), max(0, min(y2, img_height))
                            mask[y1:y2, x1:x2] = 1
                        spaghetti_total_area = int(np.sum(mask))
                    
                    print(f"[调试] 炒面框数量: {len(spaghetti_boxes)}, 并集总面积: {spaghetti_total_area}")
                    
                    # 获取最高置信度
                    max_conf = max(conf for conf, _ in spaghetti_boxes)
                    
                    # 记录检测信息
                    detected_info.append(f"spaghetti (最大置信度:{max_conf:.2f}, 总面积:{spaghetti_total_area})")
                    
                    # 判断是否触发告警（同时满足置信度和面积阈值）
                    if max_conf >= alert_conf_threshold and spaghetti_total_area >= spaghetti_area_threshold:
                        should_alert = True
                        alert_details.append(f"炒面 (置信度:{max_conf:.2f}, 总面积:{spaghetti_total_area}px²)")
                    else:
                        print(f"  -> 炒面未达到告警条件(置信度:{max_conf:.2f}/{alert_conf_threshold}, "
                              f"总面积:{spaghetti_total_area}/{spaghetti_area_threshold})")

                # 打印检测结果摘要
                if detected_info:
                    print("检测到：", ", ".join(detected_info))
                if other_faults:
                    print("其他故障：", ", ".join(other_faults))
                if not detected_info and not other_faults:
                    print("本次未检测到任何目标")

                # ───────────── 检测步骤 3: 保存预测图 ─────────────
                ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
                predicted_dir = config.get_str('predicted_dir_abs', '')
                predicted_path = os.path.join(predicted_dir, f"pred_{ts_file}.jpg")

                # 绘制标注框并保存
                annotated = results.plot()
                if cv2.imwrite(predicted_path, annotated):
                    print(f"预测图已保存：{predicted_path}")
                    # 清理旧预测图
                    if max_predicted != 0:
                        cleanup_old_images(predicted_dir, max_predicted)
                else:
                    print("预测图保存失败，跳过本轮")
                    last_time = now
                    continue

                # ───────────── 检测步骤 4: 发送告警邮件 ─────────────
                if should_alert and config.get_bool('email.enabled'):
                    # 构造告警邮件内容
                    other_faults_info = f"其他故障：{', '.join(other_faults)}" if other_faults else "无"
                    body = (
                        "【3D打印异常警报】\n\n"
                        f"检测时间：{ts_human}\n"
                        f"炒面告警：{', '.join(alert_details)}\n"
                        f"{other_faults_info}\n\n"
                        "请尽快检查打印机状态。\n"
                        "预测图片已作为附件发送。"
                    )

                    # 发送邮件
                    send_email(
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

            # 空闲时短暂休眠，避免CPU空转
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    except Exception as e:
        print(f"运行时错误：{e}")
    finally:
        # 确保释放摄像头资源
        camera.release()
        print("摄像头已释放，程序结束")


if __name__ == "__main__":
    # 程序入口：仅在直接运行本文件时执行main()
    main()