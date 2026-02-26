# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.6%2B-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.7%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/yolov8)

## 项目简介

本项目是一个部署在3D打印机上位机上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认5秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件
- **📩 邮件控制**：支持通过邮件回复远程控制打印机（停止/继续打印）
- **🔧 多固件支持**：支持 Klipper、OctoPrint、Bambu Lab 打印机控制
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数
- **🐛 调试模式**：支持视频文件测试，可控制取帧间隔

## 技术栈

- **编程语言**: Python 3.7+
- **深度学习框架**: PyTorch, YOLOv8 (ultralytics)
- **计算机视觉库**: OpenCV
- **配置管理**: PyYAML
- **HTTP客户端**: requests
- **MQTT客户端**: paho-mqtt (Bambu Lab)
- **邮件协议**: SMTP, IMAP

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（调试可用视频文件）
- 操作系统: Ubuntu / Debian / Windows
- Python: 3.7 或更高版本
- GPU: 可选（支持CUDA加速）

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
   核心依赖：`opencv-python>=4.6.0`, `torch>=1.7.0`, `ultralytics>=8.0.0`, `requests>=2.23.0`, `PyYAML>=6.0`, `numpy>=1.21.0`, `paho-mqtt`

3. **配置参数**
   编辑 `config.yaml` 配置文件

4. **运行程序**
   ```bash
   python src/main.py
   ```

## 项目结构

```
3D_Print_Error_Detection/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python依赖包列表
├── config.yaml                   # 配置文件
├── best.pt                       # 训练好的YOLOv8模型权重
├── images/                       # 图片存储目录
│   ├── captured/                 # 原始拍摄图片
│   └── predicted/                # 带标注的预测图片
└── src/                          # 源代码目录
    ├── main.py                   # 主程序入口
    ├── config.py                 # YAML配置加载
    ├── camera.py                 # 摄像头操作 + 图片清理
    ├── alerter.py                # 邮件告警 + 邮件回复 + 打印机控制
    └── device.py                 # 设备管理（GPU/CPU）
```

## 核心模块

### 1. 配置管理 (`config.py`)
- 使用YAML格式配置文件
- 支持路径自动计算（相对路径/绝对路径）
- 配置验证和目录创建

### 2. 设备管理 (`device.py`)
- 自动检测GPU可用性
- 根据配置决定是否使用CUDA加速
- 提供设备信息查询

### 3. 摄像头模块 (`camera.py`)
- 基于OpenCV的摄像头/视频操作
- 支持预热和分辨率配置
- 启动时自动清空图片目录
- 支持调试模式视频测试
- 视频模式支持帧间隔控制

### 4. 报警模块 (`alerter.py`)
- `send_email`: SMTP邮件发送，支持附件
- `EmailReplyHandler`: 监听IMAP邮箱，识别告警邮件回复
- `KlipperClient`: 通过Moonraker API控制Klipper打印机
- `OcttoPrintClien`: 通过API控制OctoPrint打印机
- `BambuClient`: 通过MQTT控制Bambu Lab打印机

### 5. 主程序 (`main.py`)
- YOLOv8模型加载和推理
- 实时检测和结果分析
- 阈值判断和告警决策
- 炒面(spaghetti)面积并集计算

## 配置说明

### 调试模式
```yaml
debug:
  video_path: "test-demo/test1.mp4"   # 视频文件路径，为空使用摄像头
  frame_interval: 60                   # 视频模式每多少帧取一张（1=每帧都取）
```

### 摄像头配置
```yaml
camera:
  index: 0              # 摄像头索引
  width: 640            # 图像宽度
  height: 480           # 图像高度
  warmup_frames: 8      # 预热帧数
  max_captured: 3       # captured目录保留图片数量，0=保留全部
  max_predicted: 3      # predicted目录保留图片数量，0=保留全部
```

### 模型配置
```yaml
model:
  path: "best.pt"                # 模型文件路径
  conf_threshold: 0.3            # 常规检测置信度阈值
  alert_conf_threshold: 0.65     # 告警置信度阈值
  spaghetti_area_threshold: 2000 # 炒面告警面积阈值(像素²)
  use_cuda: true                 # 是否启用CUDA加速
```

### 监控配置
```yaml
monitoring:
  interval_sec: 5   # 检测间隔（秒）
```

### 邮件配置
```yaml
email:
  enabled: true
  to: "接收邮箱@domain.com"
  from: "发送邮箱@domain.com"
  password: "SMTP授权码"
  smtp:
    server: "smtp.qq.com"
    port: 465
    use_ssl: true
  imap:
    server: "imap.qq.com"
    check_interval: 10    # 检查邮件回复间隔（秒）
```

### 邮件回复配置
```yaml
email_reply:
  enabled: true
  subject_prefix: "【3D打印异常警报】"
  skip_duration_min: 10   # 回复1后跳过检测的时长（分钟）
```

### 打印机配置
```yaml
printer:
  type: "klipper"  # 打印机固件类型: klipper, octoprint, bambu, none

  klipper:
    url: "http://192.168.1.100:7125"   # Moonraker服务器地址
    api_key: ""                         # API密钥（可选）

  octoprint:
    url: "http://192.168.1.100:5000"   # OctoPrint服务器地址
    api_key: ""                         # API密钥

  bambu:
    host: "192.168.1.100"              # 打印机IP地址
    mqtt_port: 8883                    # MQTT端口 (8883=SSL, 1883=非SSL)
    access_code: ""                    # 访问代码
    serial_number: ""                  # 打印机序列号
```

## 邮件回复控制

用户收到告警邮件后，可回复以下指令控制打印机：
- **回复 0**：立即停止打印
- **回复 1**：继续打印，指定分钟内不检测

回复邮件主题需包含"Re:"或"回复"。

## 注意事项

- 使用前请准备训练好的YOLOv8模型（`best.pt`或`yolov8n.pt`）
- 确保摄像头权限已配置
- 邮件发送需要SMTP授权码（非登录密码）
- 邮件回复需要开启IMAP服务
- YAML配置文件使用空格缩进，不支持Tab
- 打印机控制需先配置对应固件
- Bambu Lab 需要在打印机上启用MQTT并获取 access_code 和 serial_number
- 程序支持Ctrl+C优雅退出
- 视频调试模式：每 `frame_interval` 帧保存一张图片，用于快速测试

## 联系

- 邮箱：geekelement@outlook.com