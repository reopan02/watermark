#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PORT=8666
NO_LOG=false

for arg in "$@"; do
    case "$arg" in
        --no-log) NO_LOG=true ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

echo "============================================"
echo "  两阶段图像处理应用 - 启动中..."
echo "  后端地址: http://localhost:$PORT"
echo "  前端请打开: frontend/index.html"
echo "============================================"
echo ""

cd "$BACKEND_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "[错误] 未找到虚拟环境，请先创建: python3 -m venv .venv"
    exit 1
fi

export LOG_LEVEL="WARNING"

if [ "$NO_LOG" = true ]; then
    echo "[启动] 后端服务 (端口 $PORT, 静默模式)..."
    nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port "$PORT" > /dev/null 2>&1 &
else
    echo "[启动] 后端服务 (端口 $PORT)..."
    nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port "$PORT" > "$SCRIPT_DIR/server.log" 2>&1 &
    echo "       日志输出: $SCRIPT_DIR/server.log"
fi

PID=$!
echo "$PID" > "$SCRIPT_DIR/server.pid"

sleep 2

if kill -0 "$PID" 2>/dev/null; then
    echo ""
    echo "[完成] 服务已启动! (PID: $PID)"
    echo "       后端 API:  http://localhost:$PORT"
    echo "       健康检查:  http://localhost:$PORT/api/health"
    echo "       前端页面:  请在浏览器打开 frontend/index.html"
    echo ""
    echo "[提示] 前端设置中后端地址请填写: http://localhost:$PORT"
    echo "       停止服务: ./stop.sh 或 kill $PID"
else
    echo "[错误] 服务启动失败，请检查配置"
    exit 1
fi
