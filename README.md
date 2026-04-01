# 两阶段图像处理应用

基于 Grok + Gemini 的两阶段图像处理 Web 应用：先去除文字/水印，再补全画面。

## 功能

- **步骤1 - 去除文字/水印**：调用 Grok 模型自动去除图像中的文字和水印
- **步骤2 - 补全画面**：调用 Gemini 模型进行全画幅扩展，输出 2K 分辨率图像
- **步骤联动**：步骤1 完成后一键进入步骤2，自动填充结果
- **下载保存**：每个步骤的结果均可一键下载

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 后端服务
│   ├── requirements.txt     # Python 依赖
│   ├── .env.example         # 环境变量模板
│   └── .env                 # 实际配置（需自行创建）
├── frontend/
│   └── index.html           # 单页前端应用
├── start.bat                # Windows 一键启动脚本
├── start.sh                 # Linux 一键启动脚本
├── stop.sh                  # Linux 停止服务脚本
└── README.md
```

## 快速开始

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
GROK_API_KEY=your_api_key
GROK_BASE_URL=https://yunwu.ai/v1
GROK_MODEL=grok-4.2-image

GEMINI_API_KEY=your_api_key
GEMINI_BASE_URL=https://yunwu.ai
GEMINI_MODEL=gemini-3-pro-image-preview
```

### 2. 创建虚拟环境并安装依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 3. 启动服务

**Linux：**

```bash
chmod +x start.sh stop.sh
./start.sh            # 前台运行，日志输出到 server.log
./start.sh --no-log   # 静默模式，不输出日志
./stop.sh             # 停止服务
```

**Windows：**

```cmd
start.bat
```

服务启动在端口 **8666**。

### 4. 打开前端

在浏览器中打开 `frontend/index.html`，首次使用点击右上角齿轮图标，确认后端地址为 `http://localhost:8666`。

## 技术栈

- **后端**：Python + FastAPI + httpx
- **前端**：纯 HTML/CSS/JS 单页应用
- **AI 模型**：Grok (去除水印) + Gemini (画面补全)

## API 接口

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/task1` | POST | 去除文字/水印 |
| `/api/task2` | POST | 补全画面 |
| `/api/health` | GET | 健康检查 |

请求体：

```json
{
  "image_base64": "data:image/png;base64,...",
  "source_task_id": "optional_task_id"
}
```

响应体：

```json
{
  "task_id": "task1_xxxx",
  "result_image_base64": "data:image/png;base64,...",
  "message": "文字/水印去除完成"
}
```
