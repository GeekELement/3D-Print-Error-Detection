"""
摄像头模块

功能：基于OpenCV的摄像头操作，包括：
- 摄像头初始化和预热
- 定时拍照并保存
- 自动清理超出数量限制的旧图片
"""

import cv2
import os
from datetime import datetime
import time
from config import config


class Camera:
    """
    摄像头控制器
    
    使用示例：
        camera = Camera(camera_index=0)
        image_path = camera.capture_and_save(prefix="print")
        camera.release()
    """
    
    def __init__(self, camera_index: int = None):
        """
        初始化摄像头
        
        Args:
            camera_index: 摄像头索引，默认为配置中的值
        """
        # 摄像头索引：优先使用传入值，否则读取配置
        self.camera_index = camera_index if camera_index is not None else config.get_int('camera.index', 0)
        self.cap = None  # VideoCapture对象
        
        # 检测视频文件是否存在
        test_video_path = config.get_str('camera.test_video_path', '')
        if test_video_path:
            from pathlib import Path
            base_dir = Path(__file__).parent.parent
            self.video_path = str(base_dir / test_video_path)
            self.is_video_mode = os.path.exists(self.video_path)
        else:
            self.video_path = None
            self.is_video_mode = False
        
        # 视频模式：每隔几帧检测一次（节省资源）
        self.video_skip_frames = config.get_int('camera.video_skip_frames', 0)
        
        # 图片保存目录
        save_dir = config.get_str('captured_dir_abs', '')
        if not save_dir:
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'captured')
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 视频不存在时，立即初始化摄像头并预热
        if not self.is_video_mode:
            self._open_camera(warmup=True)

    def _open_camera(self, warmup=False):
        """
        打开视频或摄像头
        
        Args:
            warmup: 是否预热摄像头（仅在不使用视频时有效）
        """
        if self.cap is None or not self.cap.isOpened():
            if self.is_video_mode:
                self.cap = cv2.VideoCapture(self.video_path)
                if self.cap.isOpened():
                    print(f"已打开视频: {self.video_path}")
                else:
                    raise RuntimeError(f"无法打开视频 {self.video_path}")
            else:
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    raise RuntimeError(f"无法打开摄像头 {self.camera_index}")

                if warmup:
                    width = config.get_int('camera.width', 640)
                    height = config.get_int('camera.height', 480)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

                    warmup_frames = config.get_int('camera.warmup_frames', 8)
                    print("摄像头预热中...")
                    for _ in range(warmup_frames):
                        self.cap.read()
                        time.sleep(0.05)

    def capture_and_save(self, prefix: str = "print", cleanup: bool = False) -> str:
        """
        拍摄一张图片并保存
        
        Args:
            prefix: 文件名前缀，默认为"print"
            cleanup: 是否在拍摄后清理旧图片，默认为False
            
        Returns:
            str: 保存的图片文件路径
            
        Raises:
            RuntimeError: 读取画面失败或保存失败时抛出
        """
        # 确保视频/摄像头已打开
        self._open_camera()
        
        # 视频模式：跳过帧以降低检测频率
        if self.is_video_mode and self.video_skip_frames > 0:
            for _ in range(self.video_skip_frames):
                self.cap.read()
        
        # 读取一帧
        ret, frame = self.cap.read()
        if not ret:
            if self.is_video_mode:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.video_path)
                ret, frame = self.cap.read()
                if not ret:
                    raise RuntimeError("无法读取视频画面")
            else:
                raise RuntimeError("无法读取摄像头画面")

        # 生成文件名：前缀_时间戳.jpg
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        save_path = os.path.join(self.save_dir, filename)

        # 保存图片
        if not cv2.imwrite(save_path, frame):
            raise RuntimeError(f"保存图片失败：{save_path}")

        # 可选：清理旧图片
        if cleanup:
            max_pictures = config.get_int('camera.max_pictures', 100)
            if max_pictures != 0:
                cleanup_old_images(self.save_dir, max_pictures)

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