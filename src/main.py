"""FastAPI 服务入口与任务 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.automation.douyin_live import DouyinLiveAutomation, TaskRuntime
from src.automation.emoji_catalog import EmojiCatalogFetcher, EmojiCatalogResponse
from src.automation.emoji_catalog_store import load_emoji_catalog, save_emoji_catalog
from src.config_loader import AppConfig, load_config, save_config

PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(title="抖音直播间自动评论", version="1.0.0")
runtime = TaskRuntime()
automation = DouyinLiveAutomation(runtime)
emoji_catalog_fetcher = EmojiCatalogFetcher()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskStatusResponse(BaseModel):
    """任务状态响应。"""

    running: bool
    ready: bool
    sending: bool
    sentCount: int
    lastScreenshot: str
    lastError: str
    excelReportPath: str
    endTimeText: str
    logs: list[str]


@app.get("/api/config", response_model=AppConfig)
def get_config() -> AppConfig:
    """获取当前配置。"""
    return load_config()


@app.post("/api/config", response_model=AppConfig)
def update_config(config: AppConfig) -> AppConfig:
    """保存配置。"""
    save_config(config)
    return config


class EmojiCatalogRequest(BaseModel):
    """抓取表情目录请求。"""

    liveRoomUrl: str
    waitLoginSeconds: int = 30


@app.get("/api/emoji/catalog", response_model=EmojiCatalogResponse)
def get_emoji_catalog() -> EmojiCatalogResponse:
    """获取已缓存的表情目录（抖音平台通用，抓取一次即可）。"""
    cached = load_emoji_catalog()
    if cached is not None:
        return cached
    return EmojiCatalogResponse(items=[], total=0)


@app.post("/api/emoji/catalog", response_model=EmojiCatalogResponse)
def fetch_emoji_catalog(body: EmojiCatalogRequest) -> EmojiCatalogResponse:
    """从直播间抓取表情目录并写入本地缓存。"""
    if runtime.running:
        raise HTTPException(status_code=409, detail="任务运行中，请先停止任务再加载表情")
    config = AppConfig(
        liveRoomUrl=body.liveRoomUrl,
        waitLoginSeconds=body.waitLoginSeconds,
    )
    try:
        catalog = emoji_catalog_fetcher.fetch(config)
        save_emoji_catalog(catalog)
        return catalog
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/task/start")
def start_task(config: AppConfig) -> dict[str, str]:
    """启动任务：打开直播间并等待「开始发送」（不立即发评）。"""
    save_config(config)
    try:
        automation.start(config, auto_send=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "任务已启动，进入直播间后请点击「开始发送」"}


@app.post("/api/task/begin-send")
def begin_send() -> dict[str, str]:
    """开始发送评论（须在直播间就绪后调用）。"""
    try:
        automation.begin_send()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "已开始发送"}


@app.post("/api/task/stop")
def stop_task() -> dict[str, str]:
    """停止自动评论任务。"""
    automation.stop()
    return {"message": "任务已停止"}


@app.get("/api/task/status", response_model=TaskStatusResponse)
def task_status() -> TaskStatusResponse:
    """获取任务运行状态。"""
    return TaskStatusResponse(
        running=runtime.running,
        ready=runtime.ready,
        sending=runtime.sending,
        sentCount=runtime.sent_count,
        lastScreenshot=runtime.last_screenshot,
        lastError=runtime.last_error,
        excelReportPath=runtime.excel_report_path,
        endTimeText=runtime.end_time_text,
        logs=runtime.logs,
    )


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/")
    def frontend_not_built() -> dict[str, str]:
        """前端未构建时的提示。"""
        return {
            "message": "前端未构建。开发模式请运行: cd frontend && npm run dev；"
            "生产模式请运行: cd frontend && npm run build",
        }


def main() -> None:
    """启动 Web 服务。"""
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    main()
