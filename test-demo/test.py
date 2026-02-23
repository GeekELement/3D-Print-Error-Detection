import cv2
import time
import torch
from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = Path(__file__).parent.parent / "best.pt"
VIDEO_PATH = Path(__file__).parent / "test1.mp4"


def check_cuda():
    """检查CUDA并返回是否应该使用"""
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        print(f"GPU可用: {gpu_name}")
        return True
    else:
        print("CUDA不可用，将使用CPU")
        return False


def main():
    should_use_cuda = check_cuda()

    print("加载模型...")
    model = YOLO(str(MODEL_PATH))
    if should_use_cuda:
        model.to('cuda')
    print(f"模型类别: {model.names}")

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        print(f"无法打开视频: {VIDEO_PATH}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"视频信息: {width}x{height} @ {fps}fps")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    video_name = VIDEO_PATH.stem
    output_video_path = output_dir / f"{video_name}_output.mp4"

    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    frame_count = 0
    detected_count = 0
    inference_times = []

    print("\n开始识别，按 'q' 或 'ESC' 退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("视频播放结束")
            break

        frame_count += 1
        
        start_time = time.time()
        results = model(frame, conf=0.1, verbose=False)[0]
        inference_time = time.time() - start_time
        inference_times.append(inference_time)
        
        fps_current = 1.0 / inference_time if inference_time > 0 else 0

        annotated = results.plot()

        boxes = results.boxes
        if len(boxes) > 0:
            detected_count += 1
            print(f"第{frame_count}帧: 检测到 {len(boxes)} 个目标, 推理FPS: {fps_current:.1f}")
            for box in boxes:
                cls_name = results.names[int(box.cls)]
                conf = float(box.conf)
                print(f"  - {cls_name}: {conf:.2f}")

        cv2.putText(annotated, f"Frame: {frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated, f"FPS: {fps_current:.1f}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("3D打印缺陷检测", annotated)

        out.write(annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    avg_fps = frame_count / sum(inference_times) if inference_times else 0
    print(f"\n识别完成!")
    print(f"总帧数: {frame_count}")
    print(f"检测到目标的帧数: {detected_count}")
    print(f"平均推理FPS: {avg_fps:.1f}")
    print(f"输出视频: {output_video_path}")

if __name__ == "__main__":
    main()
