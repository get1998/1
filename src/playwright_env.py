"""Playwright 浏览器路径环境修复。"""

from __future__ import annotations

import os
from pathlib import Path


def _default_browsers_path() -> Path:
    """
    获取 Playwright 默认浏览器缓存目录。

    @returns: ms-playwright 目录路径
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _path_has_chromium(browsers_path: Path) -> bool:
    """
    判断目录下是否已安装 Chromium。

    @param browsers_path: Playwright 浏览器根目录
    @returns: 是否存在可用的 chrome.exe
    """
    if not browsers_path.is_dir():
        return False
    patterns = (
        "chromium-*/chrome-win64/chrome.exe",
        "chromium-*/chrome-win/chrome.exe",
    )
    return any(browsers_path.glob(pattern) for pattern in patterns)


def ensure_playwright_browsers_path() -> None:
    """
    修复 Playwright 浏览器查找路径。

    Cursor 等 IDE 终端可能注入指向临时沙箱目录的 PLAYWRIGHT_BROWSERS_PATH，
    重启后该目录会被清空，导致已执行 install 仍报浏览器不存在。
    若自定义路径无效，则回退到系统默认 ms-playwright 目录。
    """
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if not custom:
        return

    custom_path = Path(custom)
    sandbox_like = "cursor-sandbox-cache" in custom.replace("\\", "/").lower()
    if sandbox_like or not _path_has_chromium(custom_path):
        default_path = _default_browsers_path()
        if _path_has_chromium(default_path) or sandbox_like:
            os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)


ensure_playwright_browsers_path()
