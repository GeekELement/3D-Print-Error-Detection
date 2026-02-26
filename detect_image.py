import os
from pathlib import Path
from ultralytics import YOLO

# 路径配置
base_dir = Path(__file__).parent
model_path = base_dir / "best.pt"
image_path = r"C:\Users\root\Desktop\test1.png"
output_path = r"C:\Users\root\Desktop\test_result.png"

# 加载模型
model = YOLO(str(model_path))

# 检测
results = model(image_path, conf=0.25, verbose=False)[0]

# 保存结果
annotated = results.plot()
os.makedirs(os.path.dirname(output_path), exist_ok=True)

if os.path.exists(output_path):
    os.remove(output_path)

import cv2
cv2.imwrite(output_path, annotated)

print(f"检测完成，结果已保存到: {output_path}")
print(f"检测到 {len(results.boxes)} 个目标")
for box in results.boxes:
    cls_name = results.names[int(box.cls)]
    conf = float(box.conf)
    print(f"  - {cls_name}: {conf:.2f}")