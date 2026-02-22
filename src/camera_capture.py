# camera_capture.py
import cv2
import os
from datetime import datetime
import time
from config_loader import config

class SimpleCamera:
    def __init__(self, camera_index: int = None):
        # 如果没有传入摄像头索引，使用配置中的默认值
        self.camera_index = camera_index if camera_index is not None else config.get_int('camera.index', 0)
        self.cap = None
        
        # 使用配置中的保存路径
        save_dir = config.get_str('captured_dir_abs', '')
        if not save_dir:
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'images', 'saved_pictures')
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 初始化时就尝试打开（可选：也可以延迟到第一次拍摄）
        self._open_camera()

    def _open_camera(self):
        """内部方法：使用 DSHOW 后端 + 预热，减少延迟"""
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise RuntimeError(f"无法打开摄像头 {self.camera_index}")

            # 使用配置中的分辨率设置
            width = config.get_int('camera.width', 640)
            height = config.get_int('camera.height', 480)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            # self.cap.set(cv2.CAP_PROP_FPS, 30)  # 可选

            # 使用配置中的预热帧数
            warmup_frames = config.get_int('camera.warmup_frames', 8)
            print("摄像头预热中（只需第一次）...")
            for _ in range(warmup_frames):
                self.cap.read()
                time.sleep(0.05)

    def capture_and_save(self, prefix: str = "capture") -> str:
        """
        核心方法：拍一张 → 保存 → 返回文件路径
        每次调用都会自动保存一张带时间戳的图片
        """
        self._open_camera()  # 确保已打开

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("无法读取摄像头画面")

        # 文件名只带日期时间
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        save_path = os.path.join(self.save_dir, filename)

        if not cv2.imwrite(save_path, frame):
            raise RuntimeError(f"保存图片失败：{save_path}")

        max_pictures = config.get_int('camera.max_pictures', 100)
        if max_pictures != 0:
            self._cleanup_old_images(max_pictures)

        print(f"已拍摄并保存：{save_path}")
        return save_path

    def _cleanup_old_images(self, max_count: int):
        """删除超出数量的最旧图片"""
        files = [f for f in os.listdir(self.save_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        if len(files) <= max_count:
            return
        
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.save_dir, f)))
        for old_file in files[:-max_count]:
            try:
                os.remove(os.path.join(self.save_dir, old_file))
                print(f"已删除旧图片：{old_file}")
            except Exception as e:
                print(f"删除旧图片失败：{old_file}, {e}")

    def release(self):
        """程序结束或长时间不用时调用"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("摄像头已释放")

    def __del__(self):
        self.release()


# 如果直接运行本文件，可做简单测试
if __name__ == "__main__":
    cam = SimpleCamera()
    try:
        path = cam.capture_and_save("test")
        print("测试拍摄完成，路径：", path)
    finally:
        cam.release()