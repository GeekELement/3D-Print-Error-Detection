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
- **🔧 Klipper集成**：通过Moonraker API直接控制Klipper打印机
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数

## 技术栈

- **编程语言**: Python 3.7+
- **深度学习框架**: PyTorch, YOLOv8 (ultralytics)
- **计算机视觉库**: OpenCV
- **配置管理**: PyYAML
- **HTTP客户端**: requests
- **邮件协议**: SMTP, IMAP
- **打印机控制**: Klipper/Moonraker API

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
   核心依赖：`opencv-python>=4.6.0`, `torch>=1.7.0`, `ultralytics>=8.0.0`, `requests>=2.23.0`, `PyYAML>=6.0`, `numpy>=1.21.0`

3. **配置参数**
   编辑 `config.yaml` 配置文件

4. **运行程序**
   - 实时监控模式：
     ```bash
     python src/main.py
     ```
   - 视频测试模式：
     ```bash
     python test-demo/test.py
     ```

### 测试demo

`test-demo/test.py` 可独立运行，不依赖src模块：
- 支持视频文件检测
- 自动输出带标注的结果视频
- 实时显示FPS
- 自动检测CUDA可用性

## 项目结构

```
3D_Print_Error_Detection/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python依赖包列表
├── config.yaml                   # 配置文件
├── best.pt                       # 训练好的YOLOv8模型权重
├── images/                       # 图片存储目录
│   ├── saved_pictures/           # 原始拍摄图片
│   └── predicted_pictures/       # 带标注的预测图片
├── test-demo/                    # 测试demo
│   ├── test.py                   # 视频检测脚本
│   ├── test1.mp4                 # 测试视频
│   └── output/                   # 输出目录
└── src/                          # 源代码目录
    ├── main.py                   # 主程序入口
    ├── config_loader.py          # YAML配置加载器
    ├── cuda_utils.py             # CUDA工具类
    ├── camera_capture.py         # 摄像头操作模块
    ├── image_utils.py            # 图片工具模块（清理旧图片）
    ├── notify.py                 # 邮件告警模块
    ├── email_replier.py          # 邮件回复处理模块
    └── klipper_client.py         # Klipper/Moonraker API客户端
```

## 核心模块

### 1. 配置管理 (`config_loader.py`)
- 使用YAML格式配置文件
- 支持路径自动计算和环境变量
- 配置验证和错误提示

### 2. CUDA工具类 (`cuda_utils.py`)
- 自动检测GPU可用性
- 根据配置决定是否使用CUDA加速
- 提供设备信息查询

### 3. 摄像头模块 (`camera_capture.py`)
- 基于OpenCV的摄像头操作
- 支持预热和分辨率配置
- 自动保存带时间戳的图片
- 自动清理超出数量限制的旧图片

### 3. 图片工具模块 (`image_utils.py`)
- 清理超出数量限制的旧图片
- 使用堆算法高效保留最新N张图片

### 3. 检测模块 (`main.py`)
- YOLOv8模型加载和推理
- 实时检测和结果分析
- 阈值判断和告警决策

### 4. 邮件告警 (`notify.py`)
- SMTP邮件发送功能
- 支持附件（检测图片）
- 异常处理和错误日志

### 5. 邮件回复处理 (`email_replier.py`)
- 监听IMAP邮箱收件箱
- 识别告警邮件的回复
- 回复"0"：停止打印
- 回复"1"：继续打印并跳过检测

### 6. Klipper控制 (`klipper_client.py`)
- 通过Moonraker API控制打印机
- 支持暂停/恢复/停止打印
- 获取打印任务和打印机状态

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
```

### 模型配置
```yaml
model:
  path: "yolov8n.pt"           # 模型文件路径
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

### Klipper配置
```yaml
klipper:
  enabled: true
  url: "http://192.168.1.100:7125"
  api_key: "你的API密钥"
```

## 注意事项

- 使用前请准备训练好的YOLOv8模型（`best.pt`或`yolov8n.pt`）
- 确保摄像头权限已配置
- 邮件发送需要SMTP授权码（非登录密码）
- 邮件回复需要开启IMAP服务
- YAML配置文件使用空格缩进，不支持Tab
- Klipper控制需要先配置Moonraker
- 程序支持Ctrl+C优雅退出
- 如需CUDA加速，需安装PyTorch CUDA版本，并在config.yaml中设置 `model.use_cuda: true`

## 邮件回复控制

用户收到告警邮件后，可回复以下指令控制打印机：
- **回复 0**：立即停止打印
- **回复 1**：继续打印，10分钟内不检测（可配置）

回复邮件主题需包含"Re:"或"回复"。

## 扩展功能

项目设计支持多种扩展：
- 添加新的检测模型
- 集成更多打印机控制接口
- 支持数据库存储历史记录
- 添加Web界面管理
- 支持多种告警方式（微信、短信等）

## 联系

- 邮箱：geekelement@outlook.com
