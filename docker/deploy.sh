#!/bin/bash

# 3D打印异常检测系统 - Linux 部署脚本
# 使用方法: ./deploy.sh [命令]
#   ./deploy.sh build    # 构建镜像
#   ./deploy.sh start    # 启动服务
#   ./deploy.sh stop     # 停止服务
#   ./deploy.sh restart  # 重启服务
#   ./deploy.sh logs     # 查看日志
#   ./deploy.sh status   # 查看状态
#   ./deploy.sh update   # 更新并重启

set -e

# 配置
PROJECT_NAME="print-detector"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
}

# 构建镜像
cmd_build() {
    log_info "构建 Docker 镜像..."
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache
    log_info "镜像构建完成"
}

# 启动服务
cmd_start() {
    log_info "启动服务..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    log_info "服务已启动"
    
    # 等待服务启动
    sleep 3
    
    # 获取服务器 IP
    IP=$(hostname -I | awk '{print $1}')
    log_info "访问地址: http://$IP:5000"
}

# 停止服务
cmd_stop() {
    log_info "停止服务..."
    docker-compose -f $DOCKER_COMPOSE_FILE down
    log_info "服务已停止"
}

# 重启服务
cmd_restart() {
    cmd_stop
    cmd_start
}

# 查看日志
cmd_logs() {
    log_info "查看日志 (按 Ctrl+C 退出)..."
    docker-compose -f $DOCKER_COMPOSE_FILE logs -f
}

# 查看状态
cmd_status() {
    log_info "容器状态:"
    docker-compose -f $DOCKER_COMPOSE_FILE ps
    
    log_info "\n资源使用情况:"
    docker stats --no-stream $PROJECT_NAME 2>/dev/null || log_warn "容器未运行"
}

# 更新并重启
cmd_update() {
    log_info "更新代码并重启服务..."
    
    # 拉取最新代码（如果是 git 仓库）
    if [ -d ".git" ]; then
        log_info "拉取最新代码..."
        git pull
    fi
    
    # 停止旧服务
    cmd_stop
    
    # 构建新镜像
    cmd_build
    
    # 启动新服务
    cmd_start
    
    log_info "更新完成"
}

# 清理资源
cmd_clean() {
    log_warn "清理未使用的 Docker 资源..."
    docker system prune -f
    log_info "清理完成"
}

# 显示帮助
cmd_help() {
    echo "3D打印异常检测系统 - 部署脚本"
    echo ""
    echo "使用方法: ./deploy.sh [命令]"
    echo ""
    echo "命令:"
    echo "  build    构建 Docker 镜像"
    echo "  start    启动服务"
    echo "  stop     停止服务"
    echo "  restart  重启服务"
    echo "  logs     查看日志"
    echo "  status   查看服务状态"
    echo "  update   更新代码并重启"
    echo "  clean    清理未使用的 Docker 资源"
    echo "  help     显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh start    # 首次部署"
    echo "  ./deploy.sh logs     # 查看运行日志"
}

# 主函数
main() {
    # 检查 Docker
    check_docker
    
    # 切换到脚本所在目录
    cd "$(dirname "$0")"
    
    # 执行命令
    case "${1:-help}" in
        build)
            cmd_build
            ;;
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        logs)
            cmd_logs
            ;;
        status)
            cmd_status
            ;;
        update)
            cmd_update
            ;;
        clean)
            cmd_clean
            ;;
        help|*)
            cmd_help
            ;;
    esac
}

# 运行主函数
main "$@"
