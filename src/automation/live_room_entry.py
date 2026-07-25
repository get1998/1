"""进入抖音直播间：支持直接 URL，或按抖音号搜索进房。"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol
from urllib.parse import quote

from playwright.sync_api import Locator, Page

from src.config_loader import AppConfig, build_live_room_url, extract_live_room_id, normalize_web_rid

LogFn = Callable[[str], None]


class StopChecker(Protocol):
    """停止检查协议。"""

    def is_set(self) -> bool:
        """是否已请求停止。"""
        ...


SEARCH_INPUT_SELECTORS: list[str] = [
    'input[data-e2e="searchbar-input"]',
    'input[placeholder*="搜索"]',
    'header input[type="search"]',
    'header input[type="text"]',
    'input.search-input',
]

USER_TAB_SELECTORS: list[str] = [
    'span:has-text("用户")',
    'div[role="tab"]:has-text("用户")',
    'button:has-text("用户")',
    'a:has-text("用户")',
]

LIVE_BADGE_SELECTORS: list[str] = [
    'text=直播中',
    'span:has-text("直播中")',
    'div:has-text("直播中")',
]


def _raise_if_stopped(stop_checker: StopChecker | None) -> None:
    """若已停止则抛错。"""
    if stop_checker is not None and stop_checker.is_set():
        raise RuntimeError("任务已取消")


def _safe_click(locator: Locator, timeout_ms: int = 3000) -> bool:
    """
    尝试点击元素。

    @param locator: 定位器
    @param timeout_ms: 超时
    @returns: 是否点击成功
    """
    try:
        if locator.count() == 0:
            return False
        target = locator.first
        if not target.is_visible(timeout=800):
            return False
        target.click(timeout=timeout_ms)
        return True
    except Exception:
        return False


def _find_first_visible(page: Page, selectors: list[str]) -> Locator | None:
    """
    查找第一个可见元素。

    @param page: 页面
    @param selectors: 选择器列表
    @returns: locator 或 None
    """
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.count() == 0:
                continue
            candidate = locator.first
            if candidate.is_visible(timeout=800):
                return candidate
        except Exception:
            continue
    return None


def _page_looks_like_live_room(page: Page) -> bool:
    """
    粗判当前页是否已在直播间。

    @param page: 页面
    @returns: 是否像直播间
    """
    url = page.url or ""
    if "live.douyin.com/" in url and extract_live_room_id(url):
        return True
    try:
        # 评论输入常见结构
        for selector in (
            'textarea[placeholder*="说点什么"]',
            '[class*="webcast-chatroom"] textarea',
            '#chatInput textarea',
        ):
            locator = page.locator(selector)
            if locator.count() > 0 and locator.first.is_visible(timeout=500):
                return True
    except Exception:
        pass
    return False


def _try_open_direct_live(page: Page, web_rid: str, log: LogFn) -> bool:
    """
    尝试直接打开 live.douyin.com/{web_rid}。

    @param page: 页面
    @param web_rid: 直播间号或可直达的标识
    @param log: 日志回调
    @returns: 是否已进入直播间
    """
    url = build_live_room_url(web_rid)
    if not url:
        return False
    log(f"尝试直接打开: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3500)
    return _page_looks_like_live_room(page)


def _switch_to_user_tab(page: Page, log: LogFn) -> None:
    """切换到搜索结果「用户」页签。"""
    tab = _find_first_visible(page, USER_TAB_SELECTORS)
    if tab is not None:
        try:
            tab.click(timeout=3000)
            page.wait_for_timeout(1500)
            log("已切换到「用户」搜索结果")
        except Exception:
            pass


def _click_live_entry(page: Page, douyin_id: str, log: LogFn) -> bool:
    """
    在搜索/主页结果中点击进入直播。

    @param page: 页面
    @param douyin_id: 抖音号
    @param log: 日志回调
    @returns: 是否点击成功
    """
    # 1) 直接点「直播中」
    for selector in LIVE_BADGE_SELECTORS:
        locator = page.locator(selector)
        try:
            count = min(locator.count(), 8)
        except Exception:
            count = 0
        for index in range(count):
            item = locator.nth(index)
            try:
                if not item.is_visible(timeout=500):
                    continue
                item.click(timeout=3000)
                page.wait_for_timeout(2500)
                if _page_looks_like_live_room(page):
                    log("已点击「直播中」进入直播间")
                    return True
            except Exception:
                continue

    # 2) 点 live.douyin.com 链接
    live_links = page.locator('a[href*="live.douyin.com/"]')
    try:
        link_count = min(live_links.count(), 8)
    except Exception:
        link_count = 0
    for index in range(link_count):
        link = live_links.nth(index)
        try:
            href = link.get_attribute("href") or ""
            if not extract_live_room_id(href):
                continue
            link.click(timeout=3000)
            page.wait_for_timeout(2500)
            if _page_looks_like_live_room(page):
                log(f"已通过直播链接进入: {href}")
                return True
        except Exception:
            continue

    # 3) 点包含抖音号文本的用户卡片，再找直播入口
    user_card = page.locator(f'text={douyin_id}').first
    if _safe_click(user_card, 3000):
        page.wait_for_timeout(2500)
        log("已打开用户主页/卡片，继续查找直播入口")
        for selector in LIVE_BADGE_SELECTORS + ['a[href*="live.douyin.com/"]', 'text=进入直播间']:
            if _safe_click(page.locator(selector).first, 3000):
                page.wait_for_timeout(2500)
                if _page_looks_like_live_room(page):
                    log("已从用户页进入直播间")
                    return True

    return False


def _search_douyin_id_and_enter(
    page: Page,
    douyin_id: str,
    log: LogFn,
    stop_checker: StopChecker | None,
) -> str:
    """
    在抖音网页搜索抖音号并进入直播间。

    @param page: 页面
    @param douyin_id: 抖音号
    @param log: 日志回调
    @param stop_checker: 停止检查
    @returns: 最终直播间 URL
    """
    _raise_if_stopped(stop_checker)

    # 策略 A：部分账号可用抖音号直达 live.douyin.com/{抖音号}
    if _try_open_direct_live(page, douyin_id, log):
        final_url = page.url
        log(f"抖音号可直达直播间: {final_url}")
        return final_url

    _raise_if_stopped(stop_checker)
    search_url = f"https://www.douyin.com/search/{quote(douyin_id)}?type=user"
    log(f"正在抖音搜索抖音号: {douyin_id}")
    page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3000)
    _switch_to_user_tab(page, log)

    if _click_live_entry(page, douyin_id, log) and _page_looks_like_live_room(page):
        return page.url

    # 策略 B：首页搜索框
    _raise_if_stopped(stop_checker)
    log("搜索结果未直接进房，改走首页搜索框")
    page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2500)
    search_input = _find_first_visible(page, SEARCH_INPUT_SELECTORS)
    if search_input is None:
        raise RuntimeError("未找到抖音搜索框，请确认页面已加载且已登录")
    search_input.click(timeout=3000)
    search_input.fill(douyin_id)
    page.keyboard.press("Enter")
    page.wait_for_timeout(3000)
    _switch_to_user_tab(page, log)

    if _click_live_entry(page, douyin_id, log) and _page_looks_like_live_room(page):
        return page.url

    # 策略 C：从当前页 HTML 里抠 live.douyin.com 链接再跳转
    html = page.content()
    matches = re.findall(r"https://live\.douyin\.com/([A-Za-z0-9_\-]+)", html)
    for rid in matches:
        rid = normalize_web_rid(rid)
        if not rid or rid.lower() in {"search", "faq", "category"}:
            continue
        if _try_open_direct_live(page, rid, log):
            return page.url

    raise RuntimeError(
        f"未能根据抖音号「{douyin_id}」进入直播间。"
        "请确认该账号正在直播，或手动填写直播间号后重试",
    )


def enter_live_room(
    page: Page,
    config: AppConfig,
    log: LogFn,
    stop_checker: StopChecker | None = None,
) -> str:
    """
    进入直播间。

    优先级：
    1. 已配置直播间号 / URL → 直接打开
    2. 仅配置抖音号 → 打开抖音并搜索进房

    @param page: Playwright 页面
    @param config: 运行配置
    @param log: 日志回调
    @param stop_checker: 可选停止检查
    @returns: 最终直播间 URL
    """
    direct_url = config.resolve_live_room_url()
    if direct_url:
        log(f"使用已配置直播间地址打开: {direct_url}")
        page.goto(direct_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3000)
        if _page_looks_like_live_room(page):
            return page.url
        log("直接打开后未识别到评论区，若已配置抖音号将尝试搜索进房")

    douyin_id = config.douyinId.strip()
    if not douyin_id:
        if direct_url:
            return page.url
        raise ValueError("请填写抖音号，或填写直播间号/URL")

    return _search_douyin_id_and_enter(page, douyin_id, log, stop_checker)
