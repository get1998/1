"""命令行入口：不启动 Web 页面，直接运行自动评论。"""

from __future__ import annotations

import src.playwright_env  # noqa: F401  # 启动前修正 PLAYWRIGHT_BROWSERS_PATH

import argparse
import signal
import sys
import time
from pathlib import Path

from src.automation.douyin_live import DouyinLiveAutomation, TaskRuntime
from src.config_loader import (
    DEFAULT_CONFIG_PATH,
    CommentPart,
    load_config,
    save_config,
)


def _build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器。

    @returns: ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(description="抖音直播间自动评论脚本")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="配置文件路径，默认项目根目录 config.json",
    )
    parser.add_argument("--url", default="", help="直播间 URL，覆盖配置文件")
    parser.add_argument("--douyin-id", default="", help="主播抖音号；无 URL 时搜索进房")
    parser.add_argument(
        "--web-rid",
        default="",
        help="直播间号 web_rid（live.douyin.com/ 后缀），有则直接打开",
    )
    parser.add_argument("--interval", type=int, default=0, help="发送间隔秒数，覆盖配置文件")
    parser.add_argument("--comment", default="", help="评论文字，可与表情组合")
    parser.add_argument(
        "--emojis-per-send",
        type=int,
        default=-1,
        help="单次评论中同一表情的数量（0 表示不发表情）",
    )
    parser.add_argument(
        "--emoji-index",
        type=int,
        default=0,
        help="任务指定表情序号（如 1、2、3），整次任务固定发送第 N 个",
    )
    parser.add_argument("--screenshot-dir", default="", help="截图目录，覆盖配置文件")
    return parser


def main() -> None:
    """CLI 主入口。"""
    parser = _build_parser()
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    if args.douyin_id:
        config.douyinId = args.douyin_id
    if args.web_rid:
        config.webRid = args.web_rid
    if args.url:
        config.liveRoomUrl = args.url
    if args.interval > 0:
        config.intervalSeconds = args.interval
    if args.comment or args.emojis_per_send >= 0 or args.emoji_index > 0:
        parts: list[CommentPart] = []
        comment = args.comment.strip() if args.comment else config.commentText.strip()
        if comment:
            parts.append(CommentPart(type="text", text=comment))
        emoji_count = args.emojis_per_send if args.emojis_per_send >= 0 else config.emojisPerSend
        emoji_index = args.emoji_index if args.emoji_index > 0 else config.emojiIndex
        if emoji_count >= 1:
            for _ in range(emoji_count):
                parts.append(CommentPart(type="emoji", index=max(1, emoji_index)))
        config.commentParts = parts
    if args.screenshot_dir:
        config.screenshotDir = args.screenshot_dir

    save_config(config, config_path)

    runtime = TaskRuntime()
    automation = DouyinLiveAutomation(runtime)

    def _handle_stop(_signum: int, _frame: object) -> None:
        print("\n收到停止信号，正在结束任务...")
        automation.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)

    try:
        automation.start(config, auto_send=True)
        print(f"任务已启动：{config.comment_preview()}，按 Ctrl+C 停止")
        while runtime.running:
            time.sleep(1)
    except (ValueError, RuntimeError) as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
