# 3D打印异常检测系统 - Docker 镜像 (Linux 版本)
# 基于 Python 3.10 轻量级镜像，适配 Linux 服务器部署

FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Linux 必需包）
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    gcc \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 修改 requirements.txt 使用 headless 版本 OpenCV（Linux 服务器无 GUI）
RUN sed -i 's/opencv-python==/opencv-python-headless==/g' requirements.txt || true

# 安装 Python 依赖
# 使用 CPU 版本的 PyTorch（Linux 服务器通用）
RUN pip install --no-cache-dir torch==2.5.1+cpu torchvision==0.20.1+cpu --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY src/ ./src/
COPY config.yaml .

# 创建必要的目录（Linux 权限）
RUN mkdir -p images/predicted images/captured models && \
    chmod -R 755 images/

# 健康检查 - 每30秒检查一次Web服务
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 暴露 Web 服务端口
EXPOSE 5000

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 启动命令 - 运行主程序
CMD ["python", "src/main.py"]
