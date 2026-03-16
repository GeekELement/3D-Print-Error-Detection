# 3D打印异常检测系统 - Linux Docker 部署指南

本文档介绍如何在 Linux 服务器上使用 Docker 部署 3D打印异常检测系统。

## 环境要求

- Linux 操作系统（Ubuntu 20.04+ / CentOS 7+ / Debian 10+）
- Docker 20.10+
- Docker Compose 1.29+
- 至少 2GB 内存
- 至少 10GB 磁盘空间

## 文件说明

```
docker/
├── Dockerfile              # Docker 镜像构建文件（Linux 优化版）
├── docker-compose.yml      # Docker Compose 编排配置
├── .dockerignore          # Docker 构建忽略文件
├── deploy.sh              # Linux 一键部署脚本
└── README.md              # 本说明文档
```

## 快速部署

### 1. 安装 Docker（如未安装）

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# 重新登录使权限生效
```

**CentOS/RHEL:**
```bash
sudo yum install -y docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# 重新登录使权限生效
```

### 2. 上传项目到 Linux 服务器

```bash
# 在 Windows 上使用 scp 上传
scp -r C:\Files\Projects\3D_Print_Error_Detection user@your-server-ip:/opt/

# 或者使用 git 克隆
git clone https://github.com/your-repo/3D_Print_Error_Detection.git /opt/3D_Print_Error_Detection
```

### 3. 使用部署脚本一键部署

```bash
# 进入项目目录
cd /opt/3D_Print_Error_Detection/docker

# 给脚本添加执行权限
chmod +x deploy.sh

# 构建镜像
./deploy.sh build

# 启动服务
./deploy.sh start

# 查看日志
./deploy.sh logs
```

### 4. 访问服务

```
http://your-server-ip:5000
```

## 部署脚本命令

| 命令 | 说明 |
|------|------|
| `./deploy.sh build` | 构建 Docker 镜像 |
| `./deploy.sh start` | 启动服务 |
| `./deploy.sh stop` | 停止服务 |
| `./deploy.sh restart` | 重启服务 |
| `./deploy.sh logs` | 查看实时日志 |
| `./deploy.sh status` | 查看服务状态 |
| `./deploy.sh update` | 更新代码并重启 |
| `./deploy.sh clean` | 清理 Docker 资源 |

## 使用 Docker Compose 手动部署

```bash
cd /opt/3D_Print_Error_Detection/docker

# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建
docker-compose build --no-cache
```

## Linux 系统服务配置（可选）

创建 systemd 服务文件，实现开机自启：

```bash
sudo tee /etc/systemd/system/print-detector.service > /dev/null <<EOF
[Unit]
Description=3D Print Error Detector
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/3D_Print_Error_Detection/docker
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable print-detector
sudo systemctl start print-detector
sudo systemctl status print-detector
```

## 防火墙配置

**Ubuntu/Debian (UFW):**
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

**CentOS/RHEL (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

**iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo service iptables save
```

## 目录结构说明

Linux 服务器上的目录映射：

| 宿主机路径 | 容器路径 | 说明 |
|------------|----------|------|
| `/opt/3D_Print_Error_Detection/config.yaml` | `/app/config.yaml` | 配置文件（只读） |
| `/opt/3D_Print_Error_Detection/images` | `/app/images` | 图片输出目录 |
| `/opt/3D_Print_Error_Detection/models` | `/app/models` | 模型文件（只读） |

## 故障排查

### 查看容器日志
```bash
docker logs print-detector
docker-compose logs -f
```

### 进入容器内部
```bash
docker exec -it print-detector /bin/bash
```

### 检查容器状态
```bash
docker ps -a | grep print-detector
docker-compose ps
```

### 检查端口占用
```bash
sudo netstat -tlnp | grep 5000
sudo ss -tlnp | grep 5000
```

### 重启服务
```bash
./deploy.sh restart
# 或
docker-compose restart
```

### 查看系统资源
```bash
docker stats print-detector
free -h
df -h
```

## 更新部署

```bash
cd /opt/3D_Print_Error_Detection/docker

# 拉取最新代码（如果使用 git）
git pull

# 更新并重启
./deploy.sh update
```

## 卸载清理

```bash
cd /opt/3D_Print_Error_Detection/docker

# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi print-detector:latest

# 清理未使用的资源
docker system prune -f
```

## 注意事项

1. **配置文件**：确保 `config.yaml` 存在于项目根目录，并根据需要修改
2. **模型文件**：将 YOLO 模型文件放在 `models/` 目录下
3. **权限问题**：如果遇到权限错误，确保当前用户在 docker 组中
4. **端口冲突**：确保 5000 端口未被其他服务占用
5. **内存限制**：根据服务器配置调整 docker-compose.yml 中的内存限制

## 联系支持

如有问题，请查看日志或联系技术支持。
