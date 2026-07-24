"""评论发送 Excel 记录。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

HEADER_COLUMNS: list[str] = [
    "序号",
    "发送时间",
    "直播间URL",
    "表情序号",
    "单次数量",
    "截图路径",
    "状态",
    "备注",
]


class CommentExcelLogger:
    """评论发送 Excel 记录器。"""

    def __init__(self, report_dir: Path, live_room_url: str) -> None:
        """
        初始化 Excel 记录器并创建文件。

        @param report_dir: 报表目录
        @param live_room_url: 直播间 URL
        """
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_path = report_dir / f"comment_log_{timestamp}.xlsx"
        self.live_room_url = live_room_url
        self._workbook = Workbook()
        self._sheet = self._workbook.active
        self._sheet.title = "评论记录"
        self._sheet.append(HEADER_COLUMNS)
        for cell in self._sheet[1]:
            cell.font = Font(bold=True)
        self._workbook.save(self.file_path)

    def append_record(
        self,
        sequence: int,
        emoji_index: int,
        emoji_count: int,
        screenshot_path: str,
        status: str,
        remark: str = "",
    ) -> None:
        """
        追加一条评论发送记录。

        @param sequence: 发送序号
        @param emoji_index: 表情序号
        @param emoji_count: 单次表情数量
        @param screenshot_path: 截图路径
        @param status: 发送状态
        @param remark: 备注
        """
        self._sheet.append(
            [
                sequence,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.live_room_url,
                emoji_index,
                emoji_count,
                screenshot_path,
                status,
                remark,
            ],
        )
        self._workbook.save(self.file_path)

    def append_summary(self, total_sent: int, stop_reason: str) -> None:
        """
        追加任务结束摘要行。

        @param total_sent: 总发送次数
        @param stop_reason: 停止原因
        """
        self._sheet.append([])
        self._sheet.append(
            [
                "汇总",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "",
                "",
                total_sent,
                "",
                stop_reason,
                "",
            ],
        )
        self._workbook.save(self.file_path)

    def close(self) -> str:
        """
        关闭并保存 Excel。

        @returns: Excel 文件路径字符串
        """
        self._workbook.save(self.file_path)
        return str(self.file_path)
