"""命令行入口：不启动 Web 页面，直接运行自动评论。"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

from src.automation.douyin_live import DouyinLiveAutomation, TaskRuntime
from src.config_loader import DEFAULT_CONFIG_PATH, load_config, save_config


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
    parser.add_argument("--interval", type=int, default=0, help="发送间隔秒数，覆盖配置文件")
    parser.add_argument(
        "--emojis-per-send",
        type=int,
        default=0,
        help="单次评论中同一表情的数量（如 3）",
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

    if args.url:
        config.liveRoomUrl = args.url
    if args.interval > 0:
        config.intervalSeconds = args.interval
    if args.emojis_per_send > 0:
        config.emojisPerSend = args.emojis_per_send
    if args.emoji_index > 0:
        config.emojiIndex = args.emoji_index
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
        print(
            f"任务已启动：固定第 {config.emojiIndex} 个表情，"
            f"每种 {config.emojisPerSend} 个，按 Ctrl+C 停止",
        )
        while runtime.running:
            time.sleep(1)
    except (ValueError, RuntimeError) as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
