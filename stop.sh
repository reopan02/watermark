#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/server.pid" ]; then
    PID=$(cat "$SCRIPT_DIR/server.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "[停止] 服务已停止 (PID: $PID)"
    else
        echo "[提示] 进程 $PID 已不存在"
    fi
    rm -f "$SCRIPT_DIR/server.pid"
else
    echo "[提示] 未找到 PID 文件，服务可能未运行"
    echo "       手动停止: lsof -i :8666 或 pkill -f 'uvicorn main:app'"
fi
