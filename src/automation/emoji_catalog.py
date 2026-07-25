"""从抖音直播间表情面板抓取表情列表。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from playwright.sync_api import Page, sync_playwright

from src.automation.douyin_live import (
    DouyinLiveAutomation,
    ENSURE_INPUT_VISIBLE_SCRIPT,
    PROJECT_ROOT,
    TaskRuntime,
)
from src.automation.emoji_panel import EMOJI_PANEL_LIST_SCRIPT
from src.automation.live_room_entry import enter_live_room
from src.config_loader import AppConfig


class EmojiCatalogItem(BaseModel):
    """表情目录项。"""

    index: int = Field(description="表情序号，从 1 开始")
    imageUrl: str = Field(description="表情图片地址")


class EmojiCatalogResponse(BaseModel):
    """表情目录响应。"""

    items: list[EmojiCatalogItem] = Field(default_factory=list, description="表情列表")
    total: int = Field(default=0, description="表情总数")


class EmojiCatalogFetcher:
    """抖音直播间表情目录抓取器。"""

    def __init__(self) -> None:
        self._automation = DouyinLiveAutomation(TaskRuntime())

    def fetch(self, config: AppConfig) -> EmojiCatalogResponse:
        """
        打开直播间并抓取表情面板列表。

        @param config: 运行配置（需包含 liveRoomUrl）
        @returns: 表情目录
        """
        if not config.has_entry_target():
            raise ValueError("请填写抖音号，或填写直播间号/URL")

        user_data_dir = PROJECT_ROOT / ".playwright-user-data"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            try:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    viewport={"width": 1440, "height": 900},
                    locale="zh-CN",
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except Exception as exc:
                message = str(exc)
                if "Executable doesn't exist" in message:
                    raise RuntimeError(
                        "Playwright 浏览器未安装或浏览器路径无效。"
                        "请执行: .\\.venv\\Scripts\\python.exe -m playwright install chromium",
                    ) from exc
                raise

            page = context.pages[0] if context.pages else context.new_page()
            try:
                items = self._collect_from_page(page, config)
            finally:
                context.close()

        return EmojiCatalogResponse(items=items, total=len(items))

    def _collect_from_page(
        self,
        page: Page,
        config: AppConfig,
    ) -> list[EmojiCatalogItem]:
        """
        在页面上打开表情面板并收集表情。

        @param page: 页面对象
        @param config: 运行配置
        @returns: 表情列表
        """
        logs: list[str] = []

        def _log(message: str) -> None:
            logs.append(message)

        page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2000)
        if config.waitLoginSeconds > 0:
            page.wait_for_timeout(config.waitLoginSeconds * 1000)

        enter_live_room(page, config, _log)
        page.wait_for_timeout(2000)

        page.evaluate(ENSURE_INPUT_VISIBLE_SCRIPT)
        page.wait_for_timeout(500)

        if not self._automation._open_emoji_panel(page):
            raise RuntimeError("未能打开表情面板，请确认已进入直播间且评论区可用")

        page.wait_for_timeout(1200)
        self._wait_for_visible_emoji_images(page)

        raw_items: list[dict[str, object]] = page.evaluate(EMOJI_PANEL_LIST_SCRIPT)
        if not raw_items:
            raise RuntimeError("表情面板已打开，但未读取到表情图片")

        items: list[EmojiCatalogItem] = []
        for raw in raw_items:
            index = int(raw.get("index", 0))
            image_url = str(raw.get("imageUrl", "")).strip()
            if index < 1 or not image_url:
                continue
            items.append(EmojiCatalogItem(index=index, imageUrl=image_url))
        return items

    def _wait_for_visible_emoji_images(self, page: Page) -> None:
        """
        等待表情图片加载完成。

        @param page: 页面对象
        """
        try:
            page.wait_for_function(
                """
                () => {
                  const panel = document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
                    || document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
                    || document.querySelector('[class*="emoji-panel-list"]');
                  if (!panel) return false;
                  const img = panel.querySelector(
                    '[class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"], img'
                  );
                  if (!(img instanceof HTMLImageElement)) return false;
                  const rect = img.getBoundingClientRect();
                  return rect.width >= 8 && !!(img.currentSrc || img.src);
                }
                """,
                timeout=10000,
            )
        except Exception:
            page.wait_for_timeout(800)
