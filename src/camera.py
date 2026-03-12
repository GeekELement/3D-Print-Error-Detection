"""
摄像头模块

功能：基于OpenCV的摄像头操作，包括：
- 摄像头初始化和预热
- 定时拍照并保存
- 自动清理超出数量限制的旧图片
"""

import cv2
import numpy as np
import os
from datetime import datetime
import time
from typing import Optional
from config import config


class Camera:
    """
    摄像头控制器
    
    使用示例：
        camera = Camera(camera_index=0)
        image_path = camera.capture_and_save(prefix="print")
        camera.release()
    
    A1打印机相机用法：
        from bambulabs_api import Printer
        printer = Printer(host, access_code, serial_number)
        printer.connect()
        printer.camera_start()
        camera = Camera(source='a1', printer=printer)
    """
    
    def __init__(self, camera_index: int = None, source: str = None, printer=None):
        """
        初始化摄像头
        
        Args:
            camera_index: 摄像头索引，默认为配置中的值
            source: 相机来源，默认为配置中的值 (local/a1)
            printer: A1打印机对象，当source='a1'时需要传入
        """
        # 视频路径：优先检查，有值则使用视频模式
        test_video_path = config.get_str('debug.video_path', '')
        
        # 相机来源：优先使用传入值，否则读取配置
        self.source = source if source else config.get_str('camera.source', 'local')
        
        # 如果有视频路径，优先使用视频模式
        if test_video_path:
            from pathlib import Path
            base_dir = Path(__file__).parent.parent
            video_abs_path = str(base_dir / test_video_path)
            if os.path.exists(video_abs_path):
                self.source = 'video'
                self.video_path = video_abs_path
        
        self.printer = printer  # A1打印机对象
        
        # 视频模式
        if self.source == 'video':
            self.is_video_mode = True
            self.is_a1_mode = False
            self.captured_dir = config.get_str('captured_dir_abs', '')
            if not self.captured_dir:
                self.captured_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'captured')
            os.makedirs(self.captured_dir, exist_ok=True)
            
            self.predicted_dir = config.get_str('predicted_dir_abs', '')
            if not self.predicted_dir:
                self.predicted_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'predicted')
            os.makedirs(self.predicted_dir, exist_ok=True)
            
            self._cleanup_all_images()
            self.frame_interval = config.get_int('debug.frame_interval', 1)
            self.last_saved_frame_pos = -self.frame_interval
            self.cap = None  # 初始化cap属性
            self._open_camera()
            return
        
        # 摄像头索引：仅当source=local时使用
        self.camera_index = camera_index if camera_index is not None else config.get_int('camera.index', 0)
        self.cap = None  # VideoCapture对象
        
        # A1相机模式不需要OpenCV
        if self.source == 'a1':
            self.is_a1_mode = True
            self.cap = None  # A1模式不使用OpenCV
            self.video_path = None
            self.is_video_mode = False
            self.captured_dir = config.get_str('captured_dir_abs', '')
            if not self.captured_dir:
                self.captured_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'captured')
            os.makedirs(self.captured_dir, exist_ok=True)
            
            self.predicted_dir = config.get_str('predicted_dir_abs', '')
            if not self.predicted_dir:
                self.predicted_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'predicted')
            os.makedirs(self.predicted_dir, exist_ok=True)
            
            self._cleanup_all_images()
            self.frame_interval = config.get_int('debug.frame_interval', 1)
            self.last_saved_frame_pos = -self.frame_interval
            return
        
        # WebApp模式：从webapp获取图像
        if self.source == 'webapp':
            self.is_webapp_mode = True
            self.is_a1_mode = False
            self.cap = None
            self.video_path = None
            self.is_video_mode = False
            self.captured_dir = config.get_str('captured_dir_abs', '')
            if not self.captured_dir:
                self.captured_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'captured')
            os.makedirs(self.captured_dir, exist_ok=True)
            
            self.predicted_dir = config.get_str('predicted_dir_abs', '')
            if not self.predicted_dir:
                self.predicted_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'predicted')
            os.makedirs(self.predicted_dir, exist_ok=True)
            
            self._cleanup_all_images()
            return
        
        self.is_a1_mode = False
        self.is_video_mode = False
        
        # 图片保存目录
        self.captured_dir = config.get_str('captured_dir_abs', '')
        if not self.captured_dir:
            self.captured_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'captured')
        os.makedirs(self.captured_dir, exist_ok=True)
        
        self.predicted_dir = config.get_str('predicted_dir_abs', '')
        if not self.predicted_dir:
            self.predicted_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'predicted')
        os.makedirs(self.predicted_dir, exist_ok=True)
        
        # 启动时清空图片目录
        self._cleanup_all_images()
        
# 视频模式帧间隔控制
        self.frame_interval = config.get_int('debug.frame_interval', 1)
        self.last_saved_frame_pos = -self.frame_interval  # 上次保存的帧位置，初始为负值确保第一次取第0帧
        
        # 打开视频或摄像头
        self._open_camera()
    
    def _cleanup_all_images(self):
        for directory in [self.captured_dir, self.predicted_dir]:
            if not os.path.exists(directory):
                continue
            for f in os.listdir(directory):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                    try:
                        os.remove(os.path.join(directory, f))
                    except Exception as e:
                        print(f"清理图片失败：{f}, {e}")

    def _open_camera(self):
        """
        内部方法：打开视频或摄像头并预热
        
        如果配置了test_video_path，则打开视频文件
        否则使用DSHOW后端打开摄像头
        """
        if self.cap is None or not self.cap.isOpened():
            if self.is_video_mode:
                # 打开视频文件
                self.cap = cv2.VideoCapture(self.video_path)
                if not self.cap.isOpened():
                    raise RuntimeError(f"无法打开视频 {self.video_path}")
                print(f"已打开视频: {self.video_path}")
            else:
                # 使用DSHOW后端，Windows平台推荐
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    raise RuntimeError(f"无法打开摄像头 {self.camera_index}")

                # 设置分辨率
                width = config.get_int('camera.width', 640)
                height = config.get_int('camera.height', 480)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

                # 预热摄像头（让自动曝光、白平衡稳定下来）
                warmup_frames = config.get_int('camera.warmup_frames', 8)
                print("摄像头预热中...")
                for _ in range(warmup_frames):
                    self.cap.read()
                    time.sleep(0.05)

    def _capture_from_a1(self, prefix: str, cleanup: bool) -> Optional[str]:
        """
        从A1打印机获取相机帧并保存
        """
        import numpy as np
        
        if not self.printer:
            raise RuntimeError("A1模式需要传入printer对象")
        
        if not self.printer.camera_client_alive():
            raise RuntimeError("A1相机未连接")
        
        # 获取A1相机帧
        frame = self.printer.get_camera_frame()
        if frame is None:
            raise RuntimeError("无法获取A1相机画面")
        
        # 处理可能的字符串数据（base64编码）
        if isinstance(frame, str):
            import base64
            frame = base64.b64decode(frame)
        
        # 视频模式：帧间隔控制
        if self.is_video_mode and self.frame_interval > 1:
            target_pos = self.last_saved_frame_pos + self.frame_interval
            self.last_saved_frame_pos = target_pos
            print(f"A1视频模式，跳到第 {target_pos} 帧")
        
        # 生成文件名
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        save_path = os.path.join(self.captured_dir, filename)
        
        # 保存图片 (A1返回的是字节数据，需要转换为numpy数组再保存)
        nparr = np.frombuffer(frame, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if not cv2.imwrite(save_path, img):
            raise RuntimeError(f"保存图片失败：{save_path}")
        
        print(f"已保存A1相机画面：{save_path}")
        
        # 可选：清理旧图片
        if cleanup:
            max_captured = config.get_int('camera.max_captured', 1)
            if max_captured != 0:
                cleanup_old_images(self.captured_dir, max_captured)
        
        return save_path

    def _capture_from_webapp(self, prefix: str, cleanup: bool) -> Optional[str]:
        """
        从WebApp队列获取相机帧并保存
        """
        import webui as webapp_module
        
        if not webapp_module.is_camera_ready():
            raise RuntimeError("WebApp相机未就绪，请先在网页端连接打印机")
        
        frame = webapp_module.get_latest_frame(timeout=5)
        if frame is None:
            raise RuntimeError("无法获取WebApp相机画面")
        
        if isinstance(frame, str):
            import base64
            img = base64.b64decode(frame)
            import numpy as np
            img = np.frombuffer(img, np.uint8)
            img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        else:
            img = frame
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        save_path = os.path.join(self.captured_dir, filename)
        
        if not cv2.imwrite(save_path, img):
            raise RuntimeError(f"保存图片失败：{save_path}")
        
        print(f"已保存WebApp相机画面：{save_path}")
        
        if cleanup:
            max_captured = config.get_int('camera.max_captured', 1)
            if max_captured != 0:
                cleanup_old_images(self.captured_dir, max_captured)
        
        return save_path

    def capture_and_save(self, prefix: str = "print", cleanup: bool = False) -> Optional[str]:
        """
        拍摄一张图片并保存
        
        Args:
            prefix: 文件名前缀，默认为"print"
            cleanup: 是否在拍摄后清理旧图片，默认为False
            
        Returns:
            str: 保存的图片路径
            
        Raises:
            RuntimeError: 读取画面失败或保存失败时抛出
        """
        # A1打印机相机模式
        if self.is_a1_mode:
            return self._capture_from_a1(prefix, cleanup)
        
        # WebApp模式：从webapp队列获取图像
        if getattr(self, 'is_webapp_mode', False):
            return self._capture_from_webapp(prefix, cleanup)
        
        # 确保视频/摄像头已打开
        self._open_camera()
        
# 读取一帧
        ret, frame = self.cap.read()
        if not ret:
            # 视频模式：重新打开视频，重新从头开始
            if self.is_video_mode:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.video_path)
                self.last_saved_frame_pos = 0
                ret, frame = self.cap.read()
                if not ret:
                    raise RuntimeError("无法读取视频画面")
            else:
                raise RuntimeError("无法读取摄像头画面")
        
        # 视频模式：跳到上次保存位置 + frame_interval
        if self.is_video_mode and self.frame_interval > 1:
            target_pos = self.last_saved_frame_pos + self.frame_interval
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if target_pos >= total_frames:
                # 视频结束，退出程序
                print(f"视频已处理完毕，共 {total_frames} 帧")
                raise SystemExit(0)
            
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_pos)
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("无法读取视频画面")
            
            self.last_saved_frame_pos = target_pos
            print(f"跳到第 {target_pos}/{total_frames} 帧")

        # 生成文件名：前缀_时间戳.jpg
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        save_path = os.path.join(self.captured_dir, filename)

        # 保存图片
        if not cv2.imwrite(save_path, frame):
            raise RuntimeError(f"保存图片失败：{save_path}")

        # 可选：清理旧图片
        if cleanup:
            max_captured = config.get_int('camera.max_captured', 3)
            if max_captured != 0:
                cleanup_old_images(self.captured_dir, max_captured)

        print(f"已拍摄：{save_path}")
        return save_path

    def release(self):
        """
        释放摄像头资源
        
        调用此方法后摄像头将被关闭，其他程序可以使用
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __del__(self):
        """
        析构函数：确保释放摄像头资源
        """
        self.release()


def cleanup_old_images(directory: str, max_count: int):
    """
    清理目录中的旧图片，保留最新的N张
    
    Args:
        directory: 图片目录路径
        max_count: 保留的最大图片数量
        
    工作原理：
    1. 列出目录中所有图片文件（按修改时间排序）
    2. 保留最新的max_count张
    3. 删除其余图片
    
    Note:
        - max_count <= 0 时不执行清理
        - 图片格式支持：.jpg, .png, .jpeg
    """
    if max_count <= 0:
        return

    # 列出目录中的所有图片文件及其修改时间
    files = [
        (f, os.path.getmtime(os.path.join(directory, f)))
        for f in os.listdir(directory)
        if f.lower().endswith(('.jpg', '.png', '.jpeg'))
    ]

    # 如果文件数量不超过限制，无需清理
    if len(files) <= max_count:
        return

    # 按修改时间升序排序（最旧的在前）
    files.sort(key=lambda x: x[1])
    
    # 删除最旧的图片，保留最新的max_count张
    for path, _ in files[:-max_count]:
        try:
            os.remove(os.path.join(directory, path))
        except Exception as e:
            print(f"删除旧图片失败：{path}, {e}")
