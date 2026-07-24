"""评论截图保存逻辑。"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

# 弹幕/评论列表容器选择器
CHAT_LIST_SELECTORS: list[str] = [
    '[class*="webcast-chatroom___list"]',
    '[class*="webcast-chatroom"] [class*="list"]',
    '[class*="Chatroom"] [class*="list"]',
]


def build_screenshot_path(directory: Path, sequence: int) -> Path:
    """
    生成截图文件路径。

    @param directory: 截图存储目录
    @param sequence: 当前发送序号
    @returns: 截图文件完整路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comment_{timestamp}_{sequence:03d}.png"
    return directory / filename


def get_chat_message_count(page: Page) -> int:
    """
    获取当前聊天列表中的消息条数。

    @param page: Playwright 页面对象
    @returns: 消息条数
    """
    script = """
    () => {
      const list = document.querySelector('[class*="webcast-chatroom___list"]')
        || document.querySelector('[class*="webcast-chatroom"] [class*="list"]');
      if (!list) return 0;
      const items = list.querySelectorAll('[class*="item-wrapper"], [class*="item"], [data-index]');
      return items.length;
    }
    """
    try:
        return int(page.evaluate(script))
    except Exception:
        return 0


def scroll_chat_to_bottom(page: Page) -> bool:
    """
    将评论区滚动到最底部，并尽量让最新一条评论进入可视区域。

    @param page: Playwright 页面对象
    @returns: 是否找到评论列表并完成滚动
    """
    script = """
    () => {
      const list = document.querySelector('[class*="webcast-chatroom___list"]')
        || document.querySelector('[class*="webcast-chatroom"] [class*="list"]');
      if (!list) return false;

      list.scrollTop = list.scrollHeight;

      const items = list.querySelectorAll(
        '[class*="item-wrapper"], [class*="item"], [data-index]'
      );
      const last = items[items.length - 1];
      if (last instanceof HTMLElement) {
        last.scrollIntoView({ block: 'end', behavior: 'instant' });
      }

      list.scrollTop = list.scrollHeight;
      return true;
    }
    """
    try:
        for _ in range(3):
            if not page.evaluate(script):
                return False
            page.wait_for_timeout(200)
        return True
    except Exception:
        return False


def wait_for_new_comment(
    page: Page,
    previous_count: int,
    timeout_ms: int = 15000,
    poll_ms: int = 300,
) -> bool:
    """
    等待聊天区出现新评论。

    @param page: Playwright 页面对象
    @param previous_count: 发送前消息条数
    @param timeout_ms: 最长等待毫秒
    @param poll_ms: 轮询间隔毫秒
    @returns: 是否检测到新评论
    """
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if get_chat_message_count(page) > previous_count:
            scroll_chat_to_bottom(page)
            page.wait_for_timeout(500)
            return True
        scroll_chat_to_bottom(page)
        page.wait_for_timeout(poll_ms)
    return False


def capture_page(page: Page, directory: Path, sequence: int) -> Path:
    """
    截取当前页面并保存。

    @param page: Playwright 页面对象
    @param directory: 截图存储目录
    @param sequence: 当前发送序号
    @returns: 已保存的截图路径
    """
    directory.mkdir(parents=True, exist_ok=True)
    target = build_screenshot_path(directory, sequence)
    page.screenshot(path=str(target), full_page=True)
    return target


def capture_after_comment(
    page: Page,
    directory: Path,
    sequence: int,
    previous_count: int,
    wait_seconds: int = 3,
) -> tuple[Path, bool]:
    """
    等待评论出现在聊天区后再截图。

    @param page: Playwright 页面对象
    @param directory: 截图存储目录
    @param sequence: 当前发送序号
    @param previous_count: 发送前聊天消息条数
    @param wait_seconds: 最短等待秒数（评论未检测到也会等待这么久）
    @returns: (截图路径, 是否检测到新评论)
    """
    min_wait_ms = max(wait_seconds, 1) * 1000
    max_wait_ms = max(min_wait_ms + 5000, 15000)
    start = time.time()

    detected = wait_for_new_comment(page, previous_count, timeout_ms=max_wait_ms)

    elapsed_ms = (time.time() - start) * 1000
    if elapsed_ms < min_wait_ms:
        page.wait_for_timeout(int(min_wait_ms - elapsed_ms))

    if detected:
        page.wait_for_timeout(800)

    scroll_chat_to_bottom(page)
    page.wait_for_timeout(300)

    directory.mkdir(parents=True, exist_ok=True)
    target = build_screenshot_path(directory, sequence)

    chatroom = page.locator('[class*="webcast-chatroom"]').first
    try:
        if chatroom.count() > 0 and chatroom.is_visible(timeout=1000):
            chatroom.screenshot(path=str(target))
            return target, detected
    except Exception:
        pass

    page.screenshot(path=str(target), full_page=True)
    return target, detected
