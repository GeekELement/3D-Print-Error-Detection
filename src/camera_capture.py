# camera_capture.py
import cv2
import os
from datetime import datetime
import time

class SimpleCamera:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        
        # 保存路径（可改成从配置文件读取）
        self.save_dir = r"C:\Files\3D_Print_Error_Detection\YOLOv8_cs-main\images\saved_pictures"
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 初始化时就尝试打开（可选：也可以延迟到第一次拍摄）
        self._open_camera()

    def _open_camera(self):
        """内部方法：使用 DSHOW 后端 + 预热，减少延迟"""
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise RuntimeError(f"无法打开摄像头 {self.camera_index}")

            # 设置常用分辨率（加速 + 统一输入尺寸给 YOLO）
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            # self.cap.set(cv2.CAP_PROP_FPS, 30)  # 可选

            # 预热：丢弃前几帧，让自动曝光/白平衡稳定
            print("摄像头预热中（只需第一次）...")
            for _ in range(8):
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

        print(f"已拍摄并保存：{save_path}")
        return save_path

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