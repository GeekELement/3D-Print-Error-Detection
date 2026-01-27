# 3D打印缺陷检测与告警系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.7%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/yolov8)

## 项目简介

本项目是一个轻量级的3D打印缺陷检测与告警系统，运行在3D打印机上位机（如树莓派、服务器或PC）上。系统通过摄像头周期性捕获打印过程的图像，使用YOLOv8深度学习模型进行缺陷检测，并在发现异常时通过邮件发送告警通知，帮助用户及时发现和处理打印问题，减少材料浪费和时间损失。

## 核心功能

- **摄像头监控**：定期捕获3D打印过程的图像
- **智能缺陷检测**：使用YOLOv8模型实时分析图像，检测打印缺陷
- **邮件告警**：当检测到高置信度缺陷时，发送带预测结果图片的邮件告警
- **图片管理**：自动保存原始捕获图像和带标注的预测结果图像
- **OctoPrint集成**：提供OctoPrint控制接口（可扩展实现自动停止打印等功能）

## 项目结构

```
3D_Print_Error_Detection/
├── README.md              # 项目说明文件
├── yolov8n.pt             # YOLOv8模型权重文件
├── src/
│   ├── main.py            # 主程序入口
│   ├── camera_capture.py  # 摄像头操作模块
│   ├── notify.py          # 邮件通知模块
│   └── octoprint_client.py # OctoPrint控制模块
├── images/
│   ├── predicted_pictures/ # 预测结果图片保存目录
│   └── saved_pictures/     # 原始捕获图片保存目录
└── YOLOv8_cs-main/         # YOLOv8相关代码和文档
```

## 技术栈

- **编程语言**：Python 3.8+
- **核心库**：
  - `ultralytics` - YOLOv8模型推理
  - `opencv-python` - 摄像头操作和图像处理
  - `requests` - OctoPrint API调用
  - `smtplib` - 邮件发送
- **硬件要求**：
  - 支持OpenCV的摄像头
  - 足够运行YOLOv8模型的计算资源（建议至少2GB RAM）

## 快速开始

### 环境要求

- Python 3.8+
- 支持OpenCV的摄像头
- 网络连接（用于邮件发送和可选的OctoPrint控制）

### 安装与部署

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd 3D_Print_Error_Detection
   ```

2. **安装Python依赖**
   ```bash
   pip install ultralytics opencv-python requests
   ```

3. **配置系统参数**
   修改 `src/main.py` 顶部的配置常量以适配你的环境：

   ```python
   # ───────────── 配置区 ─────────────
   MODEL_PATH = r"C:\Files\3D_Print_Error_Detection\yolov8n.pt"  # 模型路径
   CAMERA_INDEX = 0  # 摄像头索引

   INTERVAL_MIN = 0.1  # 检测间隔（分钟）
   CONF_THRESHOLD = 0.25  # YOLO 检测阈值
   ALERT_CONF_THRESHOLD = 0.70  # 报警阈值

   PREDICTED_IMAGE_DIR = r"C:\Files\3D_Print_Error_Detection\images\predicted_pictures"  # 预测结果保存目录

   EMAIL_ALERT_ENABLED = True  # 是否启用邮件告警
   EMAIL_TO = "your-email@example.com"  # 接收告警的邮箱
   EMAIL_FROM = "sender-email@example.com"  # 发送告警的邮箱
   EMAIL_PASSWORD = "your-email-password"  # 邮箱授权码（不是登录密码）
   ```

   同时，你可能需要修改 `src/camera_capture.py` 中的原始图像保存路径：

   ```python
   self.save_dir = r"C:\Files\3D_Print_Error_Detection\YOLOv8_cs-main\images\saved_pictures"
   ```

4. **运行系统**
   ```bash
   python src/main.py
   ```

   系统将开始周期性检测，每完成一次检测会在控制台输出检测结果。当检测到高置信度缺陷时，会发送邮件告警。

## 使用说明

### 邮件告警格式

当系统检测到高置信度缺陷时，会发送如下格式的邮件：

```
主题：【紧急】3D打印检测到异常

正文：
【3D打印异常警报】

检测时间：2026-01-27 19:30:00
异常目标：warping (0.85), stringing (0.72)

请尽快检查打印机状态。
预测图片已作为附件发送。
```

### 图片保存

- **原始图像**：保存在 `YOLOv8_cs-main/images/saved_pictures` 目录，文件名格式为 `print_YYYYMMDD_HHMMSS.jpg`
- **预测结果**：保存在 `images/predicted_pictures` 目录，文件名格式为 `pred_YYYYMMDD_HHMMSS.jpg`，包含YOLOv8检测到的目标标注

### OctoPrint集成（可选）

项目包含 `OctoPrintClient` 类，可用于控制OctoPrint服务器。要在检测到异常时自动控制打印机，可按以下步骤扩展：

1. 在 `src/main.py` 中导入并初始化 `OctoPrintClient`：

   ```python
   from octoprint_client import OctoPrintClient

   # 在配置区添加
   OCTOPRINT_URL = "http://octoprint.local:5000"
   OCTOPRINT_API_KEY = "your-octoprint-api-key"

   # 在main函数中初始化
   octoprint_client = OctoPrintClient(OCTOPRINT_URL, OCTOPRINT_API_KEY)
   ```

2. 在检测到异常时添加控制逻辑：

   ```python
   if should_alert and EMAIL_ALERT_ENABLED:
       # 发送邮件告警（现有代码）
       # ...
       
       # 添加自动停止打印逻辑
       try:
           octoprint_client.stop_print()
           print("已自动停止打印任务")
       except Exception as e:
           print(f"停止打印失败：{e}")
   ```

## 故障排查

### 常见问题

1. **无法打开摄像头**
   - 检查 `CAMERA_INDEX` 是否正确
   - 确保摄像头未被其他程序占用
   - 检查摄像头驱动是否正常

2. **模型加载失败**
   - 确认 `MODEL_PATH` 指向正确的 `.pt` 文件
   - 确保已正确安装 `ultralytics` 包

3. **邮件发送失败**
   - 验证邮件配置是否正确
   - 确保使用的是邮箱授权码而非登录密码
   - 检查网络连接是否正常
   - 对于某些邮箱服务（如Gmail），可能需要开启"允许不安全应用访问"选项

4. **图片保存失败**
   - 检查保存路径是否存在，确保程序有写入权限
   - 检查磁盘空间是否充足

## 开发与扩展

### 模型训练

项目默认使用 `yolov8n.pt` 预训练模型，你可以根据自己的打印场景和缺陷类型，使用 `YOLOv8_cs-main` 目录中的工具训练自定义模型，提高检测准确率。

### 功能扩展

- **Web界面**：添加Web界面实时查看监控画面和检测结果
- **多摄像头支持**：扩展系统支持多个摄像头从不同角度监控
- **短信告警**：集成短信服务，在没有网络邮件的环境下也能收到告警
- **自动修复建议**：基于检测到的缺陷类型，提供可能的解决方案建议

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 联系我们

如有问题或建议，欢迎提出Issue或Pull Request。

---

**注意**：在使用本系统前，请确保你已了解并遵守相关法律法规，特别是关于摄像头使用和数据隐私的规定。