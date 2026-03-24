#!/bin/bash

# =============================================
# 3D 打印缺陷检测系统 - Linux 启动脚本
# =============================================
# 功能说明：
#   本脚本用于在 Linux 系统上启动 3D 打印缺陷检测服务。
#   它会自动激活 Conda 环境、检查程序状态、防止重复启动，
#   并在后台运行主程序。
#
# 使用方法：
#   1. 直接运行: ./start.sh
#   2. 添加到定时任务(crontab)实现开机自启或定时检查
#      例如: */5 * * * * /path/to/start.sh >/dev/null 2>&1
#
# 配置文件：
#   请在 config.yaml 中修改以下配置：
#   - app.web_port: Web 服务端口（默认 5000）
#   - printer.host: 打印机 IP 地址
#   - email.to: 告警邮件接收地址
# =============================================

# ------------ 用户配置区域（请修改以下路径）------------
# 项目根目录 - 请修改为实际部署路径
PROJECT_DIR="/path/to/3D_Print_Error_Detection/"

# Conda 安装路径 - 请根据实际安装位置修改
CONDA_BASE="/path/to/miniconda3"

# Conda 环境名称
CONDA_ENV="3dprint"

# 显示配置（仅用于启动提示信息，不影响实际运行）
DISPLAY_HOST="<ip>"      # 显示的服务器地址，如：192.168.1.100 或 <ip>
DISPLAY_PORT="<port>"    # 显示的端口号，如：5000 或 <port>
# -----------------------------------------------------

# 自动计算其他路径
SRC_DIR="${PROJECT_DIR}src/"
MAIN_SCRIPT="${SRC_DIR}main.py"
PID_FILE="${PROJECT_DIR}script.pid"
LOG_FILE="${PROJECT_DIR}logs/script.log"

# 创建日志目录（如果不存在）
mkdir -p "${PROJECT_DIR}logs"

# 记录启动时间到日志
echo "========================================" >> "$LOG_FILE"
echo "$(date): 开始启动脚本" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 加载 Conda 初始化脚本
# 作用：设置 conda 命令和环境变量
if [ -f "${CONDA_BASE}/etc/profile.d/conda.sh" ]; then
    source "${CONDA_BASE}/etc/profile.d/conda.sh"
    echo "$(date): 成功加载 conda.sh" >> "$LOG_FILE"
else
    echo "$(date): 错误：找不到 conda.sh，请检查 CONDA_BASE 路径" >> "$LOG_FILE"
    exit 1
fi

# 激活指定的 Conda 环境
conda activate "$CONDA_ENV" 2>> "$LOG_FILE"
if [ $? -eq 0 ]; then
    echo "$(date): 成功激活环境 $CONDA_ENV" >> "$LOG_FILE"
else
    echo "$(date): 错误：无法激活环境 $CONDA_ENV" >> "$LOG_FILE"
    exit 1
fi

# 切换到项目源码目录
cd "$SRC_DIR"
if [ $? -eq 0 ]; then
    echo "$(date): 成功进入目录 $SRC_DIR" >> "$LOG_FILE"
else
    echo "$(date): 错误：无法进入目录 $SRC_DIR" >> "$LOG_FILE"
    exit 1
fi

echo "$(date): 当前工作目录: $(pwd)" >> "$LOG_FILE"

# 检查主程序文件是否存在
if [ -f "$MAIN_SCRIPT" ]; then
    echo "$(date): 找到主脚本 $MAIN_SCRIPT" >> "$LOG_FILE"
else
    echo "$(date): 错误：找不到 main.py 文件！" >> "$LOG_FILE"
    echo "$(date): 检查路径: $MAIN_SCRIPT" >> "$LOG_FILE"
    echo "$(date): 当前目录文件列表：" >> "$LOG_FILE"
    ls -la >> "$LOG_FILE"
    exit 1
fi

# 单实例保护：检查程序是否已经在运行
# 原理：通过 PID 文件记录进程号，避免重复启动多个实例
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    # 检查该 PID 是否真实存在
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date): 脚本已在运行，PID: $PID，退出" >> "$LOG_FILE"
        echo "脚本已在运行（PID: $PID），无需重复启动。"
        exit 0
    else
        # PID 文件存在但进程已结束，清理过期文件
        echo "$(date): 发现过期 PID 文件，自动清理" >> "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
fi

# 启动 main.py 服务
echo "$(date): 正在启动 main.py ..." >> "$LOG_FILE"

nohup python "$MAIN_SCRIPT" >> "$LOG_FILE" 2>&1 &
PID=$!

echo "$PID" > "$PID_FILE"

# 等待 3 秒后检查程序是否成功启动
sleep 3

if ps -p "$PID" > /dev/null 2>&1; then
    # 启动成功
    echo "$(date): 启动成功！PID: $PID" >> "$LOG_FILE"

    echo "$(date): WebUI 访问地址: http://${DISPLAY_HOST}:${DISPLAY_PORT}" >> "$LOG_FILE"

    echo ""
    echo "✅ 启动成功！"
    echo "   PID: $PID"
    echo "   WebUI 地址: http://${DISPLAY_HOST}:${DISPLAY_PORT}"
    echo "   日志文件: $LOG_FILE"
    echo "   主脚本路径: $MAIN_SCRIPT"
else
    # 启动失败
    echo "$(date): 启动失败！请检查日志" >> "$LOG_FILE"
    rm -f "$PID_FILE"
    echo ""
    echo "❌ 启动失败，请查看日志文件："
    echo "   $LOG_FILE"
    echo "   建议执行: tail -n 50 $LOG_FILE"
fi
