# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.6%2B-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5%2B-red)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/ultralytics)

## 项目简介

本项目是一个部署在3D打印机上位机上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件和Web监控链接），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认3秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件，包含Web监控链接
- **📷 多相机支持**：支持本机USB摄像头、Bambu Lab A1打印机相机、视频文件
- **🌐 Web监控界面**：实时查看打印机状态、温度、进度、层数等，并可远程控制打印
- **🔧 Bambu Lab支持**：支持 Bambu Lab 打印机控制
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数
- **🐛 调试模式**：支持视频文件测试，可控制取帧间隔
- **📡 MQTT支持**：通过MQTT协议连接Bambu Lab打印机
- **🐳 Docker部署**：支持Docker容器化部署（Linux服务器）

## 技术栈

- **编程语言**: Python 3.10+
- **深度学习框架**: PyTorch 2.5+, YOLOv8 (ultralytics)
- **计算机视觉库**: OpenCV 4.6+
- **Web框架**: Flask 3.x, Flask-SocketIO
- **物联网协议**: MQTT (paho-mqtt)
- **打印机API**: bambulabs-api
- **配置管理**: PyYAML
- **HTTP客户端**: requests
- **容器化**: Docker, Docker Compose

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（调试可用视频文件）
- 操作系统: Linux / Windows
- Python: 3.10 或更高版本
- GPU/NPU: 可选（目前只支持CUDA加速）

### 安装与部署

#### 方式一：本地运行

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

#### 方式二：Docker部署（Linux服务器）

> ⚠️ **注意：Docker部署功能尚未经过完整测试，使用时请谨慎。**

1. **上传项目到Linux服务器**
   ```bash
   scp -r 3D_Print_Error_Detection user@server:/opt/
   ```

2. **使用部署脚本**
   ```bash
   cd /opt/3D_Print_Error_Detection/docker
   chmod +x deploy.sh
   ./deploy.sh build
   ./deploy.sh start
   ```

3. **访问服务**
   ```
   http://server-ip:5000
   ```

更多Docker部署详情，请参考 [docker/README.md](docker/README.md)

## 项目结构

```
3D_Print_Error_Detection/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python依赖包列表
├── config.yaml                   # 配置文件
├── config.yaml.example           # 配置文件模板
├── best.pt                       # 训练好的YOLOv8模型权重
├── best.onnx                     # ONNX格式模型权重（可选）
├── images/                       # 图片存储目录
│   ├── captured/                 # 原始拍摄图片
│   └── predicted/                # 带标注的预测图片
├── 3D-printing-defects-database/ # 3D打印缺陷数据集
│   ├── train/                    # 训练集
│   ├── valid/                    # 验证集
│   ├── test/                     # 测试集
│   └── data.yaml                 # 数据集配置文件
├── src/                          # 源代码目录
│   ├── main.py                   # 主程序入口
│   ├── config.py                 # YAML配置加载
│   ├── camera.py                 # 摄像头操作 + 图片清理
│   ├── alerter.py                # 邮件告警 + 打印机控制客户端
│   ├── device.py                 # 设备管理（GPU/CPU）
│   ├── webui.py                  # Web监控界面 (Flask + SocketIO)
│   └── webui.html                # Web监控前端页面
└── docker/                       # Docker部署配置
    ├── Dockerfile                # Docker镜像构建文件
    ├── docker-compose.yml        # Docker Compose配置
    ├── deploy.sh                 # Linux一键部署脚本
    └── README.md                 # Docker部署说明
```

## 核心模块

### 1. 配置管理 (`config.py`)
- 使用YAML格式配置文件
- 支持路径自动计算（相对路径/绝对路径）
- 配置验证和目录创建
- 提供类型安全的配置读取接口

### 2. 设备管理 (`device.py`)
- 自动检测GPU/CUDA可用性
- 提供设备信息查询接口

### 3. 摄像头管理 (`camera.py`)
- 支持多种摄像头源（本地USB、Bambu Lab A1、视频文件）
- 自动图片清理，防止磁盘占满
- 摄像头预热和参数配置

### 4. 缺陷检测 (`main.py`)
- 基于YOLOv8的实时缺陷检测
- 多帧确认机制，减少误报
- 面积阈值过滤，避免小噪点干扰

### 5. 告警系统 (`alerter.py`)
- SMTP邮件发送
- 支持SSL加密
- 带图片附件和Web链接

### 6. Web监控 (`webui.py`)
- Flask + SocketIO实时通信
- 打印机状态监控
- 远程控制功能（暂停/继续/停止）

### 7. 数据集 (`3D-printing-defects-database/`)
本项目使用的3D打印缺陷数据集来自 Roboflow Universe，包含以下缺陷类型：
- **spaghetti** (面条化/拉丝)
- **stringing** (拉丝)
- **zits** (疙瘩/气泡)

数据集结构：
- `train/` - 训练集图片和标注
- `valid/` - 验证集图片和标注
- `test/` - 测试集图片和标注
- `data.yaml` - 数据集配置文件

数据集许可证：CC BY 4.0
来源：https://universe.roboflow.com/hcmut-yxyhm/3d-printing-defects

## 配置文件说明

编辑 `config.yaml` 配置各项参数：

```yaml
# 模型配置
model:
  path: "best.pt"                     # YOLO模型路径
  conf_threshold: 0.5                 # 检测置信度阈值

# 监控配置
monitoring:
  interval_sec: 3                     # 检测间隔（秒）

# 摄像头配置
camera:
  source: local                        # 来源: local/a1
  index: 0                            # 摄像头索引

# 邮件配置
email:
  enabled: true
  to: "your_email@example.com"
  smtp:
    server: "smtp.qq.com"
    port: 465

# 打印机配置
printer:
  host: "192.168.1.100"
  access_code: ""
  serial_number: ""
```

完整配置请参考 `config.yaml.example`

## 使用说明

### 启动系统

```bash
python src/main.py
```

启动后会自动：
1. 加载YOLOv8模型
2. 启动Web服务（端口5000）
3. 开始定时检测循环

### 访问Web界面

打开浏览器访问：
```
http://localhost:5000
```

### 查看检测结果

- 原始图片：`images/captured/`
- 预测结果：`images/predicted/`

## 注意事项

1. **首次运行**：系统会自动创建必要的目录结构
2. **模型文件**：确保 `best.pt` 存在于项目根目录或配置的路径
3. **邮件配置**：需要正确的SMTP服务器信息和授权码
4. **摄像头权限**：Linux系统可能需要添加用户到video组
5. **防火墙**：确保5000端口未被防火墙阻挡
6. **Docker部署**：⚠️ **尚未经过完整测试，生产环境请谨慎使用**

## 故障排查

### 摄像头无法打开
```bash
# Linux检查摄像头设备
ls /dev/video*

# 检查权限
sudo usermod -aG video $USER
```

### 模型加载失败
- 检查 `best.pt` 文件是否存在
- 检查PyTorch和ultralytics版本兼容性

### 邮件发送失败
- 检查SMTP服务器地址和端口
- 确认使用的是授权码而非登录密码
- 检查邮箱是否开启SMTP服务

### Docker部署问题
- 检查Docker和Docker Compose版本
- 查看容器日志：`docker logs print-detector`
- 检查端口占用：`netstat -tlnp | grep 5000`

## 开发计划

- [ ] 支持更多打印机品牌（Klipper等）
- [ ] 完善Docker部署测试
- [ ] 优化检测算法，降低误报率
- [ ] 支持多打印机同时监控
- [ ] 添加模型在线更新功能

## 许可证

MIT License

## 致谢

- [Ultralytics](https://github.com/ultralytics/ultralytics)
- [Bambu Lab API](https://github.com/mchrisgm/bambulabs_api)
- [Roboflow Universe](https://universe.roboflow.com/) - 提供3D打印缺陷数据集

## 联系方式

如有问题或建议，欢迎提交Issue或Pull Request。
