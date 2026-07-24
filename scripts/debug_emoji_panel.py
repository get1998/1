"""诊断抖音表情面板 DOM 结构。"""

from __future__ import annotations

import json

from playwright.sync_api import Page, sync_playwright

from src.automation.douyin_live import (
    DOUYIN_EMOJI_ICON_CLICK_SCRIPT,
    DouyinLiveAutomation,
    ENSURE_INPUT_VISIBLE_SCRIPT,
    PROJECT_ROOT,
    TaskRuntime,
)
from src.config_loader import load_config

PANEL_STATE_SCRIPT = """
() => {
  const wrapper = document.querySelector('[class*="emoji-panel-wrapper"]');
  const panel = document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom"] [class*="emoji-panel"]')
    || wrapper;
  const imgs = panel ? [...panel.querySelectorAll('[class*="emoji-panel__common-img"], [class*="emoji-panel__all-img"], img')] : [];
  const visibleImgs = imgs.filter((img) => {
    if (!(img instanceof HTMLElement)) return false;
    const r = img.getBoundingClientRect();
    return r.width >= 8 && r.height >= 8 && img.offsetParent !== null;
  });
  const withSrc = visibleImgs.filter((img) => {
    const el = img;
    const src = el instanceof HTMLImageElement ? (el.currentSrc || el.src) : '';
    return !!src;
  });
  return {
    wrapperClass: wrapper ? (wrapper.className || '').toString() : '',
    panelClass: panel ? (panel.className || '').toString().slice(0, 120) : '',
    totalImgs: imgs.length,
    visibleImgs: visibleImgs.length,
    withSrc: withSrc.length,
    sampleSrc: withSrc.slice(0, 3).map((img) => img.currentSrc || img.src),
  };
}
"""


def snapshot(page: Page, label: str) -> dict[str, object]:
    """采集当前面板状态。"""
    state = page.evaluate(PANEL_STATE_SCRIPT)
    state["label"] = label
    return state


def main() -> None:
    """打开直播间并输出表情面板诊断信息。"""
    config = load_config()
    live_room_url = config.liveRoomUrl.strip()
    user_data_dir = PROJECT_ROOT / ".playwright-user-data"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    automation = DouyinLiveAutomation(TaskRuntime())

    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(live_room_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        page.evaluate(ENSURE_INPUT_VISIBLE_SCRIPT)
        page.wait_for_timeout(500)
        results.append(snapshot(page, "before-open"))

        js_opened = bool(page.evaluate(DOUYIN_EMOJI_ICON_CLICK_SCRIPT))
        page.wait_for_timeout(800)
        results.append({**snapshot(page, "after-js-click"), "jsOpened": js_opened})

        playwright_opened = automation._open_emoji_panel(page)
        page.wait_for_timeout(1200)
        results.append({**snapshot(page, "after-playwright-open"), "playwrightOpened": playwright_opened})

        context.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
