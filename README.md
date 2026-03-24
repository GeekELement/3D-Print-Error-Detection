# 3D打印缺陷视觉监控系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.13%2B-green)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5%2B-red)](https://pytorch.org/)
[![YOLO](https://img.shields.io/badge/YOLO-orange)](https://github.com/ultralytics/ultralytics)
## 项目简介

本项目是一个部署在3D打印机上位机上的智能监控系统。它利用 **YOLOv8** 深度学习模型，周期性地对打印过程进行视觉检测。一旦识别到打印缺陷，系统会自动发送告警邮件（包含检测图片附件和Web监控链接），提醒用户及时检查。

## 核心功能

- **⏱️ 定时监控**：按配置间隔自动捕获打印画面并检测（默认3秒/次，可配置）
- **🔍 缺陷识别**：基于YOLOv8模型，精准检测多种常见3D打印缺陷
- **📧 邮件告警**：发现高置信度缺陷时，自动发送带图片附件的告警邮件，包含Web监控链接
- **📷 多相机支持**：支持本机USB摄像头、Bambu Lab A1打印机相机、视频文件调试
- **🌐 Web监控界面**：实时查看打印机状态、温度、进度、层数等，并可远程控制打印
- **🔧 Bambu Lab支持**：支持 Bambu Lab 打印机控制和状态监控
- **🎯 多帧确认机制**：连续多帧检测到缺陷才触发告警，减少误报
- **📷 ROI区域检测**：支持设置感兴趣区域，只检测指定范围内的缺陷
- **💾 本地存储**：自动保存原始拍摄图片和带标注的预测结果图片
- **⚙️ YAML配置**：使用YAML文件统一管理所有配置参数
- **🐛 调试模式**：支持视频文件测试，可控制取帧间隔
- **📡 MQTT支持**：通过MQTT协议连接Bambu Lab打印机
- **🐳 Docker部署**：支持Docker容器化部署（Linux服务器）
- **💡 亮度检测**：自动检测环境亮度，光线不足时跳过检测，避免浪费算力

## 技术栈

- **编程语言**: Python 3.10+
- **深度学习框架**: PyTorch 2.5.1+cu121, YOLOv8 (ultralytics 8.4.14)
- **计算机视觉库**: OpenCV 4.13.0.92
- **Web框架**: Flask 3.1.3, Flask-SocketIO 5.6.1
- **物联网协议**: MQTT (paho-mqtt 2.1.0)
- **打印机API**: bambulabs-api 2.6.6
- **配置管理**: PyYAML 6.0.3
- **HTTP客户端**: requests 2.32.5
- **容器化**: Docker, Docker Compose

## 快速开始

### 环境要求

- 硬件：带摄像头的上位机（调试可用视频文件）
- 操作系统: Linux / Windows
- Python: 3.10 或更高版本
- GPU/NPU: 可选（支持CUDA加速）

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
   核心依赖：`opencv-python>=4.6.0`, `torch>=1.7.0`, `ultralytics>=8.0.0`, `requests>=2.23.0`, `PyYAML>=6.0`, `numpy>=1.21.0`, `paho-mqtt`, `flask`, `flask-socketio`, `bambulabs-api`

3. **配置参数**
   编辑 `config.yaml` 配置文件

4. **运行程序**
   ```bash
   python src/main.py
   ```

#### 方式二：使用启动脚本（Linux服务器推荐）

适用于需要后台运行、开机自启或定时检查的场景。

1. **上传项目到Linux服务器**
   ```bash
   scp -r 3D_Print_Error_Detection user@server:/opt/
   ```

2. **配置启动脚本**
   ```bash
   cd /opt/3D_Print_Error_Detection/src
   chmod +x start.sh
   ```
   编辑 `start.sh`，修改以下配置：
   - `PROJECT_DIR`: 项目根目录路径
   - `CONDA_BASE`: Conda 安装路径
   - `CONDA_ENV`: Conda 环境名称
   - `DISPLAY_HOST`/`DISPLAY_PORT`: 启动提示信息中显示的地址和端口

3. **运行启动脚本**
   ```bash
   ./start.sh
   ```

4. **添加到定时任务（可选）**
   实现开机自启或定时检查服务状态：
   ```bash
   crontab -e
   # 每5分钟检查一次，如果服务未运行则自动启动
   */5 * * * * /opt/3D_Print_Error_Detection/src/start.sh >/dev/null 2>&1
   ```

**脚本功能说明：**
- 自动激活 Conda 环境
- 单实例保护（防止重复启动）
- 后台运行主程序（nohup）
- 自动记录日志到 `logs/script.log`
- 启动后显示 WebUI 访问地址

#### 方式三：Docker部署（Linux服务器）

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

   > 提示：可通过修改 `config.yaml` 中的 `app.web_port` 自定义端口

更多Docker部署详情，请参考 [docker/README.md](docker/README.md)

## 项目结构

```
3D_Print_Error_Detection/
├── README.md                     # 项目说明文档
├── requirements.txt              # Python依赖包列表
├── config.yaml                   # 配置文件
├── config.yaml.example           # 配置文件模板
├── images/                       # 图片存储目录
│   ├── captured/                 # 原始拍摄图片
│   └── predicted/                # 带标注的预测图片
├── 3D-printing-defects-database/ # 3D打印缺陷数据集
│   ├── train/                    # 训练集
│   ├── valid/                    # 验证集
│   ├── test/                     # 测试集
│   ├── video/                    # 测试视频目录
│   └── data.yaml                 # 数据集配置文件
├── YOLO/                         # YOLO模型目录
│   ├── best.pt                   # 训练好的YOLOv8模型权重（defects检测专用）
│   ├── yolov8/                   # YOLOv8 预训练模型目录
│   │   ├── yolov8n.pt            # YOLOv8n PyTorch 模型
│   │   └── yolov8n.onnx          # YOLOv8n ONNX 模型
│   └── yolov26/                  # YOLOv26 预训练模型目录（预留）
│       └── best.pt               # YOLOv26模型权重
├── src/                          # 源代码目录
│   ├── main.py                   # 主程序入口
│   ├── config.py                 # YAML配置加载
│   ├── camera.py                 # 摄像头操作 + 图片清理
│   ├── alerter.py                # 邮件告警 + 打印机控制客户端
│   ├── device.py                 # 设备管理（GPU/CPU）
│   ├── webui.py                  # Web监控界面 (Flask + SocketIO)
│   ├── webui.html                # Web监控前端页面
│   └── start.sh                  # Linux启动脚本（后台运行+定时任务）
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
- 根据配置决定是否使用CUDA加速
- 提供设备信息查询接口

### 3. 摄像头管理 (`camera.py`)
- 支持多种摄像头源：
  - `local`: 本地USB摄像头
  - `a1`: Bambu Lab A1打印机相机（通过webui队列获取）
  - `video`: 视频文件（调试模式）
- 自动图片清理，防止磁盘占满
- 摄像头预热和参数配置
- ROI区域支持

### 4. 缺陷检测 (`main.py`)
- 基于YOLOv8的实时缺陷检测
- **多帧确认机制**：连续N帧检测到缺陷才触发告警，减少误报
- **面积阈值过滤**：计算缺陷区域并集面积，避免小噪点干扰
- **ROI区域过滤**：只检测指定区域内的缺陷
- **打印状态检查**：A1模式下只在打印进行时检测
- **亮度检测**：自动检测环境亮度，光线不足时跳过检测

### 5. 告警系统 (`alerter.py`)
- SMTP邮件发送（支持SSL加密）
- 带图片附件和Web监控链接
- Bambu Lab打印机MQTT控制（暂停/恢复/停止）

### 6. Web监控 (`webui.py`)
- Flask + SocketIO实时通信
- 打印机状态监控（温度、进度、层数等）
- 远程控制功能（暂停/继续/停止/LED控制）
- 实时视频流显示
- 自动连接打印机功能

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
来源：https://universe.roboflow.com/hcmut-yxyhm/3d-printing-defects-database

## 配置文件说明

编辑 `config.yaml` 配置各项参数：

```yaml
# ───────────── 调试模式 ─────────────
debug:
  video_path: ""                       # 视频文件路径，留空使用摄像头
  frame_interval: 30                   # 视频模式：每隔多少帧识别一次

# ───────────── 模型配置 ─────────────
model:
  path: "YOLO/best.pt"                # YOLO 模型文件路径（相对于项目根目录）
  conf_threshold: 0.5                 # 检测置信度阈值 (0.0-1.0)

# ───────────── 多帧检测配置 ─────────────
# 逻辑：阳性帧数 >= required_frames → 当前帧面积 >= area_threshold → 告警
multi_frame:
  enabled: true                       # 是否启用多帧检测
  required_frames: 5                  # 阳性帧数达到此值后验证面积
  alert_conf_threshold: 0.65          # 单帧置信度阈值 (0.0-1.0)
  area_threshold: 900                 # 面积阈值 (像素²)

# ───────────── 监控配置 ─────────────
monitoring:
  interval_sec: 3                     # 检测间隔（秒）
  brightness_threshold: 85             # 亮度阈值 (0-255)，低于此值跳过检测（避免夜间或光线不足时浪费算力）

# ───────────── 摄像头配置 ─────────────
camera:
  source: local                        # 相机来源: local/a1
  index: 0                            # 摄像头索引
  width: 640                          # 分辨率宽度
  height: 480                         # 分辨率高度
  warmup_frames: 8                    # 预热帧数
  max_captured: 1                     # captured目录保留最新图片数量
  max_predicted: 1                    # predicted目录保留最新图片数量
  roi:
    enabled: false                    # 是否启用ROI区域检测
    x1: 100                           # 左上角X坐标
    y1: 100                           # 左上角Y坐标
    x2: 540                           # 右下角X坐标
    y2: 380                           # 右下角Y坐标

# ───────────── 目录配置 ─────────────
directories:
  project_root: ".."                   # 项目根目录
  predicted_dir: "images/predicted"    # 预测图片保存目录
  captured_dir: "images/captured"      # 原始图片保存目录

# ───────────── 邮件报警配置 ─────────────
email:
  enabled: true                       # 是否启用邮件报警
  to: "your_email@domain.com"         # 接收邮件地址
  from: "your_email@domain.com"       # 发送邮件地址
  password: "xxxx"                    # SMTP授权码/应用密码
  smtp:
    server: "smtp.qq.com"             # SMTP服务器
    port: 465                         # SMTP端口
    use_ssl: true                     # 是否使用SSL

# ───────────── Bambu Lab 打印机配置 ─────────────
printer:
  host: "192.168.1.100"               # 打印机IP地址
  access_code: ""                     # 访问代码
  serial_number: ""                   # 打印机序列号

# ───────────── 程序设置 ─────────────
app:
  web_url: "http://localhost:5000"     # Web监控页面地址（用于邮件告警）
  web_port: 5000                       # Web服务器端口
```

完整配置请参考 `config.yaml.example`

## 使用说明

### 启动系统

```bash
python src/main.py
```

启动后会自动：
1. 加载YOLO模型
2. 启动Web服务（端口5000）
3. 根据配置自动连接打印机（A1模式）
4. 开始定时检测循环

### 访问Web界面

打开浏览器访问：
```
http://localhost:5000
```

> 如果修改了 `config.yaml` 中的 `app.web_port`，请使用对应端口访问

Web界面功能：
- **连接/断开打印机**：手动控制打印机连接
- **实时状态显示**：打印状态、进度、当前层/总层数、喷嘴温度、热床温度
- **实时视频流**：显示打印机摄像头画面
- **远程控制**：暂停、继续、停止打印，控制LED灯
- **日志输出**：显示连接状态和操作日志

### 查看检测结果

- 原始图片：`images/captured/`
- 预测结果：`images/predicted/`

### 检测逻辑说明

系统采用**多帧确认机制**减少误报：

1. **单帧检测**：每帧检测时，置信度≥`alert_conf_threshold` 且 面积≥`area_threshold` 才记为阳性帧
2. **多帧确认**：连续检测到 `required_frames` 个阳性帧后才触发告警
3. **面积计算**：多个spaghetti框的并集面积，避免重复计算
4. **状态检查**：A1模式下，只在打印机状态为 PRINTING/RUNNING 时进行检测
5. **亮度检测**：自动检测画面亮度，综合评分（中位数×0.6 + 25%分位数×0.4）低于 `brightness_threshold` 时跳过检测

## 注意事项

1. **首次运行**：系统会自动创建必要的目录结构
2. **模型文件**：确保 `YOLO/best.pt` 存在于项目根目录，或在配置中指定正确路径
3. **邮件配置**：需要正确的SMTP服务器信息和授权码（不是登录密码）
4. **摄像头权限**：Linux系统可能需要添加用户到video组
5. **防火墙**：确保5000端口（或自定义的 `app.web_port`）未被防火墙阻挡
6. **A1打印机**：需要在配置中正确设置IP地址、访问代码和序列号
7. **Docker部署**：请参考 [docker/README.md](docker/README.md) 进行部署

## 故障排查

### 摄像头无法打开
```bash
# Linux检查摄像头设备
ls /dev/video*

# 检查权限
sudo usermod -aG video $USER
```

### A1相机无法连接
- 确认打印机IP地址、访问代码、序列号配置正确
- 确保打印机和上位机在同一局域网
- 检查打印机固件版本是否支持MQTT

### 模型加载失败
- 检查 `YOLO/best.pt` 文件是否存在
- 检查PyTorch和ultralytics版本兼容性

### 邮件发送失败
- 检查SMTP服务器地址和端口
- 确认使用的是授权码而非登录密码
- 检查邮箱是否开启SMTP服务

### Docker部署问题
- 检查Docker和Docker Compose版本
- 查看容器日志：`docker logs print-detector`
- 检查端口占用：`netstat -tlnp | grep 5000`（或自定义端口）

## 开发计划

- [ ] 支持更多打印机品牌（Klipper等）
- [x] 完善Docker部署测试
- [ ] 优化检测算法，降低误报率
- [ ] 支持多打印机同时监控
- [ ] 添加模型在线更新功能
- [ ] 添加历史记录和统计功能

## 许可证

MIT License

## 致谢

- [Ultralytics](https://github.com/ultralytics/ultralytics)
- [Bambu Lab Wiki](https://wiki.bambulab.com/zh/knowledge-sharing/Spaghetti_detection)
- [Bambu Lab API](https://github.com/mchrisgm/bambulabs_api)
- [Roboflow Universe](https://universe.roboflow.com/)

## 联系方式

geekelement@outlook.com

如有问题或建议，欢迎提交Issue或Pull Request。
