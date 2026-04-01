"""
两阶段图像处理应用 - 后端服务
FastAPI + LangChain 封装 Grok / Gemini 多模型调用
"""

import base64 as b64mod
import json
import logging
import os
import re
import uuid

import httpx

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="两阶段图像处理应用", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ──────────────────────────────────────────────
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.2-image")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://yunwu.ai")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro-image-preview")


# ─── Models ──────────────────────────────────────────────
class TaskRequest(BaseModel):
    """统一任务请求"""

    image_base64: str  # data:image/png;base64,... 或纯 base64
    source_task_id: str | None = None  # 步骤联动时传入


class TaskResponse(BaseModel):
    """统一任务响应"""

    task_id: str
    result_image_base64: str  # data:image/png;base64,...
    message: str


# ─── Helpers ─────────────────────────────────────────────
def parse_base64_image(raw: str) -> tuple[str, str]:
    """
    解析 base64 图像，返回 (mime_type, pure_base64)
    支持 data:image/png;base64,xxx 和纯 base64 两种格式
    """
    match = re.match(r"^data:(image/\w+);base64,(.+)$", raw, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    # 纯 base64，默认 png
    return "image/png", raw


def extract_base64_from_response(text: str) -> str | None:
    """从模型响应文本中提取 base64 图像数据"""
    # 尝试匹配 data:image 格式
    match = re.search(r"data:image/\w+;base64,[A-Za-z0-9+/=]+", text)
    if match:
        return match.group(0)
    # 尝试匹配纯 base64 块（至少100字符的连续base64）
    match = re.search(r"[A-Za-z0-9+/=]{100,}", text)
    if match:
        return f"data:image/png;base64,{match.group(0)}"
    return None


def extract_image_url_from_response(text: str) -> str | None:
    """从模型响应文本中提取图片 URL（Markdown 或裸链接）"""
    # Markdown 格式: ![...](url)
    match = re.search(r"!\[.*?\]\((https?://[^\s)]+)\)", text)
    if match:
        return match.group(1)
    # 裸 URL 格式
    match = re.search(r"(https?://\S+\.(?:jpg|jpeg|png|webp|gif))", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


async def download_image_as_base64(url: str) -> str:
    """下载远程图片并转为 data:image/xxx;base64,... 格式"""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = (
            resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        )
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"
        encoded = b64mod.b64encode(resp.content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"


# ─── Task 1: 去除文字/水印 (Grok) ────────────────────────


@app.post("/api/task1", response_model=TaskResponse)
async def task1_remove_watermark(req: TaskRequest):
    """
    步骤1：去除文字/水印
    使用 grok-4.2-image 模型 (OpenAI 兼容格式)
    """
    if not GROK_API_KEY:
        raise HTTPException(status_code=500, detail="GROK_API_KEY 未配置")

    mime_type, pure_b64 = parse_base64_image(req.image_base64)
    task_id = f"task1_{uuid.uuid4().hex[:12]}"

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{pure_b64}"},
                    },
                    {"type": "text", "text": "Remove all watermarks and text"},
                ],
            }
        ],
        "max_tokens": 16384,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{GROK_BASE_URL}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # ── 打印完整响应用于排查 ──
        logger.info("=" * 60)
        logger.info("Grok API 完整响应:")
        logger.info(json.dumps(data, ensure_ascii=False, default=str)[:5000])
        logger.info("=" * 60)

        # 解析响应 - Grok 图像模型返回格式
        choices = data.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="Grok 模型未返回结果")

        message = choices[0].get("message", {})
        content = message.get("content", "")

        logger.info(f"content 类型: {type(content).__name__}")
        if isinstance(content, str):
            logger.info(f"content 文本 (前500字符): {content[:500]}")
        elif isinstance(content, list):
            logger.info(f"content 列表长度: {len(content)}")
            for i, item in enumerate(content):
                logger.info(
                    f"  content[{i}]: {json.dumps(item, ensure_ascii=False, default=str)[:300]}"
                )
        else:
            logger.info(f"content 未知类型内容: {str(content)[:500]}")

        # 尝试从 content 中提取图像
        result_image = None

        # 如果 content 是列表（多模态响应）
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        result_image = item["image_url"]["url"]
                        break
                    elif item.get("type") == "image":
                        img_data = item.get("data") or item.get("image", "")
                        if img_data:
                            result_image = (
                                f"data:image/png;base64,{img_data}"
                                if not img_data.startswith("data:")
                                else img_data
                            )
                            break
        elif isinstance(content, str):
            result_image = extract_base64_from_response(content)
            # 如果没有 base64，尝试提取图片 URL 并下载
            if not result_image:
                img_url = extract_image_url_from_response(content)
                if img_url:
                    logger.info(f"检测到图片 URL，正在下载: {img_url}")
                    result_image = await download_image_as_base64(img_url)

        if not result_image:
            raise HTTPException(
                status_code=502, detail="无法从 Grok 响应中提取图像结果"
            )

        return TaskResponse(
            task_id=task_id,
            result_image_base64=result_image,
            message="文字/水印去除完成",
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Grok API 调用失败: {e.response.status_code} - {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Grok API 请求错误: {str(e)}")


# ─── Task 2: 补全画面 (Gemini) ───────────────────────────
@app.post("/api/task2", response_model=TaskResponse)
async def task2_expand_image(req: TaskRequest):
    """
    步骤2：补全画面（全画幅扩展 + 清理冗余元素）
    使用 gemini-3-pro-image-preview 模型
    输出分辨率：2K（最大边 2048）
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY 未配置")

    mime_type, pure_b64 = parse_base64_image(req.image_base64)
    task_id = f"task2_{uuid.uuid4().hex[:12]}"

    # Gemini API 调用（经过中转站）
    url = f"{GEMINI_BASE_URL}/v1beta/models/{GEMINI_MODEL}:generateContent"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": pure_b64}},
                    {"text": "全画幅展示图像，去除多余元素。"},
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                # "aspectRatio": "1:1",
                "imageSize": "2K",
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GEMINI_API_KEY}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # ── 打印完整响应用于排查 ──
        logger.info("=" * 60)
        logger.info("Gemini API 完整响应:")
        logger.info(json.dumps(data, ensure_ascii=False, default=str)[:5000])
        logger.info("=" * 60)

        # 解析 Gemini 响应
        candidates = data.get("candidates", [])
        if not candidates:
            raise HTTPException(status_code=502, detail="Gemini 模型未返回结果")

        parts = candidates[0].get("content", {}).get("parts", [])
        result_image = None

        for part in parts:
            if "inlineData" in part:
                inline = part["inlineData"]
                img_mime = inline.get("mimeType", "image/png")
                img_data = inline.get("data", "")
                if img_data:
                    result_image = f"data:{img_mime};base64,{img_data}"
                    break

        # 如果没有 inlineData，尝试从文本中提取
        if not result_image:
            for part in parts:
                if "text" in part:
                    result_image = extract_base64_from_response(part["text"])
                    if result_image:
                        break

        if not result_image:
            raise HTTPException(
                status_code=502, detail="无法从 Gemini 响应中提取图像结果"
            )

        return TaskResponse(
            task_id=task_id, result_image_base64=result_image, message="画面补全完成"
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API 调用失败: {e.response.status_code} - {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Gemini API 请求错误: {str(e)}")


# ─── Health Check ────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "grok_configured": bool(GROK_API_KEY),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8666)
