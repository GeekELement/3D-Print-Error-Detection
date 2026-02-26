# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.6%2B-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.7%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/yolov8)
[![PyYAML](https://img.shields.io/badge/PyYAML-6.0-blue)](https://pyyaml.org/)

## 项目简介

本项目是一个部署在3D打印机上位机上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认5秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件
- **📩 邮件控制**：支持通过邮件回复远程控制打印机（停止/继续打印）
- **🔧 多打印机支持**：支持 Klipper、拓竹 Bambu、OctoPrint 三种固件
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数
- **🎬 视频调试**：支持视频文件测试，无需连接实际打印机

## 技术栈

- **编程语言**: Python 3.8+
- **深度学习框架**: PyTorch 2.5.1 (CUDA 12.1)
- **目标检测模型**: YOLOv8 (ultralytics 8.4.14)
- **计算机视觉库**: OpenCV 4.13.0
- **配置管理**: PyYAML 6.0.3
- **HTTP客户端**: requests 2.32.5
- **邮件协议**: SMTP, IMAP
- **MQTT协议**: paho-mqtt (用于拓竹打印机)
- **图像处理**: Pillow 12.1.1, NumPy 2.2.6
- **打印机控制**: Klipper/Moonraker API, Bambu MQTT, OctoPrint HTTP API

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（测试demo可用视频文件）
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
   核心依赖：`opencv-python>=4.6.0`, `torch>=1.7.0`, `ultralytics>=8.0.0`, `requests>=2.23.0`, `PyYAML>=6.0`, `numpy>=1.21.0`, `paho-mqtt>=1.6.0`

3. **配置参数**
   编辑 `config.yaml` 配置文件

4. **运行程序**
   ```bash
   python src/main.py
   ```

### 视频调试

在 `config.yaml` 中配置视频路径即可使用视频测试：
```yaml
camera:
  test_video_path: "test.mp4"  # 填入视频路径，为空则使用摄像头
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
- 支持路径自动计算
- 配置验证和目录创建

### 2. 设备管理 (`device.py`)
- 自动检测GPU可用性
- 根据配置决定是否使用CUDA加速
- 提供设备信息查询

### 3. 摄像头模块 (`camera.py`)
- 基于OpenCV的摄像头操作
- 支持预热和分辨率配置
- 自动保存带时间戳的图片
- 定时清理超出数量限制的旧图片

### 4. 报警模块 (`alerter.py`)
- `send_email`: SMTP邮件发送，支持附件
- `EmailReplyHandler`: 监听IMAP邮箱，识别告警邮件回复
- `KlipperClient`: 通过Moonraker API控制Klipper打印机
- `BambuClient`: 通过MQTT协议控制拓竹打印机
- `OctoPrintClient`: 通过HTTP API控制OctoPrint打印机

### 5. 主程序 (`main.py`)
- YOLOv8模型加载和推理
- 实时检测和结果分析
- 阈值判断和告警决策
- 炒面(spaghetti)面积并集计算

## 工作流程

1. **配置加载**：启动时读取YAML配置文件并验证
2. **初始化**：加载YOLOv8模型，初始化摄像头，启动邮件回复监听
3. **循环监控**：按设定间隔执行以下步骤：
   - 检查邮件回复（根据配置）
   - 拍摄当前打印画面
   - YOLO模型推理分析
   - 保存原始图片和标注结果
   - 判断是否需要发送告警邮件
4. **告警处理**：达到告警阈值时自动发送邮件
5. **远程控制**：用户可通过邮件回复控制打印机（0=停止，1=继续）
6. **持续监控**：循环执行直至程序终止

## 配置说明

### 摄像头配置
```yaml
camera:
  index: 0              # 摄像头索引
  width: 640            # 图像宽度
  height: 480           # 图像高度
  warmup_frames: 8      # 预热帧数
  max_pictures: 3       # 保存图片最大数量
  cleanup_interval: 1   # 图片清理间隔（每N次检测清理一次）
  test_video_path: ""   # 测试视频路径，为空则使用摄像头
```

### 模型配置
```yaml
model:
  path: "best.pt"           # 模型文件路径
  conf_threshold: 0.25          # 检测置信度阈值
  alert_conf_threshold: 0.70    # 告警置信度阈值
  use_cuda: true                # 是否启用CUDA加速
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
  type: "klipper"  # 打印机类型: klipper, bambu, octoprint（为空则不控制打印机）

# Klipper 配置
klipper:
  url: "http://192.168.1.100:7125"
  api_key: "你的API密钥"

# 拓竹 Bambu 配置
bambu:
  printer_ip: "192.168.1.100"
  access_code: "123456"  # 机身标签上的6位码
  serial_number: "01GW1234567890"

# OctoPrint 配置
octoprint:
  url: "http://192.168.1.100:5000"
  api_key: "你的API密钥"
```

## 注意事项

- 使用前请准备训练好的YOLOv8模型（`best.pt`或`yolov8n.pt`）
- 确保摄像头权限已配置
- 邮件发送需要SMTP授权码（非登录密码）
- 邮件回复需要开启IMAP服务
- YAML配置文件使用空格缩进，不支持Tab
- 打印机控制根据 `printer.type` 自动选择，无需单独启用
- 程序支持Ctrl+C优雅退出
- 如需CUDA加速，需安装PyTorch CUDA版本，并在config.yaml中设置 `model.use_cuda: true`
- 调试时可设置 `camera.test_video_path` 使用视频文件测试

## 邮件回复控制

用户收到告警邮件后，可回复以下指令控制打印机：
- **回复 0**：立即停止打印
- **回复 1**：继续打印，10分钟内不检测（可配置）

回复邮件主题需包含"Re:"或"回复"。

## 扩展功能

项目设计支持多种扩展：
- 添加新的检测模型
- 支持数据库存储历史记录
- 添加Web界面管理
## 联系

- 邮箱：geekelement@outlook.com
