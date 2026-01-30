# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.7%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/yolov8)

## 项目简介

本项目是一个部署在3D打印机上位机（如树莓派）上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认6秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片

## 技术栈

- **编程语言**: Python 3
- **深度学习框架**: PyTorch, YOLOv8 (ultralytics)
- **计算机视觉库**: OpenCV
- **邮件协议**: SMTP

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（如树莓派4B）
- 操作系统: Ubuntu / Debian / Windows

### 安装与部署

1. **克隆项目**
   ```bash
   git clone https://github.com/GeekELement/3D_Print_Error_Detection
   cd 3D_Print_Error_Detection
   ```

2. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```
   核心依赖：`opencv-python`, `torch`, `ultralytics`, `requests`

3. **配置参数**
   编辑 `src/main.py` 中的配置区：
   ```python
   MODEL_PATH = "path/to/your/model.pt"      # YOLOv8模型路径
   CAMERA_INDEX = 0                           # 摄像头索引
   INTERVAL_MIN = 0.1                         # 检测间隔（分钟）
   CONF_THRESHOLD = 0.25                      # 检测阈值
   ALERT_CONF_THRESHOLD = 0.70                # 告警阈值（高于此值才发邮件）

   # 邮件配置
   EMAIL_TO = "your_email@example.com"
   EMAIL_FROM = "sender@example.com"
   EMAIL_PASSWORD = "your_app_password"
   ```

4. **运行程序**
   ```bash
   python src/main.py
   ```

## 项目结构

```
3D-Print-Defect-Detection/
├── README.md
├── requirements.txt
├── yolov8n.pt                    # YOLOv8模型权重
├── images/
│   ├── saved_pictures/           # 原始拍摄图片
│   └── predicted_pictures/       # 带标注的预测图片
└── src/
    ├── main.py                   # 主程序入口
    ├── camera_capture.py         # 摄像头操作模块
    ├── notify.py                 # 邮件告警模块
    └── octoprint_client.py       # OctoPrint API客户端（预留）
```

## 工作流程

1. 按设定间隔启动检测
2. 调用摄像头拍摄当前打印画面
3. 使用YOLOv8模型进行推理
4. 保存原始图片和预测标注图
5. 若检测到高置信度目标，发送告警邮件

## 注意事项

- 使用前请准备训练好的YOLOv8模型（`best.pt`或`yolov8n.pt`）
- 确保摄像头权限已配置
- 邮件发送需要SMTP授权码，非登录密码
- 当前版本仅支持邮件告警，暂未实现自动控制打印机功能

## 联系

- 邮箱：geekelement@outlook.com
