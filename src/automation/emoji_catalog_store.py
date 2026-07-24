"""抖音表情目录本地持久化缓存。"""

from __future__ import annotations

import json
from pathlib import Path

from src.automation.emoji_catalog import EmojiCatalogResponse
from src.config_loader import PROJECT_ROOT

EMOJI_CATALOG_PATH = PROJECT_ROOT / "data" / "emoji-catalog.json"


def load_emoji_catalog() -> EmojiCatalogResponse | None:
    """
    读取已缓存的表情目录。

    @returns: 缓存存在时返回目录，否则 None
    """
    if not EMOJI_CATALOG_PATH.exists():
        return None
    try:
        data = json.loads(EMOJI_CATALOG_PATH.read_text(encoding="utf-8"))
        return EmojiCatalogResponse.model_validate(data)
    except (OSError, ValueError, TypeError):
        return None


def save_emoji_catalog(catalog: EmojiCatalogResponse) -> None:
    """
    保存表情目录到本地文件。

    @param catalog: 表情目录
    """
    EMOJI_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMOJI_CATALOG_PATH.write_text(
        catalog.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
