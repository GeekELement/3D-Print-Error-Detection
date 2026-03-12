# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.6%2B-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/yolov8)

## 项目简介

本项目是一个部署在3D打印机上位机上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件和Web监控链接），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认3秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件，包含Web监控链接
- **📷 多相机支持**：支持本机USB摄像头、Bambu Lab A1打印机相机、WebApp模式、视频文件
- **🌐 Web监控界面**：实时查看打印机状态、温度、进度、层数等，并可远程控制打印
- **🔧 Bambu Lab支持**：支持 Bambu Lab 打印机控制
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数
- **🐛 调试模式**：支持视频文件测试，可控制取帧间隔
- **📡 MQTT支持**：通过MQTT协议连接Bambu Lab打印机

## 技术栈

- **编程语言**: Python 3.10+
- **深度学习框架**: PyTorch 2.5+, YOLOv8 (ultralytics)
- **计算机视觉库**: OpenCV 4.6+
- **Web框架**: Flask 3.x, Flask-SocketIO
- **物联网协议**: MQTT (paho-mqtt)
- **打印机API**: bambulabs-api
- **配置管理**: PyYAML
- **HTTP客户端**: requests

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（调试可用视频文件）
- 操作系统: Linux / Windows
- Python: 3.10 或更高版本
- GPU/NPU: 可选（目前只支持CUDA加速）

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
├── README_en.md                  # 英文说明文档
├── requirements.txt              # Python依赖包列表
├── config.yaml                   # 配置文件
├── config.yaml.example           # 配置文件模板
├── best.pt                       # 训练好的YOLOv8模型权重
├── best.onnx                     # ONNX格式模型权重（可选）
├── images/                       # 图片存储目录
│   ├── captured/                 # 原始拍摄图片
│   └── predicted/                # 带标注的预测图片
└── src/                          # 源代码目录
    ├── main.py                   # 主程序入口
    ├── config.py                 # YAML配置加载
    ├── camera.py                 # 摄像头操作 + 图片清理
    ├── alerter.py                # 邮件告警 + 打印机控制客户端
    ├── device.py                 # 设备管理（GPU/CPU）
    ├── webui.py                  # Web监控界面 (Flask + SocketIO)
    └── webui.html                # Web监控前端页面
```

## 核心模块

### 1. 配置管理 (`config.py`)
- 使用YAML格式配置文件
- 支持路径自动计算（相对路径/绝对路径）
- 配置验证和目录创建
- 提供类型安全的配置读取接口

### 2. 设备管理 (`device.py`)
- 自动检测GPU/CUDA可用性
- YOLO模型自动选择GPU/CPU
- 提供设备信息查询

### 3. 摄像头模块 (`camera.py`)
- 基于OpenCV的摄像头/视频操作
- 支持多种相机模式：local(USB摄像头)、a1(A1打印机相机)、webapp(WebApp获取)、video(视频文件)
- 支持预热和分辨率配置
- 启动时自动清空图片目录
- 视频模式支持帧间隔控制

### 4. 报警模块 (`alerter.py`)
- `send_email`: SMTP邮件发送，支持附件
- `BambuClient`: Bambu Lab MQTT客户端

### 5. Web监控模块 (`webui.py` + `webui.html`)
- 实时显示打印机状态（温度、进度、层数、文件等）
- 实时显示A1相机画面（MJPEG流）
- 连接/断开打印机控制
- 远程控制：暂停、恢复、停止打印
- SocketIO实时通信

### 6. 主程序 (`main.py`)
- YOLOv8模型加载和推理
- 实时检测和结果分析
- 阈值判断和告警决策
- 炒面(spaghetti)面积并集计算
- **多帧检测**（借鉴Bambu Lab拓竹炒面检测原理）
- 支持多种相机模式自动切换

## 多帧检测算法（借鉴Bambu Lab）

本项目的多帧检测逻辑借鉴了 **Bambu Lab X1** 的炒面检测原理：

### 核心思路
1. **多帧累积**：不依赖单帧判断，而是累积多帧检测结果
2. **阳性帧计数**：只有检测到符合参数的的帧才计入阳性帧
3. **面积验证**：当阳性帧数达到阈值后，验证当前帧面积是否超过面积阈值

### 检测流程
```
每帧检测 → 是否检测到spaghetti?
         ↓
    阳性帧+1，存入历史
         ↓
    阳性帧数 >= required_frames?
         ↓
    是 → 检查当前帧面积 >= area_threshold?
         ↓
    是 → 触发告警 → 发邮件 → 清零历史
```

### 配置参数
```yaml
multi_frame:
  enabled: true              # 是否启用多帧检测
  required_frames: 5         # 阳性帧数达到此值后验证面积
  alert_conf_threshold: 0.65 # 置信度阈值 (0.0-1.0)
  area_threshold: 900        # 面积阈值 (像素²)
```

### 优势
- 减少误报：单帧的短暂异常不会触发告警
- 更可靠：需要持续检测到异常才告警
- 可调参数：可根据打印速度调整帧数和阈值

## 配置说明

### 调试模式
```yaml
debug:
  video_path: ""              # 视频文件路径，留空使用摄像头
  frame_interval: 30           # 视频模式：每隔多少帧识别一次
```

### 模型配置
```yaml
model:
  path: "best.pt"            # YOLO 模型文件路径
  conf_threshold: 0.5         # 检测置信度阈值 (0.0-1.0)，低于此值不检测
  use_cuda: true              # 是否使用CUDA加速（默认true）
```

### 多帧检测配置
```yaml
multi_frame:
  enabled: true              # 是否启用多帧检测
  required_frames: 5          # 阳性帧数达到此值后验证面积
  alert_conf_threshold: 0.65 # 置信度阈值 (0.0-1.0)
  area_threshold: 900        # 面积阈值 (像素²)
```

### 监控配置
```yaml
monitoring:
  interval_sec: 3            # 检测间隔（秒）
```

### 摄像头配置
```yaml
camera:
  source: webapp                   # 相机来源: local=本机摄像头, a1=A1打印机相机, webapp=WebApp模式
  index: 0                   # 摄像头索引 (0=默认摄像头)
  width: 640                 # 分辨率宽度
  height: 480                # 分辨率高度
  warmup_frames: 8            # 预热帧数 (自动曝光/白平衡稳定)
  max_captured: 1            # captured目录保留最新图片数量，0=保留全部
  max_predicted: 1           # predicted目录保留最新图片数量，0=保留全部
```

### 目录配置
```yaml
directories:
  project_root: ".."         # 项目根目录
  predicted_dir: "images/predicted"  # 预测图片保存目录
  captured_dir: "images/captured"    # 原始图片保存目录
```

### 邮件配置
```yaml
email:
  enabled: true               # 是否启用邮件报警
  to: "your_email@domain.com"   # 接收邮件地址
  from: "your_email@domain.com" # 发送邮件地址
  password: "xxxx"           # SMTP授权码/应用密码
  smtp:
    server: "smtp.qq.com"   # SMTP服务器
    port: 465               # SMTP端口
    use_ssl: true           # 是否使用SSL
```

### Bambu Lab 打印机配置
```yaml
printer:
  host: "192.168.1.100"     # 打印机IP地址
  access_code: "xxxxxx"       # 访问代码（打印机设置中获取）
  serial_number: "xxxxxxxx"   # 打印机序列号
```

### 程序设置
```yaml
app:
  web_url: "http://localhost:5000"  # Web监控页面地址（用于邮件告警）
```

## 注意事项

- 使用前请准备训练好的YOLOv8模型（`best.pt`或`yolov8n.pt`）
- 确保摄像头权限已配置
- 邮件发送需要SMTP授权码（非登录密码）
- YAML配置文件使用空格缩进，不支持Tab
- 打印机控制需先配置对应固件
- Bambu Lab 需要在打印机上启用MQTT并获取 access_code 和 serial_number
- 程序支持Ctrl+C优雅退出
- 视频调试模式：每 `frame_interval` 帧保存一张图片，用于快速测试
- A1相机模式：配置 `camera.source: a1` 并确保打印机网络可达
- WebApp模式：配置 `camera.source: webapp`，程序启动后需在网页端连接打印机
- Web监控：访问 http://localhost:5000 实时查看打印机状态和相机画面
- 多帧检测：可有效减少误报，需要持续检测到异常才告警
- 模型支持导出为ONNX格式以获得更好的推理性能

## 联系

- 邮箱：geekelement@outlook.com