"""抖音直播间浏览器自动评论脚本。"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

from playwright.sync_api import BrowserContext, Frame, Locator, Page, Playwright, sync_playwright

from src.automation.live_room_entry import enter_live_room
from src.config_loader import AppConfig, CommentPart, PROJECT_ROOT, extract_live_room_id
from src.report.excel_logger import CommentExcelLogger
from src.screenshot.capture import capture_after_comment, get_chat_message_count

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

# 收集抖音表情面板内可点击项（按视觉位置从上到下、从左到右排序）
EMOJI_PANEL_COLLECT_SCRIPT = """
() => {
  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');

  const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
    || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
    || document.querySelector('[class*="emoji-panel-wrapper"]')
    || document.querySelector('[class*="emoji-panel-list"]')
    || document.querySelector('[class*="webcast-chatroom"] [class*="emoji-panel"]');

  const result = [];
  const seen = new Set();

  const push = (el) => {
    if (!(el instanceof HTMLElement) || seen.has(el) || isInChatList(el) || isEmojiIcon(el)) return;
    if (el.offsetParent === null) return;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 120 || r.height > 120) return;
    seen.add(el);
    result.push({ el, top: Math.round(r.top), left: Math.round(r.left) });
  };

  if (!panel) return [];

  const officialItems = panel.querySelectorAll(
    '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"]'
  );
  if (officialItems.length > 0) {
    for (const el of officialItems) push(el);
  }

  if (result.length === 0) {
    for (const img of panel.querySelectorAll('img')) {
      push(img.closest('[class*="item"]') || img.parentElement || img);
    }
  }

  result.sort((a, b) => (a.top === b.top ? a.left - b.left : a.top - b.top));
  return result.map((item) => ({
    top: item.top,
    left: item.left,
    cls: (item.el.className || '').toString().slice(0, 80),
  }));
}
"""

EMOJI_PANEL_COUNT_SCRIPT = """
() => {
  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');
  const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
    || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
    || document.querySelector('[class*="emoji-panel-wrapper"]')
    || document.querySelector('[class*="emoji-panel-list"]');
  if (!panel || panel.offsetParent === null) return 0;

  const items = panel.querySelectorAll(
    '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"], img'
  );
  let count = 0;
  const seen = new Set();
  for (const node of items) {
    const el = node.closest(
      '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"]'
    ) || node;
    if (!(el instanceof HTMLElement) || seen.has(el) || isInChatList(el) || isEmojiIcon(el)) continue;
    if (el.offsetParent === null) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) continue;
    seen.add(el);
    count += 1;
  }
  return count;
}
"""

EMOJI_CLICK_BY_INDEX_SCRIPT = """
(index) => {
  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');

  const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
    || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
    || document.querySelector('[class*="emoji-panel-wrapper"]')
    || document.querySelector('[class*="emoji-panel-list"]')
    || document.querySelector('[class*="webcast-chatroom"] [class*="emoji-panel"]');

  const result = [];
  const seen = new Set();

  const push = (el) => {
    if (!(el instanceof HTMLElement) || seen.has(el) || isInChatList(el) || isEmojiIcon(el)) return;
    if (el.offsetParent === null) return;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 120 || r.height > 120) return;
    seen.add(el);
    result.push({ el, top: Math.round(r.top), left: Math.round(r.left) });
  };

  if (!panel) return false;

  const officialItems = panel.querySelectorAll(
    '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"]'
  );
  if (officialItems.length > 0) {
    for (const el of officialItems) push(el);
  }
  if (result.length === 0) {
    for (const img of panel.querySelectorAll('img')) {
      push(img.closest('[class*="item"]') || img.parentElement || img);
    }
  }

  result.sort((a, b) => (a.top === b.top ? a.left - b.left : a.top - b.top));
  const target = result[index - 1]?.el;
  if (!target) return false;
  target.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  target.click();
  return true;
}
"""

# 抓取表情面板列表（含图片 URL，供配置页展示）
EMOJI_PANEL_LIST_SCRIPT = """
() => {
  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');

  const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
    || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
    || document.querySelector('[class*="emoji-panel-wrapper"]')
    || document.querySelector('[class*="emoji-panel-list"]')
    || document.querySelector('[class*="webcast-chatroom"] [class*="emoji-panel"]');

  const result = [];
  const seen = new Set();

  const getImageUrl = (el) => {
    if (!(el instanceof HTMLElement)) return '';
    const img = el instanceof HTMLImageElement ? el : el.querySelector('img');
    if (img instanceof HTMLImageElement) {
      return img.currentSrc
        || img.src
        || img.getAttribute('data-src')
        || img.getAttribute('data-original')
        || '';
    }
    const bg = window.getComputedStyle(el).backgroundImage || '';
    const match = bg.match(/url\\(["']?(.*?)["']?\\)/);
    return match ? match[1] : '';
  };

  const push = (el) => {
    if (!(el instanceof HTMLElement) || seen.has(el) || isInChatList(el) || isEmojiIcon(el)) return;
    if (el.offsetParent === null) return;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 120 || r.height > 120) return;
    const imageUrl = getImageUrl(el);
    if (!imageUrl) return;
    seen.add(el);
    result.push({ el, top: Math.round(r.top), left: Math.round(r.left), imageUrl });
  };

  if (!panel) return [];

  const officialItems = panel.querySelectorAll(
    '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"]'
  );
  if (officialItems.length > 0) {
    for (const el of officialItems) push(el);
  }
  if (result.length === 0) {
    for (const img of panel.querySelectorAll('[class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"], img')) {
      push(img.closest('[class*="item"]') || img.parentElement || img);
    }
  }

  result.sort((a, b) => (a.top === b.top ? a.left - b.left : a.top - b.top));
  return result.map((item, idx) => ({
    index: idx + 1,
    imageUrl: item.imageUrl,
  }));
}
"""

# 统计输入栏附近 / 弹层内可用表情数量（优先官方 emoji-panel）
EMOJI_AVAILABLE_COUNT_SCRIPT = """
() => {
  const panelCount = (() => {
    const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
      || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
      || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
      || document.querySelector('[class*="emoji-panel-wrapper"]')
      || document.querySelector('[class*="emoji-panel-list"]');
    if (!panel || panel.offsetParent === null) return 0;
    const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');
    const items = panel.querySelectorAll(
      '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"], img'
    );
    const seen = new Set();
    let count = 0;
    for (const node of items) {
      const el = node.closest(
        '[class*="webcast-chatroom___emoji-item"], [class*="emoji-item"], [class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"]'
      ) || node;
      if (!(el instanceof HTMLElement) || seen.has(el) || isEmojiIcon(el)) continue;
      if (el.offsetParent === null) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 8) continue;
      seen.add(el);
      count += 1;
    }
    return count;
  })();
  if (panelCount > 0) return panelCount;

  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const room = document.querySelector('[class*="webcast-chatroom"]');
  const input = room?.querySelector('textarea, [contenteditable="true"]');
  const inputRect = input?.getBoundingClientRect() || null;
  if (!inputRect) return 0;

  const seen = new Set();
  let count = 0;
  for (const sel of ['[class*="emoji-panel"]', '[class*="popover"]', '[class*="Popover"]']) {
    for (const panel of document.querySelectorAll(sel)) {
      if (!(panel instanceof HTMLElement) || panel.offsetParent === null || isInChatList(panel)) continue;
      const r = panel.getBoundingClientRect();
      if (r.width < 50 || r.height < 30 || r.top < inputRect.top - 420) continue;
      for (const img of panel.querySelectorAll('img')) {
        if (!(img instanceof HTMLImageElement) || img.offsetParent === null || seen.has(img)) continue;
        const ir = img.getBoundingClientRect();
        if (ir.width < 12 || ir.height < 12) continue;
        seen.add(img);
        count += 1;
      }
    }
  }
  return count;
}
"""

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
    sent_count: int = 0
    last_screenshot: str = ""
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
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._excel_logger: CommentExcelLogger | None = None
        self._stop_reason: str = "任务结束"

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
        if not config.has_comment_content():
            raise ValueError("请在评论输入框中输入文字或插入表情")
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
        self.runtime.sent_count = 0
        self.runtime.last_error = ""
        self.runtime.last_screenshot = ""
        self.runtime.excel_report_path = ""
        preview = config.comment_preview()
        self._append_log(f"单次评论内容：{preview}")
        if config.screenshotEnabled:
            self._append_log("发评后截图：已开启")
        else:
            self._append_log("发评后截图：已关闭")
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

    def begin_send(self) -> None:
        """
        开始发送评论。

        须在任务已进入直播间（ready）且尚未发送时调用。
        """
        if not self.runtime.running:
            raise RuntimeError("请先启动任务并进入直播间")
        if not self.runtime.ready:
            raise RuntimeError("直播间尚未就绪，请稍候再点击「开始发送」")
        if self.runtime.sending or self._send_event.is_set():
            raise RuntimeError("已在发送中")
        self.runtime.sending = True
        self._send_event.set()
        self._append_log("已收到开始发送指令")

    def stop(self) -> None:
        """停止自动评论任务。"""
        self._stop_reason = "手动停止"
        self._stop_event.set()
        self._send_event.set()
        self.runtime.running = False
        self.runtime.ready = False
        self.runtime.sending = False
        self._append_log("正在停止任务...")
        self._cleanup_browser()

    def _append_log(self, message: str) -> None:
        """追加运行日志。"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.runtime.logs.append(line)
        if len(self.runtime.logs) > 200:
            self.runtime.logs = self.runtime.logs[-200:]

    def _cleanup_browser(self) -> None:
        """释放浏览器资源。"""
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._playwright = None

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

        self._playwright = sync_playwright().start()
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
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
        self._append_log(f"已进入直播间，评论区就绪: {final_url}")
        return self._page

    def _wait_until_send_or_stop(self) -> bool:
        """
        等待「开始发送」信号，或在停止时返回。

        @returns: True 表示应开始发送；False 表示任务已取消
        """
        if self._auto_send:
            self._send_event.set()
            return True

        self._append_log("等待点击「开始发送」后再发送评论…")
        while not self._stop_event.is_set():
            if self._send_event.wait(timeout=0.5):
                return not self._stop_event.is_set()
        return False

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

    def _click_emoji_at_index(self, page: Page, emoji_index: int) -> bool:
        """
        点击表情包中指定序号的表情（从 1 开始）。

        @param page: 页面对象
        @param emoji_index: 表情序号
        @returns: 是否点击成功
        """
        if self._click_douyin_emoji_at_index(page, emoji_index):
            page.wait_for_timeout(200)
            return True

        if self._click_scoped_emoji_at_index(page, emoji_index):
            page.wait_for_timeout(200)
            return True

        if self._click_emoji_by_js(page, emoji_index):
            page.wait_for_timeout(200)
            return True

        emoji_items = self._find_emoji_items(page)
        if emoji_items is not None:
            total = self._safe_count(emoji_items)
            if emoji_index <= total:
                target = emoji_items.nth(emoji_index - 1)
                try:
                    target.scroll_into_view_if_needed(timeout=3000)
                    target.click(timeout=3000, force=True)
                    page.wait_for_timeout(200)
                    return True
                except Exception:
                    pass
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

    def _insert_single_emoji(self, page: Page, emoji_index: int) -> bool:
        """
        向输入框插入单个表情。

        @param page: 页面对象
        @param emoji_index: 表情序号（从 1 开始）
        @returns: 是否插入成功
        """
        emoji_index = max(1, emoji_index)
        for attempt in range(3):
            if self._open_emoji_panel(page) and self._click_emoji_at_index(page, emoji_index):
                page.wait_for_timeout(200)
                return True
            self._append_log(f"插入表情 {emoji_index} 失败，重试 ({attempt + 1}/3)")
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)
            except Exception:
                pass
        self._append_unicode_emoji(page, emoji_index)
        return True

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
                self._insert_single_emoji(page, part.index)
                emoji_indices.append(part.index)

        page.wait_for_timeout(300)
        if not self._click_send_button(page):
            page.keyboard.press("Enter")
        page.wait_for_timeout(500)

        preview = "".join(text_chunks)
        first_emoji = emoji_indices[0] if emoji_indices else 0
        return preview, first_emoji, len(emoji_indices)

    def _run_loop(self, config: AppConfig) -> None:
        """
        评论循环主逻辑：支持文字、表情，或二者组合发送。

        @param config: 运行配置
        """
        screenshot_dir = config.resolve_screenshot_dir()
        end_at = config.resolve_end_time()
        comment_parts = config.resolved_comment_parts()
        comment_preview = config.comment_preview()

        if config.endTimeEnabled and end_at is not None:
            self._append_log(f"任务将于 {end_at.strftime('%Y-%m-%d %H:%M:%S')} 自动停止")

        if config.excelReportEnabled:
            try:
                self._excel_logger = CommentExcelLogger(
                    config.resolve_excel_report_dir(),
                    config.resolve_live_room_url(),
                )
                self.runtime.excel_report_path = str(self._excel_logger.file_path)
                self._append_log(f"Excel 统计文件: {self._excel_logger.file_path.name}")
            except Exception as exc:
                self._append_log(f"创建 Excel 统计失败: {exc}")
                self._excel_logger = None

        try:
            page = self._ensure_browser(config)
            self.runtime.ready = True

            if not self._wait_until_send_or_stop():
                self._append_log("任务在开始发送前已取消")
                return

            self.runtime.sending = True
            self._append_log("开始执行自动评论")

            while not self._stop_event.is_set():
                if end_at is not None and datetime.now() >= end_at:
                    self._stop_reason = "到达结束时间自动停止"
                    self._append_log(
                        f"已到达结束时间 {end_at.strftime('%Y-%m-%d %H:%M:%S')}，任务自动停止",
                    )
                    break

                sent_text = comment_preview
                emoji_index = 0
                emoji_count = 0
                screenshot_path = ""
                record_status = "失败"
                record_remark = ""

                try:
                    chat_count_before = get_chat_message_count(page)
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

                    if config.screenshotEnabled:
                        saved, detected = capture_after_comment(
                            page,
                            screenshot_dir,
                            self.runtime.sent_count,
                            chat_count_before,
                            config.screenshotWaitSeconds,
                        )
                        screenshot_path = str(saved)
                        self.runtime.last_screenshot = screenshot_path
                        if detected:
                            self._append_log(f"评论已出现在聊天区，已保存截图: {saved.name}")
                        else:
                            self._append_log(
                                f"等待 {config.screenshotWaitSeconds}s 后已截图（未检测到新评论）: {saved.name}",
                            )
                except Exception as exc:
                    self.runtime.last_error = str(exc)
                    record_remark = str(exc)
                    self._append_log(f"发送失败: {exc}")

                if self._excel_logger is not None:
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
                            screenshot_path=screenshot_path,
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

        except Exception as exc:
            self.runtime.last_error = str(exc)
            self._append_log(f"任务异常: {exc}")
        finally:
            self.runtime.running = False
            self.runtime.ready = False
            self.runtime.sending = False
            self._finalize_excel_report(self.runtime.sent_count)
            self._cleanup_browser()
            self._append_log("任务已停止")
