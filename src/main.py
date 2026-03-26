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
from alerter import send_email
from config import config
from device import CudaUtils
import threading
import bambulabs_api as bl


def start_web_app():
    """在后台线程中启动 web 应用"""
    import webui as web_module
    web_port = config.get_int('app.web_port', 5000)
    print(f"Web 应用已启动，访问 http://localhost:{web_port} 查看监控面板")

    # 使用socketio的background task来自动连接（在socketio上下文内）
    web_module.socketio.start_background_task(auto_connect_and_notify)

    web_module.socketio.run(web_module.app, host='0.0.0.0', port=web_port, debug=False, log_output=False, allow_unsafe_werkzeug=True)

def auto_connect_and_notify():
    """自动连接并通知前端"""
    import webui as web_module
    import time
    import bambulabs_api as bl
    
    source = config.get_str('camera.source', 'local')
    if source != 'a1':
        return
    
    host = config.get_str('printer.host', '')
    access_code = config.get_str('printer.access_code', '')
    serial_number = config.get_str('printer.serial_number', '')
    
    if not host:
        return
    
    time.sleep(2)  # 等待网页先连接
    
    print(f"自动连接到 {host}...")
    web_module.socketio.emit('log', {'message': f'Auto connecting to {host}...'})
    
    web_module.printer = bl.Printer(host, access_code, serial_number)
    web_module.printer.connect()
    web_module.socketio.emit('log', {'message': 'TCP Connected'})
    web_module.printer.mqtt_start()
    
    for i in range(10):
        time.sleep(1)
        if web_module.printer.mqtt_client_connected():
            break
    
    if not web_module.printer.mqtt_client_connected():
        web_module.socketio.emit('log', {'message': 'MQTT failed'})
        return
    
    web_module.socketio.emit('log', {'message': 'MQTT connected'})
    web_module.running = True
    web_module.camera_running = True
    web_module.socketio.start_background_task(web_module.status_loop)
    
    try:
        web_module.printer.camera_start()
        web_module.socketio.start_background_task(web_module.camera_loop)
        web_module.socketio.emit('log', {'message': 'Camera started'})
    except Exception as e:
        web_module.socketio.emit('log', {'message': f'Camera error: {e}'})
    
    # 发送connected事件，启用前端control按钮
    web_module.socketio.emit('connected', {'status': True})
    print("自动连接成功")


class DetectionHistory:
    """多帧检测历史"""
    
    def __init__(self, max_history: int = 100):
        """
        初始化检测历史
        
        Args:
            max_history: 最大保留历史帧数，防止内存泄漏，默认100
        """
        self.frames = []  # 每帧检测结果
        self._alerted = False  # 是否已发送过告警
        self._max_history = max_history
    
    def add_frame(self, has_spaghetti: bool, boxes: list, max_conf: float = 0, total_area: int = 0):
        """添加一帧检测结果"""
        self.frames.append({
            'spaghetti': has_spaghetti,
            'boxes': boxes,
            'conf': max_conf,
            'area': total_area,
            'timestamp': time.time()
        })
        self._alerted = False
        
        # 限制历史长度，防止内存泄漏
        if len(self.frames) > self._max_history:
            # 保留最近的帧，但确保至少保留 required_frames 数量的阳性帧用于判断
            self._trim_old_frames()
    
    def _trim_old_frames(self):
        """清理旧帧，保留最近的一半数据"""
        # 简单的策略：保留最近的一半历史
        keep_count = self._max_history // 2
        self.frames = self.frames[-keep_count:]
    
    def get_positive_frames(self):
        """获取所有阳性帧"""
        return [f for f in self.frames if f['spaghetti'] and f['boxes']]
    
    def check_multi_frame_alert(self, required_frames: int, area_threshold: float = 5000) -> tuple:
        """
        检查是否满足多帧告警条件
        
        逻辑：
        1. 阳性帧计数 >= required_frames
        2. 当前帧面积 >= 阈值
        
        触发后清零重新计数
        
        Returns:
            (should_alert, details)
        """
        if self._alerted:
            return False, ""
        
        positive_count = len(self.get_positive_frames())
        
        # 阳性帧数不足
        if positive_count < required_frames:
            return False, f"阳性帧不足 ({positive_count}/{required_frames})"
        
        # 检查当前帧的面积
        current_frame = self.frames[-1]
        current_area = current_frame['area']
        current_conf = current_frame['conf']
        
        print(f"  -> 多帧检查: 阳性{positive_count}帧, "
              f"当前帧面积:{current_area}px², 置信度:{current_conf:.2f}")
        
        # 当前帧面积>=阈值 才告警
        if current_area >= area_threshold:
            self._alerted = True
            return True, f"阳性{positive_count}帧, 当前帧面积:{current_area}px²"
        
        return False, f"当前帧面积不足 ({current_area}/{area_threshold})"
    
    def reset_alert(self):
        """重置告警状态，允许再次告警"""
        self._alerted = False
    
    def clear(self):
        """清空历史"""
        self.frames = []
        self._alerted = False


def main():
    """
    主函数：初始化各模块并进入监控循环
    
    流程：
    1. 验证配置并创建必要目录
    2. 初始化CUDA设备、摄像头、YOLO模型、邮件回复处理器
    3. 进入循环：拍照 -> 检测 -> 保存 -> 告警
    """
    
    # ───────────── 初始化阶段 ─────────────
    
    # 1. 确保图片保存目录存在（先创建目录，再验证）
    config.ensure_directories()
    
    # 2. 验证配置合法性
    errors = config.validate()
    if errors:
        print("配置验证失败：")
        for error in errors:
            print(f"  - {error}")
        return
    
    # 3. 初始化CUDA设备
    cuda_utils = CudaUtils(config)
    cuda_utils.print_info()

    # 4. 启动 Web 应用（后台线程）
    web_thread = threading.Thread(target=start_web_app, daemon=True)
    web_thread.start()
    time.sleep(1)

    # 5. 初始化摄像头
    print("初始化摄像头...")
    camera_source = config.get_str('camera.source', 'local')
    
    if camera_source == 'a1':
        # 等待webui连接打印机
        print("等待WebUI自动连接打印机...")
        import webui as web_module
        time.sleep(3)  # 等待webui启动连接
        
        # 等待webui连接打印机和相机
        max_wait = 30
        for i in range(max_wait):
            if web_module.is_printer_connected() and web_module.is_camera_ready():
                print("A1相机已就绪")
                break
            time.sleep(1)
            if i % 5 == 0:
                print(f"  等待中... ({i}/{max_wait})")
        else:
            print("错误：A1相机未就绪，请确保已在网页端连接打印机")
            return
        
        # 等待相机获取到画面
        time.sleep(2)
        
        # 使用a1模式从webui获取图像
        camera = Camera(source='a1')
    else:
        camera = Camera(camera_index=config.get_int('camera.index', 0))

    # 6. 加载YOLOv8模型
    print("加载 YOLO 模型...")
    try:
        model = YOLO(config.get_str('model_path_abs', ''))
        # 根据CUDA可用性决定使用GPU还是CPU
        if cuda_utils.should_use_cuda:
            model.to('cuda')
        print("模型加载完成")
    except Exception as e:
        print(f"模型加载失败：{e}")
        return

    # 6. 初始化多帧检测历史
    multi_frame_enabled = config.get_bool('multi_frame.enabled', True)
    detection_history = DetectionHistory() if multi_frame_enabled else None
    
    # 多帧检测配置
    required_frames = config.get_int('multi_frame.required_frames', 5)
    spaghetti_area_threshold = config.get_float('multi_frame.area_threshold', 900)
    
    if multi_frame_enabled:
        print(f"多帧检测已启用: 阳性帧数>={required_frames}时验证面积, 面积阈值:{spaghetti_area_threshold}px²")

    # 读取 ROI 配置
    roi_enabled = config.get_bool('camera.roi.enabled', False)
    roi_box = None
    if roi_enabled:
        x1 = config.get_int('camera.roi.x1', 0)
        y1 = config.get_int('camera.roi.y1', 0)
        x2 = config.get_int('camera.roi.x2', 0)
        y2 = config.get_int('camera.roi.y2', 0)
        if x2 > x1 and y2 > y1:
            roi_box = (x1, y1, x2, y2)
            print(f"ROI区域已启用: 左上({x1},{y1}), 右下({x2},{y2})")
        else:
            print("ROI配置无效，跳过")

    # ───────────── 监控循环阶段 ─────────────
    
# 读取配置参数
    interval_sec = config.get_float('monitoring.interval_sec', 1)  # 检测间隔
    max_captured = config.get_int('camera.max_captured', 3)
    max_predicted = config.get_int('camera.max_predicted', 3)
    
    print(f"开始监控，每 {interval_sec} 秒检测一次（Ctrl+C 退出）")
    
    # 状态变量
    last_time = time.time()           # 上次检测时间

    try:
        while True:
            now = time.time()
            
            # 达到检测间隔，开始新一轮检测
            if now - last_time >= interval_sec:
                ts_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ───────────── 检测步骤 0: 检查打印状态 ─────────────
                # 注意：video 模式是调试模式，优先级最高，不需要检查打印状态
                # 获取实际的相机模式（Camera 内部会判断 video_path 优先级）
                actual_camera_source = camera.source if hasattr(camera, 'source') else camera_source
                if actual_camera_source == 'a1':
                    import webui as web_module
                    if web_module.printer and web_module.printer.mqtt_client_connected():
                        try:
                            status = web_module.printer.mqtt_dump()
                            if "print" in status:
                                ps = status["print"]
                                gcode_state = ps.get("gcode_state", "unknown").upper()
                                state_map = {
                                    "IDLE": "空闲",
                                    "PRINTING": "打印中",
                                    "PAUSED": "已暂停",
                                    "FINISHED": "已完成",
                                    "FAILED": "失败",
                                    "RUNNING": "打印中"
                                }
                                state_name = state_map.get(gcode_state, gcode_state)
                                print(f"\n[{ts_human}] 打印状态: {state_name} ({gcode_state})")
                                
                                # PRINTING 和 RUNNING 都表示正在打印
                                if gcode_state not in ["PRINTING", "RUNNING"]:
                                    print("  -> 打印未进行，跳过检测")
                                    last_time = time.time()
                                    time.sleep(60)
                                    continue
                                print("  -> 打印进行中，开始检测")
                        except Exception as e:
                            print(f"  -> 获取打印状态失败: {e}，继续检测")
                
                print(f"\n[{ts_human}] 开始新一轮检测...")

                # ───────────── 检测步骤 1: 拍照 ─────────────
                image_path = camera.capture_and_save(prefix="print", cleanup=True)
                
                # 跳过未保存的图片（视频模式帧间隔控制）
                if image_path is None:
                    continue

                # ───────────── 检测步骤 1.5: 亮度检测 ─────────────
                # 加载图片进行亮度检测
                img_for_brightness = cv2.imread(image_path)
                if img_for_brightness is not None:
                    # 转换为灰度图
                    gray = cv2.cvtColor(img_for_brightness, cv2.COLOR_BGR2GRAY)

                    # 使用ROI区域进行亮度检测（如果配置了ROI）
                    if roi_box:
                        rx1, ry1, rx2, ry2 = roi_box
                        roi_gray = gray[ry1:ry2, rx1:rx2]
                        roi_desc = "ROI"
                    else:
                        # 未配置ROI时使用全图
                        roi_gray = gray
                        roi_desc = "全图"

                    # 使用多种指标综合评估亮度，避免LED过曝或极端值影响
                    mean_brightness = np.mean(roi_gray)           # 平均值
                    median_brightness = np.median(roi_gray)       # 中位数（更鲁棒，不受极端值影响）
                    percentile_25 = np.percentile(roi_gray, 25)   # 25%分位数（暗部亮度）

                    # 综合亮度评分：中位数占主要权重，暗部亮度占次要权重
                    # 这样可以避免LED过曝拉高平均值，同时确保暗部不要太黑
                    composite_brightness = median_brightness * 0.6 + percentile_25 * 0.4

                    # 获取亮度阈值配置，默认35（综合评分建议稍高一些）
                    brightness_threshold = config.get_float('monitoring.brightness_threshold', 35.0)

                    print(f"  -> 亮度检测({roi_desc}) - 均值:{mean_brightness:.1f} 中位数:{median_brightness:.1f} "
                          f"25%分位:{percentile_25:.1f} 综合评分:{composite_brightness:.1f} (阈值:{brightness_threshold})")

                    # 使用综合评分判断，更鲁棒
                    if composite_brightness < brightness_threshold:
                        print(f"  -> 亮度过低，跳过本次检测")
                        last_time = time.time()
                        continue

                # ───────────── 检测步骤 1.6: 模糊检测 ─────────────
                if img_for_brightness is not None:
                    # 使用ROI区域进行模糊检测（如果配置了ROI）
                    if roi_box:
                        rx1, ry1, rx2, ry2 = roi_box
                        roi_gray = gray[ry1:ry2, rx1:rx2]
                        roi_desc = f"ROI({rx1},{ry1})->({rx2},{ry2})"
                    else:
                        # 未配置ROI时使用全图
                        roi_gray = gray
                        roi_desc = "全图"

                    # 使用拉普拉斯算子计算清晰度
                    laplacian_var = cv2.Laplacian(roi_gray, cv2.CV_64F).var()

                    # 获取模糊阈值配置，默认100（值越小表示越模糊）
                    blur_threshold = config.get_float('monitoring.blur_threshold', 100.0)

                    print(f"  -> 模糊检测 - {roi_desc} 清晰度:{laplacian_var:.1f} (阈值:{blur_threshold})")

                    # 如果清晰度低于阈值，说明图片过于模糊
                    if laplacian_var < blur_threshold:
                        print(f"  -> 图片过于模糊，跳过本次检测")
                        last_time = time.time()
                        continue

                # ───────────── 检测步骤 2: YOLO 推理 ─────────────
                # 获取检测阈值
                conf_threshold = config.get_float('model.conf_threshold', 0.25)
                
                # 执行推理（使用原图，不裁剪）
                results = model(image_path, conf=conf_threshold, verbose=False)[0]
                
                # 如果启用了ROI，过滤检测框，只保留ROI区域内的检测结果
                if roi_box:
                    x1, y1, x2, y2 = roi_box
                    filtered_boxes = []
                    for box in results.boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        cx = (xyxy[0] + xyxy[2]) / 2
                        cy = (xyxy[1] + xyxy[3]) / 2
                        if x1 <= cx <= x2 and y1 <= cy <= y2:
                            filtered_boxes.append(box)
                    results.boxes = filtered_boxes
                    print(f"ROI过滤: ({x1},{y1}) -> ({x2},{y2}), 保留 {len(filtered_boxes)} 个检测框")

                # 解析检测结果
                detected_info = []       # 记录本次检测到的目标信息
                should_alert = False     # 是否需要发送告警
                alert_details = []       # 告警详情

                # 读取告警阈值配置（从多帧检测配置中读取）
                alert_conf_threshold = config.get_float('multi_frame.alert_conf_threshold', 0.8)

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
                # 先添加到历史记录（无论是否达到单帧阈值）
                current_has_spaghetti = False
                spaghetti_total_area = 0
                max_conf = 0
                
                if spaghetti_boxes:
                    img_height, img_width = results.orig_img.shape[:2]
                    
                    # 计算spaghetti区域并集面积
                    if len(spaghetti_boxes) == 1:
                        x1, y1, x2, y2 = spaghetti_boxes[0][1]
                        spaghetti_total_area = max(0, min(x2, img_width) - max(0, x1)) * \
                                               max(0, min(y2, img_height) - max(0, y1))
                    else:
                        mask = np.zeros((img_height, img_width), dtype=np.uint8)
                        for conf, xyxy in spaghetti_boxes:
                            x1, y1, x2, y2 = xyxy
                            x1, x2 = max(0, min(x1, img_width)), max(0, min(x2, img_width))
                            y1, y2 = max(0, min(y1, img_height)), max(0, min(y2, img_height))
                            mask[y1:y2, x1:x2] = 1
                        spaghetti_total_area = int(np.sum(mask))
                    
                    max_conf = max(conf for conf, _ in spaghetti_boxes)
                    print(f"[调试] 炒面框数量: {len(spaghetti_boxes)}, 并集总面积: {spaghetti_total_area}")
                    detected_info.append(f"spaghetti (最大置信度:{max_conf:.2f}, 总面积:{spaghetti_total_area})")
                    
                    # 达到单帧阈值才标记为阳性帧
                    if max_conf >= alert_conf_threshold and spaghetti_total_area >= spaghetti_area_threshold:
                        current_has_spaghetti = True
                    else:
                        print(f"  -> 炒面未达到单帧告警条件(置信度:{max_conf:.2f}/{alert_conf_threshold}, "
                              f"总面积:{spaghetti_total_area}/{spaghetti_area_threshold})")

                # ───────────── 添加到多帧历史 ─────────────
                if detection_history:
                    detection_history.add_frame(current_has_spaghetti, spaghetti_boxes, max_conf, spaghetti_total_area)
                    
                    # 多帧检测：连续N帧阳性 + 第N帧面积验证
                    should_alert, alert_detail = detection_history.check_multi_frame_alert(
                        required_frames=required_frames,
                        area_threshold=spaghetti_area_threshold
                    )
                    
                    if should_alert:
                        alert_details.append(f"炒面 ({alert_detail})")
                    else:
                        if alert_detail:
                            print(f"  -> {alert_detail}")
                else:
                    # 未启用多帧，使用原来的单帧判断
                    if current_has_spaghetti:
                        should_alert = True
                        alert_details.append(f"炒面 (置信度:{max_conf:.2f}, 总面积:{spaghetti_total_area}px²)")

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
                    continue

                # ───────────── 检测步骤 4: 发送告警邮件 ─────────────
                if should_alert and config.get_bool('email.enabled'):
                    web_url = config.get_str('app.web_url', 'http://localhost:5000')
                    other_faults_info = f"其他故障：{', '.join(other_faults)}" if other_faults else "无"
                    body = (
                        "【3D打印异常警报】\n\n"
                        f"检测时间：{ts_human}\n"
                        f"炒面告警：{', '.join(alert_details)}\n"
                        f"{other_faults_info}\n\n"
                        f"查看监控画面：{web_url}\n"
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
                    
                    # 发邮件后清零检测历史，避免重复告警
                    if detection_history:
                        detection_history.clear()
                        print("[多帧] 已发送告警，历史已清零")

                # 更新上次检测时间
                last_time = time.time()
            
            # 空闲时短暂休眠，避免CPU空转
            # 计算距离下次检测还剩多少时间
            elapsed = time.time() - last_time
            sleep_time = max(0, interval_sec - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    except Exception as e:
        print(f"运行时错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保释放摄像头资源
        try:
            if 'camera' in locals() and camera is not None:
                camera.release()
                print("摄像头已释放，程序结束")
        except Exception as e:
            print(f"释放摄像头时出错：{e}")


if __name__ == "__main__":
    # 程序入口：仅在直接运行本文件时执行main()
    main()