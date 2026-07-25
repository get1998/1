"""抖音直播间浏览器自动评论脚本。"""

from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Frame, Locator, Page, Playwright, sync_playwright

from src.automation.emoji_panel import (
    EMOJI_CLICK_BY_INDEX_SCRIPT,
    EMOJI_CLICK_BY_OBJECT_KEY_SCRIPT,
    EMOJI_PANEL_COUNT_SCRIPT,
    emoji_object_key_from_url,
)
from src.automation.live_room_entry import enter_live_room
from src.config_loader import AppConfig, CommentPart, PROJECT_ROOT, extract_live_room_id, load_config
from src.report.excel_logger import CommentExcelLogger
# 评论输入框候选选择器
COMMENT_INPUT_SELECTORS: list[str] = [
    '#chatInput textarea',
    '#chatInput [contenteditable="true"]',
    '[class*="webcast-chatroom___input-container"] textarea',
    '[class*="webcast-chatroom___input-container"] [contenteditable="true"]',
    '[class*="webcast-chatroom"] textarea',
    '[class*="webcast-chatroom"] div[contenteditable="true"]',
    '[class*="Chatroom"] textarea',
    '[class*="Chatroom"] div[contenteditable="true"]',
    'textarea[placeholder*="说点什么"]',
    'textarea[placeholder*="聊"]',
    'textarea[placeholder*="评论"]',
    'div[contenteditable="true"][data-slate-editor="true"]',
    'div[contenteditable="true"]',
    'input[placeholder*="说点什么"]',
]

# 抖音官方表情按钮（webcast-chatroom___emoji-icon）
DOUYIN_EMOJI_ICON_SELECTORS: list[str] = [
    '#chatInput [class*="webcast-chatroom___emoji-icon"]',
    '[class*="webcast-chatroom___input-container"] [class*="webcast-chatroom___emoji-icon"]',
    '[class*="webcast-chatroom___emoji-icon"]',
]

# 表情按钮候选选择器（优先抖音官方 emoji-icon）
EMOJI_PANEL_BUTTON_SELECTORS: list[str] = [
    *DOUYIN_EMOJI_ICON_SELECTORS,
    '[class*="webcast-chatroom___input-container"] svg',
    '[class*="webcast-chatroom___input"] svg',
    'button[aria-label*="表情"]',
    '[data-e2e*="emoji"]',
    '[class*="emoji-btn"]',
]

# 表情项候选选择器（抖音官方 emoji-panel / emoji-item，含新版 emoji-panel__*）
DOUYIN_EMOJI_ITEM_SELECTORS: list[str] = [
    '[class*="webcast-chatroom___emoji-panel"] [class*="webcast-chatroom___emoji-item"]',
    '[class*="webcast-chatroom___emoji-panel"] [class*="emoji-item"]',
    '[class*="webcast-chatroom___emoji-list"] [class*="webcast-chatroom___emoji-item"]',
    '[class*="webcast-chatroom___emoji-list"] [class*="emoji-item"]',
    '[class*="webcast-chatroom___emoji-panel"] img',
    '[class*="webcast-chatroom___emoji-list"] img',
    '[class*="emoji-panel-wrapper"] [class*="emoji-panel__common-img"]',
    '[class*="emoji-panel-wrapper"] [class*="emoji-panel__all-img"]',
    '[class*="emoji-panel-list"] [class*="emoji-panel__common-img"]',
    '[class*="emoji-panel-list"] [class*="emoji-panel__all-img"]',
]

EMOJI_ITEM_SELECTORS: list[str] = [
    *DOUYIN_EMOJI_ITEM_SELECTORS,
    '[class*="emoji-panel"] [class*="item"]',
    '[class*="emoji-panel"] img',
    '[class*="expression-panel"] img',
    '[class*="sticker-panel"] img',
    '[class*="emoji-list"] img',
]

# 发送按钮候选选择器
SEND_BUTTON_SELECTORS: list[str] = [
    '[class*="webcast-chatroom"] button:has-text("发送")',
    '[class*="webcast-chatroom"] [class*="send"]',
    'button:has-text("发送")',
    'div[role="button"]:has-text("发送")',
    '[class*="send-btn"]',
    '[class*="SendButton"]',
]

# 备用：按序号发送的 Unicode 表情（点击失败时使用）
FALLBACK_UNICODE_EMOJIS: list[str] = ["😀", "😁", "😂", "🤣", "😊", "😍", "👍", "🎉", "🔥", "❤️"]

# 面板内表情数量（与 emoji_panel 模块统一）
EMOJI_AVAILABLE_COUNT_SCRIPT = EMOJI_PANEL_COUNT_SCRIPT

# 获取输入栏左侧可点击的图标按钮坐标
EMOJI_TOOLBAR_CANDIDATES_SCRIPT = """
() => {
  const room = document.querySelector('[class*="webcast-chatroom"]')
    || document.querySelector('[class*="Chatroom"]');
  const input = room?.querySelector('textarea, [contenteditable="true"]');
  if (!input) return [];

  const inputRect = input.getBoundingClientRect();
  const isInList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"]'
  );
  const isSend = (el) => {
    const text = (el.textContent || '').replace(/\\s/g, '');
    const cls = (el.className || '').toString().toLowerCase();
    return text.includes('发送') || cls.includes('send');
  };

  let container = input.parentElement;
  for (let i = 0; i < 8 && container; i++) {
    const rect = container.getBoundingClientRect();
    if (rect.height >= 28 && rect.height <= 160 && rect.width > inputRect.width * 0.45) break;
    container = container.parentElement;
  }

  const root = container || input.parentElement;
  if (!root) return [];

  const seen = new Set();
  const out = [];
  for (const node of root.querySelectorAll('button, [role="button"], svg, span, div')) {
    const el = node.closest('button, [role="button"]') || node;
    if (!(el instanceof HTMLElement) || seen.has(el) || isInList(el)) continue;
    if (input.contains(el) || el === input) continue;
    if (isSend(el)) continue;
    if (el.offsetParent === null) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 10 || r.height < 10 || r.width > 90) continue;
    if (r.bottom < inputRect.top - 10 || r.top > inputRect.bottom + 10) continue;
    if (r.left > inputRect.right + 40) continue;
    seen.add(el);
    out.push({ x: r.left + r.width / 2, y: r.top + r.height / 2, left: r.left });
  }

  out.sort((a, b) => a.left - b.left);
  return out.slice(0, 8);
}
"""

EMOJI_DEBUG_SCRIPT = """
() => {
  const room = document.querySelector('[class*="webcast-chatroom"]');
  const input = room?.querySelector('textarea, [contenteditable="true"]');
  const inputRect = input?.getBoundingClientRect();
  const emojiIcon = document.querySelector('[class*="webcast-chatroom___emoji-icon"]');
  const emojiPanel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]');
  const panelItems = emojiPanel
    ? emojiPanel.querySelectorAll('[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], img').length
    : 0;
  const candidates = [];
  if (input) {
    let container = input.parentElement;
    for (let i = 0; i < 8 && container; i++) {
      const rect = container.getBoundingClientRect();
      if (rect.height >= 28 && rect.height <= 160) break;
      container = container.parentElement;
    }
    const root = container || input.parentElement;
    if (root) {
      for (const node of root.querySelectorAll('button, [role="button"], svg')) {
        const el = node.closest('button, [role="button"]') || node;
        if (!(el instanceof HTMLElement) || el.offsetParent === null) continue;
        const r = el.getBoundingClientRect();
        candidates.push({
          tag: el.tagName,
          cls: (el.className || '').toString().slice(0, 60),
          text: (el.textContent || '').trim().slice(0, 10),
        });
      }
    }
  }
  return {
    hasRoom: !!room,
    hasInput: !!input,
    hasEmojiIcon: !!emojiIcon,
    hasEmojiPanel: !!emojiPanel,
    panelItemCount: panelItems,
    inputPlaceholder: input?.getAttribute('placeholder') || '',
    inputRect: inputRect ? { top: inputRect.top, left: inputRect.left } : null,
    toolbarCandidates: candidates.slice(0, 8),
  };
}
"""

DOUYIN_EMOJI_ICON_CLICK_SCRIPT = """
() => {
  const btn = document.querySelector('#chatInput [class*="webcast-chatroom___emoji-icon"]')
    || document.querySelector('[class*="webcast-chatroom___input-container"] [class*="webcast-chatroom___emoji-icon"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-icon"]');
  if (!(btn instanceof HTMLElement) || btn.offsetParent === null) return false;
  btn.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  btn.click();
  return true;
}
"""

ENSURE_INPUT_VISIBLE_SCRIPT = """
() => {
  const room = document.querySelector('[class*="webcast-chatroom"]')
    || document.querySelector('[class*="Chatroom"]');
  const input = room?.querySelector('textarea, [contenteditable="true"]');
  if (!(input instanceof HTMLElement)) return false;
  input.scrollIntoView({ block: 'end', behavior: 'instant' });
  input.focus();
  return true;
}
"""


@dataclass
class TaskRuntime:
    """任务运行时状态。"""

    running: bool = False
    ready: bool = False
    sending: bool = False
    recording: bool = False
    sent_count: int = 0
    last_screenshot: str = ""
    last_video: str = ""
    last_error: str = ""
    excel_report_path: str = ""
    end_time_text: str = ""
    logs: list[str] = field(default_factory=list)


class DouyinLiveAutomation:
    """抖音直播间自动评论控制器。"""

    def __init__(self, runtime: TaskRuntime) -> None:
        self.runtime = runtime
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._send_event = threading.Event()
        self._auto_send = False
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._excel_logger: CommentExcelLogger | None = None
        self._stop_reason: str = "任务结束"
        self._video_save_dir: Path | None = None
        self._browser_lock = threading.Lock()
        self._resolved_live_room_url: str = ""
        self._last_comment_preview: str = ""

    def start(self, config: AppConfig, *, auto_send: bool = False) -> None:
        """
        启动任务：打开直播间并等待手动「开始发送」（除非 auto_send）。

        @param config: 运行配置
        @param auto_send: 为 True 时进入直播间后立即发评（CLI 模式）
        """
        if self.runtime.running:
            raise RuntimeError("任务已在运行中")

        if not config.has_entry_target():
            raise ValueError("请填写抖音号，或填写直播间号/URL")
        if config.endTimeEnabled:
            end_at = config.resolve_end_time()
            if end_at is None:
                raise ValueError("已启用结束时间，请设置结束时间")
            if end_at <= datetime.now():
                raise ValueError("结束时间必须晚于当前时间")
            self.runtime.end_time_text = end_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.runtime.end_time_text = ""

        self._stop_event.clear()
        self._send_event.clear()
        self._auto_send = auto_send
        self._stop_reason = "任务结束"
        self._excel_logger = None
        self.runtime.running = True
        self.runtime.ready = False
        self.runtime.sending = False
        self.runtime.recording = False
        self.runtime.sent_count = 0
        self.runtime.last_error = ""
        self.runtime.last_screenshot = ""
        self.runtime.last_video = ""
        self.runtime.excel_report_path = ""
        self._video_save_dir = None
        self._resolved_live_room_url = ""
        self._last_comment_preview = ""
        preview = config.comment_preview()
        if preview:
            self._append_log(f"当前评论内容：{preview}")
        self._append_log("每次发送前将重新读取配置文件中的参数")
        if config.videoRecordEnabled:
            self._append_log("页面录屏：开始发送时自动录制，停止发送后保存")
        else:
            self._append_log("页面录屏：未开启")
        if config.excelReportEnabled:
            self._append_log("Excel 评论统计：已开启")
        else:
            self._append_log("Excel 评论统计：已关闭")
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(config,),
            daemon=True,
        )
        self._thread.start()

    def _load_live_config(self) -> AppConfig:
        """
        从配置文件加载最新运行参数。

        @returns: 当前配置
        """
        return load_config()

    def _sync_excel_logger(self, config: AppConfig) -> None:
        """
        按最新配置创建或复用 Excel 记录器。

        @param config: 当前配置
        """
        if not config.excelReportEnabled:
            return
        report_dir = config.resolve_excel_report_dir()
        live_url = config.resolve_live_room_url() or self._resolved_live_room_url
        if self._excel_logger is not None:
            if self._excel_logger.file_path.parent.resolve() == report_dir.resolve():
                self._excel_logger.live_room_url = live_url
                return
        try:
            self._excel_logger = CommentExcelLogger(report_dir, live_url)
            self.runtime.excel_report_path = str(self._excel_logger.file_path)
            self._append_log(f"Excel 统计文件: {self._excel_logger.file_path.name}")
        except Exception as exc:
            self._append_log(f"创建 Excel 统计失败: {exc}")
            self._excel_logger = None

    def begin_send(self) -> None:
        """
        开始发送评论（同时按配置自动开始录屏）。

        须在任务已进入直播间（ready）且尚未发送时调用。
        """
        if not self.runtime.running:
            raise RuntimeError("请先启动任务并进入直播间")
        if not self.runtime.ready:
            raise RuntimeError("直播间尚未就绪，请稍候再点击「开始发送」")
        if self.runtime.sending or self._send_event.is_set():
            raise RuntimeError("已在发送中")
        config = self._load_live_config()
        if not config.has_comment_content():
            raise RuntimeError("请在评论输入框中输入文字或插入表情，并保存配置")
        self._send_event.set()
        if config.videoRecordEnabled:
            self._append_log("已收到开始发送指令，将同步开始录屏")
        else:
            self._append_log("已收到开始发送指令")

    def stop(self) -> None:
        """停止自动评论任务。"""
        self._stop_reason = "手动停止"
        self._stop_event.set()
        self._send_event.set()
        self.runtime.running = False
        self.runtime.ready = False
        self.runtime.sending = False
        self.runtime.recording = False
        self._append_log("正在停止任务...")
        self._cleanup_browser()

    def _append_log(self, message: str) -> None:
        """追加运行日志。"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.runtime.logs.append(line)
        if len(self.runtime.logs) > 200:
            self.runtime.logs = self.runtime.logs[-200:]

    def _finalize_recorded_video(self, page: Page | None, video_dir: Path | None) -> None:
        """
        浏览器关闭后整理录屏文件到可读文件名。

        @param page: 已关闭的页面（仍可取 video.path）
        @param video_dir: 录屏目标目录
        """
        if page is None or video_dir is None:
            return
        try:
            video = page.video
            if video is None:
                return
            raw_path = Path(video.path())
            if not raw_path.exists():
                self._append_log("录屏文件尚未生成或已被移除")
                return
            video_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            target = video_dir / f"session_{stamp}.webm"
            index = 1
            while target.exists():
                target = video_dir / f"session_{stamp}_{index}.webm"
                index += 1
            shutil.move(str(raw_path), str(target))
            self.runtime.last_video = str(target)
            self._append_log(f"录屏已保存: {target}")
        except Exception as exc:
            self._append_log(f"保存录屏失败: {exc}")

    def _start_video_recording_if_enabled(self, config: AppConfig) -> None:
        """
        开始发送时按配置开启页面录屏。

        Playwright 录屏需在创建 Context 时指定，因此在发评前切换为带录屏的 Context。

        @param config: 当前配置
        """
        if not config.videoRecordEnabled:
            return
        if self._video_save_dir is not None:
            return
        if self._page is None or self._context is None:
            return

        live_url = self._resolved_live_room_url or self._page.url
        if not live_url or "douyin.com" not in live_url:
            self._append_log("页面录屏：无法获取直播间地址，跳过录制")
            return

        video_dir = config.resolve_video_dir()
        video_dir.mkdir(parents=True, exist_ok=True)

        with self._browser_lock:
            if self._stop_event.is_set() or self._page is None or self._context is None:
                return
            try:
                storage_state = self._context.storage_state()
                old_context = self._context
                self._page = None
                self._context = None
                try:
                    old_context.close()
                except Exception:
                    pass

                if self._playwright is None:
                    self._playwright = sync_playwright().start()

                self._browser = self._playwright.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                self._context = self._browser.new_context(
                    storage_state=storage_state,
                    viewport={"width": 1440, "height": 900},
                    locale="zh-CN",
                    record_video_dir=str(video_dir),
                    record_video_size={"width": 1440, "height": 900},
                )
                self._page = self._context.new_page()
                self._video_save_dir = video_dir
                self._page.goto(live_url, wait_until="domcontentloaded", timeout=90000)
                self._page.wait_for_timeout(2000)
                self._dismiss_overlays(self._page)
                self._wait_for_comment_area(self._page)
                self.runtime.recording = True
                self._append_log(f"页面录屏已开始，保存目录 {video_dir}")
            except Exception as exc:
                self._video_save_dir = None
                self.runtime.recording = False
                self._append_log(f"开启页面录屏失败: {exc}")

    def _reopen_live_room(self, live_url: str) -> None:
        """
        录屏结束后恢复普通浏览器会话（无录屏）。

        @param live_url: 直播间地址
        """
        user_data_dir = PROJECT_ROOT / ".playwright-user-data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        self._browser = None
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto(live_url, wait_until="domcontentloaded", timeout=90000)
        self._page.wait_for_timeout(2000)
        self._dismiss_overlays(self._page)
        self._wait_for_comment_area(self._page)
        self._append_log("已恢复直播间页面（录屏已结束）")

    def _stop_video_recording_session(self) -> None:
        """停止发送时结束录屏并保存文件；任务未停止则恢复普通浏览器。"""
        if self._video_save_dir is None:
            return
        live_url = self._resolved_live_room_url
        keep_task = not self._stop_event.is_set() and self.runtime.running
        with self._browser_lock:
            page = self._page
            context = self._context
            browser = self._browser
            video_dir = self._video_save_dir
            self._page = None
            self._context = None
            self._browser = None
            self._video_save_dir = None
            self.runtime.recording = False

            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            self._finalize_recorded_video(page, video_dir)
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass

        if keep_task and live_url:
            try:
                self._reopen_live_room(live_url)
            except Exception as exc:
                self._append_log(f"恢复直播间失败: {exc}")

    def _cleanup_browser(self) -> None:
        """释放浏览器资源，并在开启录屏时落盘视频。"""
        with self._browser_lock:
            page = self._page
            context = self._context
            browser = self._browser
            playwright = self._playwright
            video_dir = self._video_save_dir
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._video_save_dir = None

            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            self._finalize_recorded_video(page, video_dir)
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    pass
            self.runtime.recording = False

    def _wait_interval_or_stop(self, interval_seconds: int, end_at: datetime | None) -> bool:
        """
        等待发送间隔，或在停止/到达结束时间时返回 True。

        @param interval_seconds: 发送间隔秒数
        @param end_at: 任务结束时间
        @returns: 是否应退出循环
        """
        if end_at is not None and datetime.now() >= end_at:
            return True
        wait_seconds = float(interval_seconds)
        if end_at is not None:
            remaining = (end_at - datetime.now()).total_seconds()
            if remaining <= 0:
                return True
            wait_seconds = min(wait_seconds, remaining)
        return self._stop_event.wait(wait_seconds)

    def _finalize_excel_report(self, total_sent: int) -> None:
        """
        写入 Excel 汇总并保存文件。

        @param total_sent: 总发送次数
        """
        if self._excel_logger is None:
            return
        try:
            self._excel_logger.append_summary(total_sent, self._stop_reason)
            self.runtime.excel_report_path = self._excel_logger.close()
            self._append_log(f"Excel 统计已保存: {self.runtime.excel_report_path}")
        except Exception as exc:
            self._append_log(f"保存 Excel 统计失败: {exc}")
        finally:
            self._excel_logger = None

    def _prepare_comment_area(self, page: Page) -> None:
        """
        发评前整理评论区：关闭浮层、确保输入框可见可点（不滚动弹幕，避免输入栏错位）。

        @param page: 页面对象
        """
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            page.evaluate(ENSURE_INPUT_VISIBLE_SCRIPT)
            page.wait_for_timeout(200)
        except Exception:
            pass

    def _get_available_emoji_count(self, page: Page) -> int:
        """
        统计输入栏附近 / 弹层内可用表情数量。

        @param page: 页面对象
        @returns: 可用表情数量
        """
        try:
            return int(page.evaluate(EMOJI_AVAILABLE_COUNT_SCRIPT))
        except Exception:
            return 0

    def _click_left_of_input(self, page: Page, offset_px: int) -> bool:
        """
        在输入框左侧指定偏移处点击（表情按钮常见位置）。

        @param page: 页面对象
        @param offset_px: 相对输入框左边缘向左偏移像素
        @returns: 是否执行点击
        """
        script = """
        (offset) => {
          const input = document.querySelector('[class*="webcast-chatroom"] textarea, [class*="webcast-chatroom"] [contenteditable="true"]');
          if (!input) return null;
          const r = input.getBoundingClientRect();
          return { x: r.left - offset, y: r.top + r.height / 2 };
        }
        """
        try:
            pos = page.evaluate(script, offset_px)
            if not pos:
                return False
            page.mouse.click(float(pos["x"]), float(pos["y"]))
            return True
        except Exception:
            return False

    def _click_scoped_emoji_at_index(self, page: Page, emoji_index: int) -> bool:
        """
        点击输入栏/面板内第 N 个表情。

        @param page: 页面对象
        @param emoji_index: 表情序号（从 1 开始）
        @returns: 是否点击成功
        """
        try:
            return bool(page.evaluate(EMOJI_CLICK_BY_INDEX_SCRIPT, emoji_index))
        except Exception:
            return False

    def _log_emoji_toolbar_debug(self, page: Page) -> None:
        """
        记录输入栏调试信息，便于排查表情按钮定位失败。

        @param page: 页面对象
        """
        try:
            info = page.evaluate(EMOJI_DEBUG_SCRIPT)
            self._append_log(
                f"表情调试: 输入框={info.get('hasInput')}, "
                f"emoji-icon={info.get('hasEmojiIcon')}, "
                f"emoji-panel={info.get('hasEmojiPanel')}, "
                f"面板项={info.get('panelItemCount', 0)}",
            )
        except Exception as exc:
            self._append_log(f"表情调试信息获取失败: {exc}")

    def _type_into_comment_input(self, page: Page, input_box: Locator, text: str) -> None:
        """
        向评论输入框写入文本（兼容 textarea 与 contenteditable）。

        @param page: 页面对象
        @param input_box: 输入框 locator
        @param text: 待输入文本
        """
        input_box.click(timeout=3000)
        page.wait_for_timeout(200)
        try:
            tag_name = input_box.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            tag_name = "textarea"
        if tag_name == "textarea":
            input_box.fill(text)
        else:
            page.keyboard.press("Control+A")
            page.keyboard.insert_text(text)

    def _get_douyin_panel_emoji_count(self, page: Page) -> int:
        """
        获取抖音官方 emoji-panel 内表情数量。

        @param page: 页面对象
        @returns: 面板内表情数量
        """
        try:
            return int(page.evaluate(EMOJI_PANEL_COUNT_SCRIPT))
        except Exception:
            return 0

    def _click_douyin_emoji_at_index(self, page: Page, emoji_index: int) -> bool:
        """
        点击抖音 emoji-panel 内第 N 个表情（按视觉位置排序）。

        @param page: 页面对象
        @param emoji_index: 表情序号（从 1 开始）
        @returns: 是否点击成功
        """
        for root in self._get_search_roots(page):
            for selector in DOUYIN_EMOJI_ITEM_SELECTORS:
                locator = root.locator(selector)
                count = self._safe_count(locator)
                if count < emoji_index:
                    continue
                target = locator.nth(emoji_index - 1)
                try:
                    if target.is_visible(timeout=1000):
                        target.scroll_into_view_if_needed(timeout=2000)
                        target.click(timeout=3000, force=True)
                        return True
                except Exception:
                    continue
        return False

    def _ensure_browser(self, config: AppConfig) -> Page:
        """
        初始化浏览器并打开直播间。

        @param config: 运行配置
        @returns: 当前页面对象
        """
        if self._page is not None:
            return self._page

        user_data_dir = PROJECT_ROOT / ".playwright-user-data"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        launch_kwargs: dict[str, object] = {
            "user_data_dir": str(user_data_dir),
            "headless": False,
            "viewport": {"width": 1440, "height": 900},
            "locale": "zh-CN",
            "args": ["--disable-blink-features=AutomationControlled"],
        }

        self._playwright = sync_playwright().start()
        try:
            self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message:
                raise RuntimeError(
                    "Playwright 浏览器未安装或浏览器路径无效。"
                    "请在项目目录激活 .venv 后执行："
                    ".\\.venv\\Scripts\\python.exe -m playwright install chromium，"
                    "然后重启后端再试。"
                    "若已安装仍报错，请确认未设置错误的 PLAYWRIGHT_BROWSERS_PATH 环境变量。",
                ) from exc
            raise

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

        if config.resolve_live_room_url():
            self._append_log(f"将直接打开直播间: {config.resolve_live_room_url()}")
        else:
            self._append_log(f"未配置直播间 URL，将按抖音号「{config.douyinId}」搜索进房")

        # 先打开抖音首页，便于登录与搜索
        self._page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=90000)
        self._page.wait_for_timeout(2000)
        self._dismiss_overlays(self._page)

        if config.waitLoginSeconds > 0:
            self._append_log(f"请在浏览器中登录抖音，等待 {config.waitLoginSeconds} 秒...")
            if self._stop_event.wait(config.waitLoginSeconds):
                raise RuntimeError("任务已取消")

        final_url = enter_live_room(
            self._page,
            config,
            self._append_log,
            self._stop_event,
        )
        self._dismiss_overlays(self._page)

        # 搜索进房后回填直播间号，便于截图目录与下次直达
        rid = extract_live_room_id(final_url)
        if rid:
            config.webRid = rid
            config.liveRoomUrl = f"https://live.douyin.com/{rid}"
            self._append_log(f"已解析直播间号: {rid}")

        self._wait_for_comment_area(self._page)
        self._resolved_live_room_url = final_url
        self._append_log(f"已进入直播间，评论区就绪: {final_url}")
        return self._page

    def _run_send_loop(self) -> None:
        """发送评论循环：开始时录屏，结束时保存录屏（不再按秒截图）。"""
        send_config = self._load_live_config()
        if send_config.videoRecordEnabled:
            self._start_video_recording_if_enabled(send_config)
        try:
            while not self._stop_event.is_set():
                page = self._page
                if page is None:
                    raise RuntimeError("页面不可用，无法继续发送")

                config = self._load_live_config()
                end_at = config.resolve_end_time() if config.endTimeEnabled else None
                if config.endTimeEnabled and end_at is not None:
                    self.runtime.end_time_text = end_at.strftime("%Y-%m-%d %H:%M:%S")
                elif not config.endTimeEnabled:
                    self.runtime.end_time_text = ""

                if end_at is not None and datetime.now() >= end_at:
                    self._stop_reason = "到达结束时间自动停止"
                    self._append_log(
                        f"已到达结束时间 {end_at.strftime('%Y-%m-%d %H:%M:%S')}，任务自动停止",
                    )
                    break

                if not config.has_comment_content():
                    self._append_log("当前配置评论内容为空，跳过本次发送")
                    if self._wait_interval_or_stop(config.intervalSeconds, end_at):
                        if end_at is not None and datetime.now() >= end_at:
                            self._stop_reason = "到达结束时间自动停止"
                            self._append_log(
                                f"已到达结束时间 {end_at.strftime('%Y-%m-%d %H:%M:%S')}，任务自动停止",
                            )
                        break
                    continue

                comment_parts = config.resolved_comment_parts()
                comment_preview = config.comment_preview()
                if comment_preview != self._last_comment_preview:
                    self._append_log(f"评论内容已更新：{comment_preview}")
                    self._last_comment_preview = comment_preview

                self._sync_excel_logger(config)

                sent_text = comment_preview
                emoji_index = 0
                emoji_count = 0
                proof_path = ""
                record_status = "失败"
                record_remark = ""

                try:
                    sent_text, emoji_index, emoji_count = self._send_comment(
                        page,
                        comment_parts,
                    )
                    self.runtime.sent_count += 1
                    self.runtime.last_error = ""
                    record_status = "成功"
                    self._append_log(
                        f"已发送评论 ({self.runtime.sent_count}): {comment_preview}",
                    )
                    if self.runtime.recording and self.runtime.last_video:
                        proof_path = self.runtime.last_video
                    elif self.runtime.recording:
                        proof_path = "录屏进行中"
                except Exception as exc:
                    self.runtime.last_error = str(exc)
                    record_remark = str(exc)
                    self._append_log(f"发送失败: {exc}")

                if config.excelReportEnabled and self._excel_logger is not None:
                    try:
                        self._excel_logger.append_record(
                            sequence=(
                                self.runtime.sent_count
                                if record_status == "成功"
                                else self.runtime.sent_count + 1
                            ),
                            comment_text=comment_preview or sent_text,
                            emoji_index=emoji_index,
                            emoji_count=emoji_count,
                            screenshot_path=proof_path,
                            status=record_status,
                            remark=record_remark,
                        )
                    except Exception as exc:
                        self._append_log(f"写入 Excel 记录失败: {exc}")

                if self._wait_interval_or_stop(config.intervalSeconds, end_at):
                    if end_at is not None and datetime.now() >= end_at:
                        self._stop_reason = "到达结束时间自动停止"
                        self._append_log(
                            f"已到达结束时间 {end_at.strftime('%Y-%m-%d %H:%M:%S')}，任务自动停止",
                        )
                    break
        finally:
            if send_config.videoRecordEnabled or self._video_save_dir is not None:
                self._append_log("发送已停止，正在保存录屏…")
                self._stop_video_recording_session()

    def _run_loop(self, startup_config: AppConfig) -> None:
        """
        任务主循环：进房后等待「开始发送」。

        @param startup_config: 启动任务时的配置（仅用于打开直播间）
        """
        startup_end_at = startup_config.resolve_end_time()
        if startup_config.endTimeEnabled and startup_end_at is not None:
            self._append_log(f"任务将于 {startup_end_at.strftime('%Y-%m-%d %H:%M:%S')} 自动停止")

        try:
            self._ensure_browser(startup_config)
            self.runtime.ready = True
            self._append_log("直播间已就绪，请点击「开始发送」")

            if self._auto_send:
                auto_config = self._load_live_config()
                if auto_config.has_comment_content():
                    self._send_event.set()
                else:
                    self._append_log("评论内容为空，CLI 未自动开始发送")

            while not self._stop_event.is_set():
                if self._send_event.is_set() and not self.runtime.sending:
                    self.runtime.sending = True
                    self._append_log("开始执行自动评论")
                    try:
                        self._run_send_loop()
                    finally:
                        self.runtime.sending = False
                        self._send_event.clear()
                    continue

                if self._stop_event.wait(0.5):
                    break

        except Exception as exc:
            self.runtime.last_error = str(exc)
            self._append_log(f"任务异常: {exc}")
        finally:
            self.runtime.running = False
            self.runtime.ready = False
            self.runtime.sending = False
            self.runtime.recording = False
            self._finalize_excel_report(self.runtime.sent_count)
            self._cleanup_browser()
            self._append_log("任务已停止")

    def _safe_count(self, locator: Locator) -> int:
        """
        安全获取 locator 数量，避免 detached frame 报错。

        @param locator: 元素定位器
        @returns: 匹配数量
        """
        try:
            return locator.count()
        except Exception:
            return 0

    def _get_search_roots(self, page: Page) -> list[Page | Frame]:
        """
        获取可搜索的根节点（主页面 + 未 detached 的 iframe）。

        @param page: 页面对象
        @returns: 根节点列表
        """
        roots: list[Page | Frame] = [page]
        try:
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                try:
                    frame.evaluate("() => true")
                    roots.append(frame)
                except Exception:
                    continue
        except Exception:
            pass
        return roots

    def _find_first_visible(
        self,
        page: Page,
        selectors: list[str],
    ) -> Locator | None:
        """
        在页面及 iframe 中查找第一个可见元素。

        @param page: 页面对象
        @param selectors: CSS 选择器列表
        @returns: 第一个可见 locator
        """
        for root in self._get_search_roots(page):
            for selector in selectors:
                locator = root.locator(selector)
                if self._safe_count(locator) == 0:
                    continue
                candidate = locator.first
                try:
                    if candidate.is_visible(timeout=800):
                        return candidate
                except Exception:
                    continue
        return None

    def _wait_for_comment_area(self, page: Page, timeout_ms: int = 60000) -> None:
        """
        等待评论区加载完成。

        @param page: 页面对象
        @param timeout_ms: 超时毫秒
        """
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            if self._find_comment_input(page) is not None:
                self._append_log("评论区已就绪")
                return
            page.wait_for_timeout(1000)
        raise RuntimeError("未检测到评论区，请确认直播间 URL 正确且直播进行中")

    def _dismiss_overlays(self, page: Page) -> None:
        """尝试关闭常见弹窗。"""
        close_selectors = [
            'button:has-text("我知道了")',
            'button:has-text("知道了")',
            'button:has-text("关闭")',
            '[aria-label="关闭"]',
        ]
        for selector in close_selectors:
            locator = page.locator(selector)
            if self._safe_count(locator) == 0:
                continue
            try:
                locator.first.click(timeout=1000)
                page.wait_for_timeout(300)
            except Exception:
                continue

    def _find_comment_input(self, page: Page) -> Locator | None:
        """查找评论输入框。"""
        return self._find_first_visible(page, COMMENT_INPUT_SELECTORS)

    def _focus_comment_input(self, page: Page) -> Locator:
        """
        聚焦评论输入框。

        @param page: 页面对象
        @returns: 评论输入框 locator
        """
        input_box = self._find_comment_input(page)
        if input_box is None:
            raise RuntimeError("未找到评论输入框，请确认已进入直播间")

        input_box.scroll_into_view_if_needed(timeout=5000)
        input_box.click(timeout=5000)
        page.wait_for_timeout(500)
        return input_box

    def _click_send_button(self, page: Page) -> bool:
        """点击发送按钮。"""
        button = self._find_first_visible(page, SEND_BUTTON_SELECTORS)
        if button is None:
            return False
        try:
            button.click(timeout=2000)
            return True
        except Exception:
            return False

    def _click_douyin_emoji_icon(self, page: Page) -> bool:
        """
        点击抖音官方表情按钮 webcast-chatroom___emoji-icon。

        @param page: 页面对象
        @returns: 是否点击成功
        """
        for root in self._get_search_roots(page):
            for selector in DOUYIN_EMOJI_ICON_SELECTORS:
                locator = root.locator(selector)
                if self._safe_count(locator) == 0:
                    continue
                target = locator.first
                try:
                    if target.is_visible(timeout=1500):
                        target.scroll_into_view_if_needed(timeout=3000)
                        target.click(timeout=3000)
                        return True
                except Exception:
                    try:
                        svg = target.locator("svg").first
                        if svg.is_visible(timeout=1000):
                            svg.click(timeout=3000, force=True)
                            return True
                    except Exception:
                        continue

        try:
            return bool(page.evaluate(DOUYIN_EMOJI_ICON_CLICK_SCRIPT))
        except Exception:
            return False

    def _open_emoji_panel(self, page: Page) -> bool:
        """
        尝试打开表情面板：优先点击 webcast-chatroom___emoji-icon。

        @param page: 页面对象
        @returns: 是否成功打开或表情条已可见
        """
        before_count = self._get_available_emoji_count(page)
        if before_count >= 1 and self._get_douyin_panel_emoji_count(page) >= 1:
            return True

        if self._click_douyin_emoji_icon(page):
            page.wait_for_timeout(600)
            after_count = self._get_available_emoji_count(page)
            if after_count > before_count:
                self._append_log("表情面板已打开（webcast-chatroom___emoji-icon）")
                return True

        try:
            candidates: list[dict[str, float]] = page.evaluate(EMOJI_TOOLBAR_CANDIDATES_SCRIPT)
        except Exception:
            candidates = []

        for index, candidate in enumerate(candidates):
            try:
                page.mouse.click(float(candidate["x"]), float(candidate["y"]))
                page.wait_for_timeout(500)
                after_count = self._get_available_emoji_count(page)
                if after_count > before_count:
                    self._append_log(f"表情面板已打开（工具栏第 {index + 1} 个按钮）")
                    return True
            except Exception:
                continue

        for offset in (20, 36, 52, 68, 84):
            if self._click_left_of_input(page, offset):
                page.wait_for_timeout(500)
                after_count = self._get_available_emoji_count(page)
                if after_count > before_count:
                    self._append_log(f"表情面板已打开（输入框左侧 {offset}px）")
                    return True

        for root in self._get_search_roots(page):
            for selector in EMOJI_PANEL_BUTTON_SELECTORS:
                locator = root.locator(selector)
                if self._safe_count(locator) == 0:
                    continue
                for btn_index in range(min(self._safe_count(locator), 5)):
                    try:
                        target = locator.nth(btn_index)
                        if not target.is_visible(timeout=500):
                            continue
                        target.click(timeout=2000, force=True)
                        page.wait_for_timeout(500)
                        after_count = self._get_available_emoji_count(page)
                        if after_count > before_count:
                            self._append_log(f"表情面板已打开（选择器 {selector}）")
                            return True
                    except Exception:
                        continue

        after_count = self._get_available_emoji_count(page)
        if after_count > before_count:
            return True

        self._append_log(
            f"表情面板打开失败（打开前 {before_count} 个，打开后 {after_count} 个可用表情）",
        )
        self._log_emoji_toolbar_debug(page)
        return False

    def _count_visible_emoji_items(self, page: Page) -> int:
        """
        统计当前可见表情项数量（优先官方 emoji-panel）。

        @param page: 页面对象
        @returns: 可见表情数量
        """
        panel_count = self._get_douyin_panel_emoji_count(page)
        if panel_count > 0:
            return panel_count

        scoped = self._get_available_emoji_count(page)
        if scoped > 0:
            return scoped

        for root in self._get_search_roots(page):
            for selector in EMOJI_ITEM_SELECTORS:
                locator = root.locator(selector)
                count = self._safe_count(locator)
                if count == 0:
                    continue
                visible = 0
                for index in range(min(count, 100)):
                    try:
                        if locator.nth(index).is_visible(timeout=300):
                            visible += 1
                    except Exception:
                        continue
                if visible > 0:
                    return visible
        return 0

    def _find_emoji_items(self, page: Page) -> Locator | None:
        """查找表情项列表 locator（优先官方 emoji-panel 内 emoji-item）。"""
        for root in self._get_search_roots(page):
            for selector in DOUYIN_EMOJI_ITEM_SELECTORS:
                locator = root.locator(selector)
                if self._safe_count(locator) > 0:
                    return locator
        for root in self._get_search_roots(page):
            for selector in EMOJI_ITEM_SELECTORS:
                locator = root.locator(selector)
                if self._safe_count(locator) > 0:
                    return locator
        return None

    def _resolve_emoji_image_url(self, part: CommentPart) -> str:
        """
        解析表情图片 URL（配置内嵌或本地缓存目录）。

        @param part: 表情片段
        @returns: 图片 URL；无则返回空字符串
        """
        if part.imageUrl.strip():
            return part.imageUrl.strip()
        from src.automation.emoji_catalog_store import load_emoji_catalog

        catalog = load_emoji_catalog()
        if catalog is None:
            return ""
        for item in catalog.items:
            if item.index == part.index:
                return item.imageUrl
        return ""

    def _click_emoji_by_object_key(self, page: Page, image_url: str) -> bool:
        """
        按图片 object path 点击表情（与抓取目录同一套去重逻辑）。

        @param page: 页面对象
        @param image_url: 表情图片 URL 或 path
        @returns: 是否点击成功
        """
        key = emoji_object_key_from_url(image_url)
        if not key:
            return False
        try:
            return bool(page.evaluate(EMOJI_CLICK_BY_OBJECT_KEY_SCRIPT, key))
        except Exception:
            return False

    def _click_emoji_by_js(self, page: Page, emoji_index: int) -> bool:
        """
        通过 JS 点击 emoji-panel 内第 N 个表情。

        @param page: 页面对象
        @param emoji_index: 表情序号（从 1 开始）
        @returns: 是否点击成功
        """
        try:
            return bool(page.evaluate(EMOJI_CLICK_BY_INDEX_SCRIPT, emoji_index))
        except Exception:
            return False

    def _get_emoji_pack_total(self, page: Page) -> int:
        """
        获取当前表情面板中可用表情数量。

        @param page: 页面对象
        @returns: 表情数量，至少为 1
        """
        emoji_items = self._find_emoji_items(page)
        if emoji_items is not None:
            total = self._safe_count(emoji_items)
            if total > 0:
                return total
        visible = self._count_visible_emoji_items(page)
        if visible > 0:
            return visible
        return len(FALLBACK_UNICODE_EMOJIS)

    def _click_emoji_at_index(self, page: Page, emoji_index: int, image_url: str = "") -> bool:
        """
        点击表情包中指定表情：优先按图片 URL，再按统一视觉序号。

        @param page: 页面对象
        @param emoji_index: 表情序号
        @param image_url: 可选，表情图片 URL
        @returns: 是否点击成功
        """
        if image_url and self._click_emoji_by_object_key(page, image_url):
            page.wait_for_timeout(200)
            return True

        if self._click_emoji_by_js(page, emoji_index):
            page.wait_for_timeout(200)
            return True

        return False

    def _append_text_to_input(self, page: Page, text: str, *, clear_first: bool) -> None:
        """
        向评论输入框写入文字。

        @param page: 页面对象
        @param text: 文字内容
        @param clear_first: 是否先清空输入框
        """
        input_box = self._focus_comment_input(page)
        if clear_first:
            self._type_into_comment_input(page, input_box, text)
        else:
            input_box.click(timeout=3000)
            page.wait_for_timeout(120)
            page.keyboard.press("End")
            page.keyboard.insert_text(text)
        page.wait_for_timeout(150)

    def _append_unicode_emoji(self, page: Page, emoji_index: int) -> None:
        """
        备用方案：追加一个 Unicode 表情。

        @param page: 页面对象
        @param emoji_index: 表情序号（从 1 开始）
        """
        emoji_char = FALLBACK_UNICODE_EMOJIS[(emoji_index - 1) % len(FALLBACK_UNICODE_EMOJIS)]
        input_box = self._focus_comment_input(page)
        input_box.click(timeout=3000)
        page.wait_for_timeout(120)
        page.keyboard.press("End")
        page.keyboard.insert_text(emoji_char)
        page.wait_for_timeout(150)
        self._append_log(f"已使用备用 Unicode 表情: {emoji_char}")

    def _insert_single_emoji(self, page: Page, part: CommentPart) -> bool:
        """
        向输入框插入单个表情。

        @param page: 页面对象
        @param part: 表情片段
        @returns: 是否插入成功
        """
        emoji_index = max(1, part.index)
        image_url = self._resolve_emoji_image_url(part)
        for attempt in range(3):
            if self._open_emoji_panel(page) and self._click_emoji_at_index(
                page,
                emoji_index,
                image_url,
            ):
                page.wait_for_timeout(200)
                return True
            self._append_log(f"插入表情 {emoji_index} 失败，重试 ({attempt + 1}/3)")
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)
            except Exception:
                pass
        hint = "请重新「从直播间加载表情」后再试"
        if image_url:
            self._append_log(f"插入表情 {emoji_index} 失败（已按图片匹配），{hint}")
        else:
            self._append_log(f"插入表情 {emoji_index} 失败（无图片 URL），{hint}")
        return False

    def _send_comment(
        self,
        page: Page,
        parts: list[CommentPart],
    ) -> tuple[str, int, int]:
        """
        按片段顺序发送一条评论（文字与表情可自由穿插）。

        @param page: 页面对象
        @param parts: 评论片段列表
        @returns: (文字预览, 首个表情序号, 表情总数)
        """
        if not parts:
            raise RuntimeError("评论内容为空：请输入文字或插入表情")

        self._prepare_comment_area(page)
        self._focus_comment_input(page)

        text_chunks: list[str] = []
        emoji_indices: list[int] = []
        is_first = True

        for part in parts:
            if part.type == "text":
                text = part.text.strip()
                if not text:
                    continue
                self._append_text_to_input(page, text, clear_first=is_first)
                text_chunks.append(text)
                is_first = False
                continue

            if part.type == "emoji":
                if is_first:
                    # 首段为表情时先清空输入框，避免残留
                    input_box = self._focus_comment_input(page)
                    self._type_into_comment_input(page, input_box, "")
                    is_first = False
                self._insert_single_emoji(page, part)
                emoji_indices.append(part.index)

        page.wait_for_timeout(300)
        if not self._click_send_button(page):
            page.keyboard.press("Enter")
        page.wait_for_timeout(500)

        preview = "".join(text_chunks)
        first_emoji = emoji_indices[0] if emoji_indices else 0
        return preview, first_emoji, len(emoji_indices)
