"""抖音直播间表情面板：统一收集、去重与点击逻辑。"""

from __future__ import annotations

from urllib.parse import urlparse

# 内联 JS：收集面板表情（视觉排序 + 按图片 path 去重）
_EMOJI_HELPERS_BODY = """
  const isInChatList = (el) => !!el.closest(
    '[class*="webcast-chatroom___list"], [class*="___items"], [class*="message"], [class*="item-wrapper"]'
  );
  const isEmojiIcon = (el) => !!el.closest('[class*="webcast-chatroom___emoji-icon"]');

  const objectKeyFromUrl = (url) => {
    if (!url) return '';
    try {
      return new URL(url).pathname;
    } catch {
      const noQuery = String(url).split('?')[0];
      const idx = noQuery.indexOf('/obj/');
      return idx >= 0 ? noQuery.slice(idx) : noQuery;
    }
  };

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

  const findPanel = () =>
    document.querySelector('[class*="webcast-chatroom___emoji-panel"]')
    || document.querySelector('[class*="webcast-chatroom___emoji-list"]')
    || document.querySelector('[class*="emoji-panel-wrapper"]:not(.invisible)')
    || document.querySelector('[class*="emoji-panel-wrapper"]')
    || document.querySelector('[class*="emoji-panel-list"]')
    || document.querySelector('[class*="webcast-chatroom"] [class*="emoji-panel"]');

  const collectItems = () => {
    const panel = findPanel();
    if (!panel) return [];

    const candidates = [];
    const selectors = [
      '[class*="webcast-chatroom___emoji-item"] img',
      '[class*="emoji-item"] img',
      '[class*="emoji-panel__common-img"]',
      '[class*="emoji-panel__all-img"]',
      '[class*="webcast-chatroom___emoji-item"]',
      '[class*="emoji-item"]',
    ];
    for (const selector of selectors) {
      for (const node of panel.querySelectorAll(selector)) {
        if (!(node instanceof HTMLElement)) continue;
        const el = node instanceof HTMLImageElement
          ? node
          : (node.querySelector('img') || node);
        if (!(el instanceof HTMLElement)) continue;
        if (isInChatList(el) || isEmojiIcon(el)) continue;
        if (el.offsetParent === null) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 8 || r.height < 8 || r.width > 120 || r.height > 120) continue;
        const imageUrl = getImageUrl(el);
        if (!imageUrl) continue;
        candidates.push({ el, top: Math.round(r.top), left: Math.round(r.left), imageUrl });
      }
    }

    candidates.sort((a, b) => (a.top === b.top ? a.left - b.left : a.top - b.top));

    const seenKeys = new Set();
    const result = [];
    for (const item of candidates) {
      const objectKey = objectKeyFromUrl(item.imageUrl);
      if (!objectKey || seenKeys.has(objectKey)) continue;
      seenKeys.add(objectKey);
      result.push({
        top: item.top,
        left: item.left,
        imageUrl: item.imageUrl,
        objectKey,
        el: item.el,
      });
    }
    return result;
  };
"""

EMOJI_PANEL_LIST_SCRIPT = (
    "() => {\n"
    + _EMOJI_HELPERS_BODY
    + """
  return collectItems().map((item, idx) => ({
    index: idx + 1,
    imageUrl: item.imageUrl,
    objectKey: item.objectKey,
  }));
}
"""
)

EMOJI_PANEL_COUNT_SCRIPT = (
    "() => {\n"
    + _EMOJI_HELPERS_BODY
    + """
  return collectItems().length;
}
"""
)

EMOJI_CLICK_BY_INDEX_SCRIPT = (
    "(index) => {\n"
    + _EMOJI_HELPERS_BODY
    + """
  const items = collectItems();
  const target = items[index - 1]?.el;
  if (!target) return false;
  target.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  target.click();
  return true;
}
"""
)

EMOJI_CLICK_BY_OBJECT_KEY_SCRIPT = (
    "(objectKey) => {\n"
    + _EMOJI_HELPERS_BODY
    + """
  const key = String(objectKey || '').trim();
  if (!key) return false;
  const normalized = key.startsWith('/') ? key : (() => {
    try { return new URL(key).pathname; } catch { return key.split('?')[0]; }
  })();
  const items = collectItems();
  const target = items.find((item) =>
    item.objectKey === normalized
    || item.objectKey.endsWith(normalized)
    || normalized.endsWith(item.objectKey)
    || item.imageUrl.includes(normalized)
  )?.el;
  if (!target) return false;
  target.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  target.click();
  return true;
}
"""
)


def emoji_object_key_from_url(url: str) -> str:
    """
    从表情图片 URL 提取稳定 object path（用于去重与点击）。

    @param url: 图片 URL
    @returns: path 键，如 /obj/tos-cn-i-tsj2vxp0zn/xxx
    """
    trimmed = url.strip()
    if not trimmed:
        return ""
    try:
        return urlparse(trimmed).path
    except Exception:
        no_query = trimmed.split("?", 1)[0]
        idx = no_query.find("/obj/")
        return no_query[idx:] if idx >= 0 else no_query
